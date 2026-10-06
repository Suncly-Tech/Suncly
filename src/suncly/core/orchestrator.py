"""The Orchestrator (schema §2, §11), minimal and in-process (OQ-R1, proposal).

It expands an approved contract into runs (test case x repetitions), gives
every run its deterministic key, owns concurrency, retries, timeouts and the
budget cap, and re-fetches the card when all runs finish. It holds no
credentials and never calls the agent: the Runner does that, through the
``RunExecutor`` port.
"""

from __future__ import annotations

import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from decimal import Decimal

from suncly.core import signing
from suncly.core.judge import Judgement, JudgeService
from suncly.domain.card import AgentInterface, parse_agent_card
from suncly.domain.errors import CardError, StoreError
from suncly.domain.evidence import CardRecheck, NotExecutedReason, NotExecutedRun
from suncly.domain.models import Attestation, AttestationStatus, Run, TestCase
from suncly.domain.transcript import COST_PER_ATTEMPT
from suncly.ports.card_fetcher import CardFetcher
from suncly.ports.clock import Clock, IdGenerator
from suncly.ports.progress import ProgressListener
from suncly.ports.run_executor import RunExecutor, RunJob, RunResult
from suncly.ports.store import EvidenceStore


@dataclass(frozen=True)
class OrchestratorSettings:
    runs: int
    concurrency: int
    max_retries: int
    run_timeout_s: float
    poll_interval_s: float


@dataclass(frozen=True)
class RecordedRun:
    run: Run
    judgement: Judgement


@dataclass(frozen=True)
class OrchestrationResult:
    attestation: Attestation
    recorded: list[RecordedRun]
    not_executed: list[NotExecutedRun]
    planned_runs: int
    card_recheck: CardRecheck


def input_preview(test_case: TestCase, limit: int = 24) -> str:
    """A short, single-line view of a test case's input for progress output."""
    raw = test_case.input.get("text") or str(test_case.input.get("parts"))
    text = " ".join(str(raw).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class _Budget:
    """Thread-safe accounting: an attempt is charged before it starts (schema §11)."""

    def __init__(self, cost_total: Decimal, budget_limit: Decimal) -> None:
        self._lock = threading.Lock()
        self.cost_total = cost_total
        self.budget_limit = budget_limit

    def reached(self) -> bool:
        with self._lock:
            return self.cost_total >= self.budget_limit

    def charge(self, cost: Decimal) -> bool:
        """Charge ``cost`` unless the limit is already reached. Returns whether it was charged."""
        with self._lock:
            if self.cost_total >= self.budget_limit:
                return False
            self.cost_total += cost
            return True


class Orchestrator:
    def __init__(
        self,
        *,
        executor: RunExecutor,
        store: EvidenceStore,
        judge: JudgeService,
        fetcher: CardFetcher,
        clock: Clock,
        ids: IdGenerator,
        progress: ProgressListener,
        settings: OrchestratorSettings,
    ) -> None:
        self._executor = executor
        self._store = store
        self._judge = judge
        self._fetcher = fetcher
        self._clock = clock
        self._ids = ids
        self._progress = progress
        self._settings = settings

    def execute(
        self,
        attestation: Attestation,
        test_cases: list[TestCase],
        interface: AgentInterface,
        card_url: str,
        expected_card_hash: str,
        sandbox_declared: bool,
    ) -> OrchestrationResult:
        """Run the attestation to the point where the Policy engine takes over, or ends it."""
        attestation = self._set_status(attestation, AttestationStatus.RUNNING)
        plan = [(tc, attempt) for tc in test_cases for attempt in range(1, self._settings.runs + 1)]
        budget = _Budget(attestation.cost_total, attestation.budget_limit)
        recorded: list[RecordedRun] = []
        not_executed: list[NotExecutedRun] = []
        budget_stopped = False

        with ThreadPoolExecutor(max_workers=self._settings.concurrency) as pool:
            pending: set[Future[RecordedRun | NotExecutedRun]] = set()
            for test_case, attempt in plan:
                if budget.reached():
                    budget_stopped = True
                    not_executed.append(
                        NotExecutedRun(
                            test_case_id=test_case.id,
                            attempt=attempt,
                            reason=NotExecutedReason.BUDGET,
                            detail=f"cost_total reached budget_limit {budget.budget_limit}",
                        )
                    )
                    continue
                while len(pending) >= self._settings.concurrency:
                    done, pending = wait(pending, return_when=FIRST_COMPLETED)
                    self._collect(done, recorded, not_executed)
                pending.add(
                    pool.submit(
                        self._run_one,
                        attestation,
                        test_case,
                        attempt,
                        interface,
                        budget,
                        sandbox_declared,
                    )
                )
            done, _ = wait(pending)
            self._collect(done, recorded, not_executed)

        if any(item.reason is NotExecutedReason.BUDGET for item in not_executed):
            budget_stopped = True
        if budget_stopped:
            self._progress.on_event(
                "budget_stop",
                cost_total=str(budget.cost_total),
                budget_limit=str(budget.budget_limit),
            )

        attestation = signing.replace_fields(attestation, cost_total=budget.cost_total)
        if budget_stopped:
            recheck = CardRecheck(
                outcome="not_performed", detail="the budget stopped the attestation"
            )
            attestation = self._finish(attestation, AttestationStatus.FAILED)
        else:
            recheck = self._recheck_card(card_url, expected_card_hash)
            if recheck.outcome == "changed":
                attestation = self._finish(attestation, AttestationStatus.INVALIDATED)
            elif recheck.outcome == "unavailable":
                attestation = self._finish(attestation, AttestationStatus.FAILED)
            else:
                self._store.update_attestation(attestation)
        recorded.sort(key=lambda r: (str(r.run.test_case_id), r.run.attempt))
        return OrchestrationResult(
            attestation=attestation,
            recorded=recorded,
            not_executed=sorted(not_executed, key=lambda n: (str(n.test_case_id), n.attempt)),
            planned_runs=len(plan),
            card_recheck=recheck,
        )

    # -- one run ---------------------------------------------------------------

    def _run_one(
        self,
        attestation: Attestation,
        test_case: TestCase,
        attempt: int,
        interface: AgentInterface,
        budget: _Budget,
        sandbox_declared: bool,
    ) -> RecordedRun | NotExecutedRun:
        """Execute one run under its key, retrying crashes under the same key (DR-001)."""
        last_error = "the Runner produced no result"
        for retry in range(self._settings.max_retries + 1):
            if not budget.charge(COST_PER_ATTEMPT):
                return NotExecutedRun(
                    test_case_id=test_case.id,
                    attempt=attempt,
                    reason=NotExecutedReason.BUDGET,
                    detail="cost_total reached budget_limit before this attempt",
                )
            job = RunJob(
                attestation_id=attestation.id,
                test_case_id=test_case.id,
                attempt=attempt,
                message_id=str(self._ids.new_id()),
                input=test_case.input,
                target_url=interface.url,
                protocol_binding=interface.protocol_binding,
                protocol_version=interface.protocol_version,
                tenant=interface.tenant,
                timeout_s=self._settings.run_timeout_s,
                poll_interval_s=self._settings.poll_interval_s,
                sandbox_declared=sandbox_declared,
            )
            self._progress.on_event(
                "run_started",
                test_case_id=test_case.id,
                skill_id=test_case.skill_id,
                input_preview=input_preview(test_case),
                attempt=attempt,
                retry=retry,
            )
            result = self._execute(job)
            if result.transcript is not None:
                try:
                    run, judgement = self._judge.record(result.transcript, test_case)
                except StoreError as exc:
                    # A result under this key already exists: counted once, never twice.
                    self._progress.on_event(
                        "run_duplicate", test_case_id=test_case.id, attempt=attempt
                    )
                    existing = next(
                        (
                            r
                            for r in self._store.list_runs(attestation.id)
                            if r.test_case_id == test_case.id and r.attempt == attempt
                        ),
                        None,
                    )
                    if existing is None:
                        raise exc
                    return RecordedRun(
                        existing, judgement=Judgement(existing.verdict, existing.judge_layer)
                    )
                self._progress.on_event(
                    "run_recorded",
                    test_case_id=test_case.id,
                    skill_id=test_case.skill_id,
                    input_preview=input_preview(test_case),
                    attempt=attempt,
                    verdict=run.verdict.value,
                    latency_ms=run.latency_ms,
                    summary=judgement.summary,
                )
                return RecordedRun(run, judgement)
            if result.withheld:
                self._progress.on_event("run_withheld", test_case_id=test_case.id, attempt=attempt)
                return NotExecutedRun(
                    test_case_id=test_case.id,
                    attempt=attempt,
                    reason=NotExecutedReason.WITHHELD,
                    detail=result.error or "redaction failed; the transcript was withheld",
                )
            last_error = result.error or last_error
            self._progress.on_event(
                "run_retry",
                test_case_id=test_case.id,
                attempt=attempt,
                retry=retry + 1,
                error=last_error,
            )
        return NotExecutedRun(
            test_case_id=test_case.id,
            attempt=attempt,
            reason=NotExecutedReason.RUNNER_CRASHED,
            detail=f"after {self._settings.max_retries + 1} attempt(s): {last_error}",
        )

    def _execute(self, job: RunJob) -> RunResult:
        try:
            return self._executor.execute(job)
        except Exception as exc:  # a crashing executor is a crashed run, retried under the same key
            return RunResult(crashed=True, error=f"{type(exc).__name__}: {exc}")

    @staticmethod
    def _collect(
        done: set[Future[RecordedRun | NotExecutedRun]],
        recorded: list[RecordedRun],
        not_executed: list[NotExecutedRun],
    ) -> None:
        for future in done:
            outcome = future.result()
            if isinstance(outcome, RecordedRun):
                recorded.append(outcome)
            else:
                not_executed.append(outcome)

    # -- card re-fetch (schema §11) -------------------------------------------

    def _recheck_card(self, card_url: str, expected_card_hash: str) -> CardRecheck:
        try:
            fetched = self._fetcher.fetch(card_url)
            parsed = parse_agent_card(fetched.raw_json)
        except CardError as exc:
            recheck = CardRecheck(outcome="unavailable", detail=str(exc))
        else:
            if parsed.card_hash == expected_card_hash:
                recheck = CardRecheck(outcome="unchanged", card_hash=parsed.card_hash)
            else:
                recheck = CardRecheck(
                    outcome="changed",
                    card_hash=parsed.card_hash,
                    detail=f"card_hash is now {parsed.card_hash}, expected {expected_card_hash}",
                )
        self._progress.on_event("card_recheck", outcome=recheck.outcome, detail=recheck.detail)
        return recheck

    # -- status changes -------------------------------------------------------

    def _set_status(self, attestation: Attestation, status: AttestationStatus) -> Attestation:
        updated = signing.replace_fields(attestation, status=status)
        self._store.update_attestation(updated)
        self._progress.on_event("attestation_status", status=status.value)
        return updated

    def _finish(self, attestation: Attestation, status: AttestationStatus) -> Attestation:
        updated = signing.replace_fields(attestation, status=status, finished_at=self._clock.now())
        self._store.update_attestation(updated)
        self._progress.on_event("attestation_status", status=status.value)
        return updated
