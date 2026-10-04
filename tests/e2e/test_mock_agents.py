"""End to end: every bundled mock agent produces exactly its expected result.

These tests use the real pieces: a mock agent on a local port, the real card
fetcher, the Runner as a separate process, the file store, Ed25519 key files
and the report writer. Only the clock and ids are real too; the expectations
below are exact counts.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import pytest

from suncly.adapters.file_keys import FileSigningKeys
from suncly.adapters.file_store import FileEvidenceStore
from suncly.adapters.httpx_card_fetcher import HttpxCardFetcher
from suncly.adapters.local_transcripts import LocalTranscriptStorage
from suncly.adapters.report.writer import FolderReportWriter, read_report_folder
from suncly.adapters.subprocess_executor import SubprocessRunExecutor
from suncly.adapters.system import SystemClock, UuidIds
from suncly.core.attestation import AttestationService, AttestOutcome, AttestRequest, Services
from suncly.core.config import Config
from suncly.core.contract_builder import DeterministicDrafter
from suncly.core.verify import verify_result
from suncly.domain.models import AttestationStatus, DecisionOutcome
from suncly.domain.transcript import RunOutcome
from suncly.mock_agents import behaviours
from suncly.mock_agents.server import MockAgentServer
from suncly.ports.progress import NoProgress
from suncly.runner.credentials import CREDENTIAL_ENV_VAR
from tests.fakes import iter_files

pytestmark = pytest.mark.e2e

TEST_CREDENTIAL = "Bearer leaky-secret-token-ABCDEFGH123456"


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path / "home"


def make_services(
    home: Path, reports: Path, *, latency_limit_ms: int = 5000, runs: int = 1
) -> Services:
    config = Config(
        home=home,
        reports_dir=reports,
        runs=runs,
        run_timeout_s=8.0,
        latency_limit_ms=latency_limit_ms,
        max_retries=1,
        concurrency=3,
        poll_interval_s=0.05,
    )
    transcripts = LocalTranscriptStorage(config.transcripts_dir)
    return Services(
        config=config,
        store=FileEvidenceStore(config.store_dir),
        transcripts=transcripts,
        fetcher=HttpxCardFetcher(config.card_timeout_s, config.card_max_bytes),
        drafter=DeterministicDrafter(),
        executor=SubprocessRunExecutor(),
        keys=FileSigningKeys(config.keys_dir),
        clock=SystemClock(),
        ids=UuidIds(),
        report_writer=FolderReportWriter(config.reports_dir, transcripts),
        progress=NoProgress(),
    )


Attest = Callable[..., tuple[AttestOutcome, MockAgentServer]]


@pytest.fixture
def attest(home: Path, tmp_path: Path) -> Attest:
    def run(
        behaviour: behaviours.Behaviour,
        *,
        runs: int = 1,
        latency_limit_ms: int = 5000,
        budget: Decimal | None = None,
    ) -> tuple[AttestOutcome, MockAgentServer]:
        with MockAgentServer(behaviour) as server:
            services = make_services(
                home, tmp_path / "reports", latency_limit_ms=latency_limit_ms, runs=runs
            )
            outcome = AttestationService(services).attest(
                AttestRequest(
                    card_url=server.card_url,
                    sandbox_declared=True,
                    runs=runs,
                    budget_limit=budget,
                    approve_as="e2e",
                )
            )
            return outcome, server

    return run


def verdicts(outcome: AttestOutcome) -> dict[str, int]:
    assert outcome.bundle is not None
    counts = {"pass": 0, "fail": 0, "inconclusive": 0}
    for result in outcome.bundle.results:
        counts["pass"] += result.pass_count
        counts["fail"] += result.fail_count
        counts["inconclusive"] += result.inconclusive_count
    return counts


def outcomes(outcome: AttestOutcome) -> set[str]:
    assert outcome.bundle is not None
    return {str(r.document["transcript"]["outcome"]) for r in outcome.bundle.runs}


def check_names(outcome: AttestOutcome, passed: bool) -> set[str]:
    assert outcome.bundle is not None
    names: set[str] = set()
    for run in outcome.bundle.runs:
        for check in run.document["judgement"]["checks"]:
            if check["passed"] is passed:
                names.add(str(check["name"]))
    return names


def test_honest_agent_passes_every_run_and_the_report_verifies(attest: Attest) -> None:
    outcome, _ = attest(behaviours.Honest(), runs=2)
    assert outcome.kind == "completed"
    assert (
        outcome.attestation is not None
        and outcome.attestation.status is AttestationStatus.COMPLETED
    )
    assert verdicts(outcome) == {"pass": 6, "fail": 0, "inconclusive": 0}
    assert outcome.decision is not None and outcome.decision.outcome is DecisionOutcome.FLAG
    assert outcome.attestation.signature and outcome.attestation.signing_key_id
    assert outcome.report_dir is not None
    names = {p.name for p in outcome.report_dir.iterdir()}
    assert {"result.json", "report.md", "report.html", "transcripts"} <= names
    result, transcripts = read_report_folder(outcome.report_dir)
    assert verify_result(result, transcripts).ok
    report = (outcome.report_dir / "report.md").read_text(encoding="utf-8")
    assert "Decision: flag. No policy is configured, so a human must review this result." in report
    assert "## What was NOT tested" in report


def test_honest_async_agent_is_followed_by_polling_get_task(attest: Attest) -> None:
    outcome, _ = attest(behaviours.HonestAsync())
    assert verdicts(outcome) == {"pass": 3, "fail": 0, "inconclusive": 0}
    assert outcome.bundle is not None
    methods = {
        exchange["method"]
        for run in outcome.bundle.runs
        for exchange in run.document["transcript"]["exchanges"]
    }
    assert methods == {"SendMessage", "GetTask"}


def test_lying_agent_fails_every_run_on_its_declared_output_modes(attest: Attest) -> None:
    outcome, _ = attest(behaviours.Lying())
    assert outcome.kind == "completed"
    assert verdicts(outcome) == {"pass": 0, "fail": 3, "inconclusive": 0}
    assert check_names(outcome, passed=False) == {"output_modes"}
    assert outcome.decision is not None and outcome.decision.outcome is DecisionOutcome.FLAG


def test_flaky_agent_gives_an_exact_mix_of_pass_and_fail(attest: Attest) -> None:
    outcome, server = attest(behaviours.Flaky(), runs=2)
    assert server.calls == 6
    assert verdicts(outcome) == {"pass": 3, "fail": 3, "inconclusive": 0}
    # A failed task reaches the wrong final state and carries no artifacts.
    assert check_names(outcome, passed=False) == {"final_task_state", "response_present"}


def test_slow_agent_fails_the_latency_check(attest: Attest) -> None:
    outcome, _ = attest(behaviours.Slow(delay_s=0.8), latency_limit_ms=200)
    assert verdicts(outcome) == {"pass": 0, "fail": 3, "inconclusive": 0}
    assert check_names(outcome, passed=False) == {"latency_limit"}


def test_unreachable_agent_never_passes_and_is_inconclusive(attest: Attest) -> None:
    outcome, _ = attest(behaviours.Unreachable())
    assert outcome.kind == "completed"
    assert verdicts(outcome) == {"pass": 0, "fail": 0, "inconclusive": 3}
    assert outcomes(outcome) == {RunOutcome.UNREACHABLE.value}
    assert outcome.bundle is not None
    assert all(r.run.latency_ms is None for r in outcome.bundle.runs)
    assert any(item.category == "inconclusive runs" for item in outcome.bundle.not_tested)


def test_direct_message_reply_is_handled_without_error_and_is_not_a_pass(attest: Attest) -> None:
    outcome, _ = attest(behaviours.DirectMessage())
    assert outcomes(outcome) == {RunOutcome.RESPONDED_MESSAGE.value}
    assert verdicts(outcome) == {"pass": 0, "fail": 3, "inconclusive": 0}
    assert check_names(outcome, passed=False) == {"final_task_state"}
    assert "valid_schema" in check_names(outcome, passed=True)


def test_interrupted_agent_is_recorded_and_never_passes(attest: Attest) -> None:
    outcome, _ = attest(behaviours.Interrupted())
    assert verdicts(outcome) == {"pass": 0, "fail": 3, "inconclusive": 0}
    assert outcome.bundle is not None
    states = {r.document["transcript"]["final_task_state"] for r in outcome.bundle.runs}
    assert states == {"TASK_STATE_INPUT_REQUIRED"}
    methods = {
        e["method"] for r in outcome.bundle.runs for e in r.document["transcript"]["exchanges"]
    }
    assert methods == {"SendMessage"}, "the Runner never answers an interrupted state"


def test_leaky_agent_cannot_make_the_credential_appear_anywhere(
    attest: Attest,
    monkeypatch: pytest.MonkeyPatch,
    home: Path,
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """DR-003 end to end: the Runner process alone sees the credential; nothing it writes contains it."""
    monkeypatch.setenv(CREDENTIAL_ENV_VAR, TEST_CREDENTIAL)
    outcome, _ = attest(behaviours.Leaky())
    assert verdicts(outcome) == {"pass": 3, "fail": 0, "inconclusive": 0}
    token = TEST_CREDENTIAL.split()[1]
    for path in iter_files(tmp_path):
        if path.suffix in {".pem", ".pub"} or path.name == "current":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        assert TEST_CREDENTIAL not in text and token not in text, f"credential found in {path}"
    captured = capfd.readouterr()
    assert token not in captured.out and token not in captured.err
    assert outcome.bundle is not None
    transcript_text = json.dumps([r.document for r in outcome.bundle.runs])
    assert "[REDACTED]" in transcript_text
    assert all(
        r.document["transcript"]["redaction"]["replacements"] >= 2 for r in outcome.bundle.runs
    )


def test_card_changer_ends_invalidated_with_no_decision(attest: Attest, home: Path) -> None:
    outcome, _ = attest(behaviours.CardChanger())
    assert outcome.kind == "invalidated"
    assert outcome.attestation is not None
    assert outcome.attestation.status is AttestationStatus.INVALIDATED
    assert outcome.decision is None
    assert outcome.bundle is not None and outcome.bundle.decisions == []
    assert outcome.bundle.card_recheck.outcome == "changed"
    assert outcome.attestation.signature is not None, (
        "OQ-F7: signed with no decision in the payload"
    )
    assert outcome.bundle.signature_payload is not None
    assert outcome.bundle.signature_payload["decision"] is None
    store = FileEvidenceStore(home / "store")
    assert store.list_decisions(outcome.attestation.id) == []
    assert outcome.report_dir is not None
    assert "No decision" in (outcome.report_dir / "report.md").read_text(encoding="utf-8")


def test_skill_without_examples_is_listed_as_not_tested(attest: Attest) -> None:
    outcome, _ = attest(behaviours.NoExamples())
    assert outcome.kind == "completed"
    assert outcome.bundle is not None
    skills_tested = {tc.skill_id for tc in outcome.bundle.test_cases}
    assert skills_tested == {"uppercase"}
    details = [
        item.detail
        for item in outcome.bundle.not_tested
        if item.category == "skill without test case"
    ]
    assert len(details) == 1 and "summarize" in details[0] and "invariant 1" in details[0]


def test_budget_stop_ends_failed_and_reports_runs_never_executed(attest: Attest) -> None:
    outcome, server = attest(behaviours.Honest(), runs=2, budget=Decimal(2))
    assert outcome.kind == "failed"
    assert outcome.attestation is not None
    assert outcome.attestation.status is AttestationStatus.FAILED
    assert outcome.attestation.cost_total == Decimal(2)
    assert server.calls == 2
    assert outcome.decision is None
    assert outcome.bundle is not None and len(outcome.bundle.not_executed) == 4
    assert outcome.report_dir is not None
    report = (outcome.report_dir / "report.md").read_text(encoding="utf-8")
    assert "4 run(s) of 6 planned were never executed" in report
