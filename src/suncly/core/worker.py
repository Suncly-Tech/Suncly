"""The attestation job handler: runs one attestation through the Orchestrator, resumably.

What the in-process CLI path does in ``core/attestation.py`` this handler
does for a durable job: it loads the records, provisions a scoped executor
for the registration, resumes from the evidence already recorded, judges,
decides under the organization's policy, signs payload version 2, records
the ledger lines and settles the reservation. Progress is persisted on the
job after every run so the API can show it and a successor worker can resume
without repeating a run whose outcome is unknown.
"""

from __future__ import annotations

import contextlib
import hashlib
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from suncly.core import integrity
from suncly.core.app import AppServices
from suncly.core.attestation import deployment_identity_of
from suncly.core.cards import select_interface
from suncly.core.evidence import evidence_document_hash, store_payload
from suncly.core.jobs import JobCancelledError, JobContext, LeaseLostError
from suncly.core.judge import JUDGE_VERSION, JudgeService
from suncly.core.model_judge import ModelJudge
from suncly.core.orchestrator import (
    Orchestrator,
    OrchestratorSettings,
    ResumeState,
    RunKeyTuple,
)
from suncly.core.policy_engine import PolicyEngine, SigningBinding, aggregate
from suncly.domain.card import parse_agent_card
from suncly.domain.errors import StoreError, TranscriptExistsError
from suncly.domain.evidence import NotExecutedReason, TestCaseResult
from suncly.domain.jobs import JobKind, OutboxMessage
from suncly.domain.ledger import UsageOperation, UsageOutcome
from suncly.domain.models import AttestationStatus, JsonObject, TestCase
from suncly.domain.policy import ExternalToolSummary
from suncly.domain.tenancy import AgentRegistration
from suncly.ports.app_store import AttestationMeta, ExternalArtifact, SigningKeyRecord
from suncly.ports.external_tools import ExternalToolResult
from suncly.ports.model import StructuredResponse
from suncly.ports.signer import Signer


class _Progress:
    """Persists orchestration progress on the job and checks for cancellation and lease loss."""

    def __init__(self, context: JobContext, planned: int) -> None:
        self._context = context
        self._recorded = 0
        self._in_flight: set[str] = set(context.progress().get("in_flight") or [])
        self._planned = planned
        context.update_progress(
            phase="running", planned_runs=planned, in_flight=sorted(self._in_flight)
        )

    def on_event(self, event: str, **details: Any) -> None:
        if event == "run_recorded":
            self._recorded += 1
            self._context.update_progress(recorded_runs=self._recorded)

    def attempt_start(self, key: RunKeyTuple) -> None:
        self._context.check()
        self._in_flight.add(f"{key[0]}:{key[1]}")
        self._context.update_progress(in_flight=sorted(self._in_flight))

    def attempt_end(self, key: RunKeyTuple, outcome: str) -> None:
        self._in_flight.discard(f"{key[0]}:{key[1]}")
        self._context.update_progress(in_flight=sorted(self._in_flight))

    def should_stop(self) -> bool:
        return self._context.cancel_requested

    def in_flight_keys(self) -> frozenset[RunKeyTuple]:
        keys: set[RunKeyTuple] = set()
        for raw in self._in_flight:
            test_case_id, _, attempt = raw.rpartition(":")
            keys.add((test_case_id, int(attempt)))
        return frozenset(keys)


class AttestationJobHandler:
    kind = JobKind.ATTESTATION

    def __init__(self, services: AppServices) -> None:
        self._s = services

    def _signer(self) -> Signer:
        signer = self._s.keys.current()
        if signer is None:
            signer = self._s.keys.create()
        if self._s.app_store.get_signing_key(signer.key_id) is None:
            self._s.app_store.add_signing_key(
                SigningKeyRecord(
                    key_id=signer.key_id,
                    issuer=self._s.app_config.issuer,
                    public_key=signer.public_key,
                    created_at=self._s.clock.now(),
                )
            )
        return signer

    def handle(self, context: JobContext) -> None:
        s = self._s
        job = context.job
        attestation_id = job.logical_id
        meta = s.app_store.get_attestation_meta(attestation_id)
        attestation = s.store.get_attestation(attestation_id)
        if meta is None or attestation is None:
            raise StoreError(f"Attestation {attestation_id} has no record; nothing to run.")
        if attestation.status.is_final:
            context.update_progress(phase="finished", note="already final; nothing to do")
            return
        registration = s.app_store.get_registration(meta.organization_id, meta.registration_id)
        contract = s.store.get_contract(attestation.contract_id)
        card_version = s.store.get_card_version(attestation.card_version_id)
        agent = s.store.get_agent(card_version.agent_id) if card_version else None
        if registration is None or contract is None or card_version is None or agent is None:
            raise StoreError(f"Attestation {attestation_id} references records that do not exist.")
        if s.executor_factory is None:
            raise StoreError(
                "This process has no Runner executor; only a worker runs attestations."
            )
        test_cases = s.store.list_test_cases(contract.id)
        parsed = parse_agent_card(card_version.raw_json)
        interface = select_interface(parsed)
        runs = int(job.payload.get("runs") or meta.runs_per_test_case)
        reservation_id = (
            UUID(str(job.payload["reservation_id"])) if job.payload.get("reservation_id") else None
        )
        signer = self._signer()
        progress = _Progress(context, runs * len(test_cases))
        context.update_progress(target_url=interface.url)

        judge = JudgeService(
            s.store,
            s.transcripts,
            s.clock,
            s.ids,
            model_judge=self._model_judge(meta, registration, context, reservation_id),
        )
        orchestrator = Orchestrator(
            executor=s.executor_factory(registration),
            store=s.store,
            judge=judge,
            fetcher=s.fetcher,
            clock=s.clock,
            ids=s.ids,
            progress=progress,
            settings=OrchestratorSettings(
                runs=runs,
                concurrency=s.config.concurrency,
                max_retries=s.config.max_retries,
                run_timeout_s=s.config.run_timeout_s,
                poll_interval_s=s.config.poll_interval_s,
                retry_crashes=registration.sandbox_idempotent,
            ),
            should_stop=progress.should_stop,
            on_attempt_start=progress.attempt_start,
            on_attempt_end=progress.attempt_end,
        )
        try:
            orchestration = orchestrator.execute(
                attestation,
                test_cases,
                interface,
                registration.card_url,
                parsed.card_hash,
                registration.sandbox_declared,
                resume=ResumeState(
                    in_flight=progress.in_flight_keys(),
                    retry_unknown=registration.sandbox_idempotent,
                ),
            )
        except LeaseLostError:
            raise
        # A worker whose lease is gone finalizes nothing: another worker owns the job now.
        context.check()
        attestation = orchestration.attestation
        runs_recorded = [r.run for r in orchestration.recorded]
        external_results, artifact_hashes, external_summaries = self._external_tools(
            context, meta, attestation, registration, interface.url
        )
        context.check()

        # -- ledger lines: one per recorded run, whichever attempt recorded it ----------------
        # A run recorded by an attempt that died before writing its ledger line is billed
        # here, once; a run already on the ledger is never billed again.
        ledger = [
            event
            for event in s.app_store.list_usage_events(meta.organization_id)
            if event.attestation_id == attestation.id
            and event.operation is UsageOperation.AGENT_CALL
        ]
        billed_runs = {event.logical_run_id for event in ledger if event.logical_run_id}
        billed_notes = {event.note for event in ledger if event.logical_run_id is None}
        for run in runs_recorded:
            if run.id in billed_runs:
                continue
            s.usage.record_agent_call(
                organization_id=meta.organization_id,
                attestation_id=attestation.id,
                execution_attempt_id=context.attempt.id,
                reservation_id=reservation_id,
                outcome=UsageOutcome.SETTLED,
                note=f"run {run.test_case_id}#{run.attempt}",
                logical_run_id=run.id,
            )
        unknown = 0
        for item in orchestration.not_executed:
            if item.reason in (NotExecutedReason.UNKNOWN_OUTCOME, NotExecutedReason.RUNNER_CRASHED):
                unknown += 1
                note = (
                    f"unknown outcome: {item.reason.value} for {item.test_case_id}#{item.attempt}"
                )
                outcome = UsageOutcome.UNKNOWN
            elif item.reason is NotExecutedReason.WITHHELD:
                note = f"withheld transcript for {item.test_case_id}#{item.attempt}"
                outcome = UsageOutcome.SETTLED
            else:
                continue
            if note in billed_notes:
                continue
            s.usage.record_agent_call(
                organization_id=meta.organization_id,
                attestation_id=attestation.id,
                execution_attempt_id=context.attempt.id,
                reservation_id=reservation_id,
                outcome=outcome,
                note=note,
            )

        transcript_hashes = {
            str(run.id): evidence_document_hash(s.transcripts, run.transcript_ref)
            for run in runs_recorded
        }
        policy_record = self._latest_policy(meta.organization_id)
        baseline, baseline_at = self._baseline(meta, test_cases)
        binding = SigningBinding(
            issuer=s.app_config.issuer,
            contract_content_hash=meta.contract_content_hash,
            suite_version=meta.suite_version,
            judge_version=JUDGE_VERSION,
            environment=integrity.EnvironmentBinding(
                target_url=interface.url,
                deployment_mode=registration.deployment_mode.value,
                sandbox_declared=registration.sandbox_declared,
                protocol_binding=interface.protocol_binding,
                protocol_version=interface.protocol_version,
            ),
            deployment_identity=deployment_identity_of(parsed),
            validity=timedelta(days=s.app_config.attestation_validity_days),
            policy=policy_record.configuration if policy_record else None,
            risk_level=registration.risk_level,
            baseline=baseline,
            baseline_at=baseline_at,
            artifact_hashes=artifact_hashes,
            external=external_summaries,
        )
        context.check()
        engine = PolicyEngine(s.store, s.clock, s.ids, signer)
        policy_evaluation: JsonObject | None = None
        if attestation.status is AttestationStatus.RUNNING:
            _, attestation, _, evaluation, payload = engine.decide_and_sign(
                attestation,
                contract,
                parsed.card_hash,
                test_cases,
                runs_recorded,
                transcript_hashes,
                binding,
            )
            policy_evaluation = evaluation.model_dump(mode="json")
        else:
            attestation, payload = engine.sign_without_decision(
                attestation,
                contract,
                parsed.card_hash,
                test_cases,
                runs_recorded,
                transcript_hashes,
                binding,
            )
        store_payload(s.transcripts, attestation.id, payload)
        s.app_store.update_attestation_meta(
            meta.model_copy(
                update={
                    "policy_version": policy_record.policy_version if policy_record else None,
                    "policy_content_hash": policy_record.content_hash if policy_record else None,
                    "environment": binding.environment.to_json(),
                    "deployment_identity": binding.deployment_identity.to_json()
                    if binding.deployment_identity
                    else None,
                    "issued_at": datetime.fromisoformat(str(payload["issued_at"])),
                    "expires_at": datetime.fromisoformat(str(payload["expires_at"])),
                    "payload_version": integrity.PAYLOAD_VERSION_2,
                }
            )
        )
        if reservation_id is not None:
            s.usage.settle(reservation_id, unknown)
        context.update_progress(
            phase="finished",
            status=attestation.status.value,
            recorded_runs=len(runs_recorded),
            not_executed=[item.model_dump(mode="json") for item in orchestration.not_executed],
            card_recheck=orchestration.card_recheck.model_dump(mode="json"),
            policy_evaluation=policy_evaluation,
            unknown_outcomes=unknown,
            external_results=external_results,
            in_flight=[],
        )
        s.app_store.add_outbox(
            OutboxMessage(
                id=s.ids.new_id(),
                organization_id=meta.organization_id,
                topic="attestation.finished",
                dedup_key=f"attestation.finished:{attestation.id}",
                payload={"attestation_id": str(attestation.id), "status": attestation.status.value},
                created_at=s.clock.now(),
            )
        )
        if orchestration.cancelled:
            raise JobCancelledError(f"attestation {attestation.id} was cancelled")

    # -- exhausted --------------------------------------------------------------------

    def exhausted(self, context: JobContext, job: Any) -> None:
        """Every attempt failed: the attestation ends ``failed`` with no decision; the
        reservation stays held and is listed for reconciliation (ledger lines for runs the
        dead attempts recorded were never written, so nothing is settled by guesswork)."""
        s = self._s
        attestation = s.store.get_attestation(job.logical_id)
        if attestation is None or attestation.status.is_final:
            return
        failed = attestation.model_copy(
            update={"status": AttestationStatus.FAILED, "finished_at": s.clock.now()}
        )
        s.store.update_attestation(failed)
        meta = s.app_store.get_attestation_meta(attestation.id)
        if meta is not None:
            s.app_store.add_outbox(
                OutboxMessage(
                    id=s.ids.new_id(),
                    organization_id=meta.organization_id,
                    topic="attestation.failed",
                    dedup_key=f"attestation.failed:{attestation.id}",
                    payload={
                        "attestation_id": str(attestation.id),
                        "reason": job.last_error or "the job exhausted its attempts",
                    },
                    created_at=s.clock.now(),
                )
            )
        context.update_progress(
            phase="finished",
            status=AttestationStatus.FAILED.value,
            note=f"the job failed {job.attempts} time(s): {job.last_error or 'no error text'}",
        )

    # -- external tools -----------------------------------------------------------------

    def _external_tools(
        self,
        context: JobContext,
        meta: AttestationMeta,
        attestation: Any,
        registration: AgentRegistration,
        target_url: str,
    ) -> tuple[list[JsonObject], dict[str, str], list[ExternalToolSummary]]:
        """Run every requested tool once; a resumed execution reuses recorded results."""
        s = self._s
        requested = [str(name) for name in context.job.payload.get("external_tools") or []]
        if not requested:
            return [], {}, []
        recorded: dict[str, JsonObject] = {
            str(item.get("tool")): item
            for item in context.progress().get("external_results") or []
            if isinstance(item, dict)
        }
        results: list[JsonObject] = []
        for name in dict.fromkeys(requested):
            if name in recorded:
                results.append(recorded[name])
                continue
            context.check()
            context.update_progress(phase="external_tools", tool=name)
            factory = s.external_tools.get(name)
            if factory is None:
                outcome = ExternalToolResult(
                    tool=name,
                    tool_version="unavailable",
                    adapter_version="none",
                    target_url=target_url,
                    checks=[],
                    failure="this deployment has no runner for the tool",
                )
            else:
                work_dir = tempfile.mkdtemp(prefix=f"suncly-{name}-")
                try:
                    outcome = factory(registration).run(
                        target_url, work_dir, s.app_config.worker.external_tool_timeout_s
                    )
                except Exception as exc:  # a crashing adapter is a failed tool, never a pass
                    outcome = ExternalToolResult(
                        tool=name,
                        tool_version="unknown",
                        adapter_version="unknown",
                        target_url=target_url,
                        checks=[],
                        failure=f"{type(exc).__name__}: {exc}",
                    )
                finally:
                    shutil.rmtree(work_dir, ignore_errors=True)
            stored: list[JsonObject] = []
            for artifact in outcome.artifacts:
                key = f"{attestation.id}/external/{name}/{artifact.filename}"
                digest = "sha256:" + hashlib.sha256(artifact.content).hexdigest()
                with contextlib.suppress(TranscriptExistsError):
                    s.transcripts.put(key, artifact.content)
                s.app_store.add_external_artifact(
                    ExternalArtifact(
                        id=s.ids.new_id(),
                        organization_id=meta.organization_id,
                        attestation_id=attestation.id,
                        tool=name,
                        tool_version=outcome.tool_version,
                        kind=artifact.kind,
                        storage_ref=key,
                        sha256=digest,
                        created_at=s.clock.now(),
                    )
                )
                stored.append({"kind": artifact.kind, "storage_ref": key, "sha256": digest})
            item: JsonObject = {
                **outcome.model_dump(mode="json", exclude={"artifacts"}),
                "counts": outcome.counts(),
                "artifacts": stored,
            }
            results.append(item)
            context.update_progress(external_results=results)
        hashes = {
            str(a["storage_ref"]): str(a["sha256"]) for r in results for a in r.get("artifacts", [])
        }
        summaries = [
            ExternalToolSummary(
                tool=str(r["tool"]),
                tool_version=str(r["tool_version"]),
                passed=int(r["counts"]["passed"]),
                failed=int(r["counts"]["failed"]),
                undecided=int(r["counts"]["undecided"]),
                failure=r.get("failure"),
            )
            for r in results
        ]
        context.update_progress(phase="running")
        return results, hashes, summaries

    # -- helpers ------------------------------------------------------------------------

    def _model_judge(
        self,
        meta: AttestationMeta,
        registration: AgentRegistration,
        context: JobContext,
        reservation_id: UUID | None,
    ) -> ModelJudge | None:
        s = self._s
        if s.model_client is None or s.app_config.model is None:
            return None
        config = s.app_config.model

        def record(response: StructuredResponse) -> None:
            s.usage.record_model_call(
                organization_id=meta.organization_id,
                attestation_id=meta.attestation_id,
                execution_attempt_id=context.attempt.id,
                reservation_id=reservation_id,
                provider=config.provider,
                model=response.model or config.model,
                operation=UsageOperation.JUDGE,
                usage=response.usage,
                outcome=UsageOutcome.SETTLED if response.ok else UsageOutcome.FAILED,
                byok=registration.bring_your_own_model_key,
            )

        return ModelJudge(s.model_client, config, on_response=record)

    def _latest_policy(self, organization_id: UUID) -> Any:
        policies = self._s.app_store.list_policies(organization_id)
        return policies[-1] if policies else None

    def _baseline(
        self, meta: AttestationMeta, test_cases: list[TestCase]
    ) -> tuple[dict[UUID, TestCaseResult] | None, Any]:
        """The previous completed attestation of the same registration, keyed by test case."""
        s = self._s
        candidates = [
            m
            for m in s.app_store.list_attestation_meta(meta.organization_id, meta.registration_id)
            if m.attestation_id != meta.attestation_id
        ]
        best = None
        for candidate in candidates:
            record = s.store.get_attestation(candidate.attestation_id)
            if record is None or record.status is not AttestationStatus.COMPLETED:
                continue
            if best is None or record.started_at > best.started_at:
                best = record
        if best is None:
            return None, None
        previous_cases = s.store.list_test_cases(best.contract_id)
        from suncly.core.contract_builder import content_key

        by_content = {content_key(tc): tc.id for tc in previous_cases}
        results = {r.test_case_id: r for r in aggregate(previous_cases, s.store.list_runs(best.id))}
        mapped: dict[UUID, TestCaseResult] = {}
        for tc in test_cases:
            previous_id = by_content.get(content_key(tc))
            if previous_id is not None and previous_id in results:
                mapped[tc.id] = results[previous_id]
        return (mapped or None), best.finished_at
