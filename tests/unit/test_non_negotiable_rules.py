"""One test per non-negotiable rule, named after the rule.

These tests prove the rules at the unit level with fakes. The end-to-end
suite proves them again against the bundled mock agents and a real Runner
process.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from suncly.adapters.file_store import FileEvidenceStore
from suncly.adapters.local_transcripts import LocalTranscriptStorage
from suncly.core.attestation import AttestationService, AttestRequest, Services
from suncly.core.judge import judge_run
from suncly.core.policy_engine import aggregate, decide
from suncly.domain.criteria import Criteria
from suncly.domain.errors import ApprovalRequiredError, SandboxDeclarationMissingError, StoreError
from suncly.domain.evidence import TestCaseResult
from suncly.domain.models import (
    AttestationStatus,
    DecisionOutcome,
    JudgeLayer,
    RunVerdict,
    TestCaseKind,
)
from suncly.domain.transcript import RunOutcome
from suncly.ports.run_executor import RunJob, RunResult
from suncly.runner.redaction import Redactor
from tests.fakes import FakeExecutor, StaticFetcher, card_text, make_transcript

CARD_URL = "https://agent.example.com/.well-known/agent-card.json"
ServicesFactory = Callable[..., Services]


def request(**overrides: object) -> AttestRequest:
    base: dict[str, object] = {
        "card_url": CARD_URL,
        "sandbox_declared": True,
        "runs": 2,
        "approve_as": "tester",
    }
    base.update(overrides)
    return AttestRequest(**base)  # type: ignore[arg-type]


def test_dr_001_idempotent_runs_retry_under_the_same_key_and_count_once(
    services_factory: ServicesFactory, file_store: FileEvidenceStore
) -> None:
    """A Runner that crashes once is retried under the same run key; the result is counted once."""

    def crash_then_pass(job: RunJob, n: int) -> RunResult:
        if n == 1:
            return RunResult(crashed=True, error="boom")
        return RunResult(transcript=make_transcript(job))

    executor = FakeExecutor(crash_then_pass)
    services = services_factory(StaticFetcher({CARD_URL: card_text()}), executor=executor)
    outcome = AttestationService(services).attest(request())
    assert outcome.attestation is not None
    runs = file_store.list_runs(outcome.attestation.id)
    assert len(runs) == 2 == outcome.planned_runs
    assert sorted(r.attempt for r in runs) == [1, 2]
    assert all(n == 2 for n in executor.attempts.values()), "each key was tried exactly twice"
    assert outcome.attestation.cost_total == Decimal(4), "every attempt is charged"
    with pytest.raises(StoreError, match="DR-001"):
        file_store.add_run(runs[0].model_copy(update={"id": runs[1].id}))


def test_dr_002_evidence_is_immutable(file_store: FileEvidenceStore, tmp_path: Path) -> None:
    """Runs, decisions and transcripts are append-only; corrections are new records."""
    assert not any(
        hasattr(file_store, name)
        for name in ("update_run", "delete_run", "update_decision", "delete_decision")
    )
    transcripts = LocalTranscriptStorage(tmp_path / "t")
    ref = transcripts.put("a/b.json", b"{}")
    with pytest.raises(StoreError, match="DR-002"):
        transcripts.put("a/b.json", b"{}")
    assert transcripts.get(ref) == b"{}"


def test_dr_003_secrets_never_leave_the_runner() -> None:
    """The credential, sensitive headers and known token patterns are removed from transcripts."""
    secret = "Bearer ZZtopSecretToken123456"
    redactor = Redactor([secret, secret.split()[1]])
    transcript = make_transcript()
    leaky = transcript.model_copy(
        update={
            "exchanges": [
                transcript.exchanges[0].model_copy(
                    update={
                        "headers": {
                            "Authorization": secret,
                            "Cookie": "session=abc",
                            "X-Other": "fine",
                        },
                        "body": {
                            "text": f"you sent {secret}",
                            "nested": [f"token={secret.split()[1]}"],
                        },
                    }
                )
            ],
            "final_response": {"artifacts": [{"parts": [{"text": f"echo {secret}"}]}]},
        }
    )
    from suncly.runner.redaction import redact_transcript

    redacted = redact_transcript(leaky, redactor)
    dumped = redacted.model_dump_json()
    assert secret not in dumped and "ZZtopSecretToken123456" not in dumped
    assert "session=abc" not in dumped
    assert "fine" in dumped
    assert redacted.redaction.replacements >= 4


def test_dr_005_budget_caps_live_in_the_orchestrator(
    services_factory: ServicesFactory, file_store: FileEvidenceStore
) -> None:
    """No run starts once cost_total reaches budget_limit; the attestation ends failed, undecided."""
    services = services_factory(StaticFetcher({CARD_URL: card_text()}))
    outcome = AttestationService(services).attest(request(budget_limit=Decimal(1)))
    assert outcome.kind == "failed"
    assert outcome.attestation is not None
    assert outcome.attestation.status is AttestationStatus.FAILED
    assert outcome.attestation.cost_total == Decimal(1) <= outcome.attestation.budget_limit
    assert len(file_store.list_runs(outcome.attestation.id)) == 1
    assert file_store.list_decisions(outcome.attestation.id) == []
    assert outcome.bundle is not None
    assert len(outcome.bundle.not_executed) == 1
    assert any("never executed" in item.category for item in outcome.bundle.not_tested)


def test_dr_006_tests_hit_only_a_declared_sandbox(services_factory: ServicesFactory) -> None:
    """Without the explicit sandbox declaration nothing runs, not even the card fetch."""
    fetcher = StaticFetcher({CARD_URL: card_text()})
    executor = FakeExecutor(lambda job, n: RunResult(transcript=make_transcript(job)))
    services = services_factory(fetcher, executor=executor)
    with pytest.raises(SandboxDeclarationMissingError):
        AttestationService(services).attest(request(sandbox_declared=False))
    assert fetcher.fetches == 0
    assert executor.jobs == []


def test_dr_007_reports_state_what_was_not_tested(services_factory: ServicesFactory) -> None:
    card = card_text(
        skills=[
            {"id": "echo", "name": "Echo", "description": "", "tags": ["t"], "examples": ["hi"]},
            {"id": "summarize", "name": "Summarize", "description": "", "tags": ["t"]},
        ],
        extra={"capabilities": {"streaming": True}},
    )
    services = services_factory(StaticFetcher({CARD_URL: card}))
    outcome = AttestationService(services).attest(request())
    assert outcome.bundle is not None
    categories = {item.category for item in outcome.bundle.not_tested}
    assert {
        "skill without test case",
        "declared capability not exercised",
        "production endpoint",
    } <= categories
    details = " ".join(item.detail for item in outcome.bundle.not_tested)
    assert "summarize" in details and "streaming" in details and "invariant 1" in details


def test_nothing_runs_against_a_contract_until_a_human_has_approved_it(
    services_factory: ServicesFactory, file_store: FileEvidenceStore
) -> None:
    executor = FakeExecutor(lambda job, n: RunResult(transcript=make_transcript(job)))
    services = services_factory(StaticFetcher({CARD_URL: card_text()}), executor=executor)
    with pytest.raises(ApprovalRequiredError):
        AttestationService(services).attest(request(approve_as=None))
    assert executor.jobs == []
    with pytest.raises(ApprovalRequiredError):
        AttestationService(services).attest(
            request(approve_as=None, approval_prompt=lambda draft: None)
        )
    assert executor.jobs == []
    outcome = AttestationService(services).attest(
        request(approve_as=None, approval_prompt=lambda draft: "alice")
    )
    assert outcome.attestation is not None
    contract = file_store.get_contract(outcome.attestation.contract_id)
    assert (
        contract is not None
        and contract.approved_by == "alice"
        and contract.approved_at is not None
    )


def test_inconclusive_is_never_counted_as_a_pass() -> None:
    criteria = Criteria(latency_limit_ms=1000, model_checks=["tone"])
    judgement = judge_run(make_transcript(), criteria)
    assert judgement.verdict is RunVerdict.INCONCLUSIVE
    unreachable = judge_run(
        make_transcript(outcome=RunOutcome.UNREACHABLE, failure="refused"),
        Criteria(latency_limit_ms=1000),
    )
    assert unreachable.verdict is RunVerdict.INCONCLUSIVE
    results = aggregate([], [])
    assert results == []
    result = TestCaseResult(
        test_case_id=UUID(int=1),
        skill_id="s",
        kind=TestCaseKind.SKILL,
        pass_count=1,
        fail_count=0,
        inconclusive_count=5,
    )
    assert result.to_payload()["pass"] == 1 and result.to_payload()["inconclusive"] == 5


@pytest.mark.parametrize(
    "passes,fails,inconclusives", [(0, 0, 0), (100, 0, 0), (0, 100, 0), (0, 0, 100), (7, 3, 1)]
)
def test_suncly_never_writes_an_approve_decision(
    passes: int, fails: int, inconclusives: int
) -> None:

    results = [
        TestCaseResult(
            test_case_id=uuid.uuid4(),
            skill_id="s",
            kind=TestCaseKind.SKILL,
            pass_count=passes,
            fail_count=fails,
            inconclusive_count=inconclusives,
        )
    ]
    assert decide(results) is DecisionOutcome.FLAG
    assert decide([]) is DecisionOutcome.FLAG


def test_only_the_runner_holds_credentials_and_the_job_carries_none() -> None:
    from suncly.ports.run_executor import RunJob

    assert "credential" not in {f.lower() for f in RunJob.model_fields}
    assert "authorization" not in {f.lower() for f in RunJob.model_fields}
    schema = json.dumps(RunJob.model_json_schema())
    assert "SUNCLY_AGENT" not in schema


def test_judge_layer_is_deterministic_for_every_layer_1_verdict() -> None:
    judgement = judge_run(make_transcript(), Criteria(latency_limit_ms=1000))
    assert (
        judgement.judge_layer is JudgeLayer.DETERMINISTIC and judgement.verdict is RunVerdict.PASS
    )
