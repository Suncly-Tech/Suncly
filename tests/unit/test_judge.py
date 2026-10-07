"""Judge Layer 1: every check, and the verdict rules."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from suncly.adapters.file_store import FileEvidenceStore
from suncly.adapters.local_transcripts import LocalTranscriptStorage
from suncly.core.judge import JudgeService, judge_run, resolve_pointer
from suncly.domain.criteria import Criteria, ModelCheck
from suncly.domain.errors import StoreError
from suncly.domain.models import (
    Agent,
    Attestation,
    AttestationStatus,
    AttestationTrigger,
    CardVersion,
    Contract,
    ContractStatus,
    JudgeLayer,
    RiskLevel,
    RunVerdict,
    TestCase,
    TestCaseKind,
)
from suncly.domain.transcript import RunOutcome
from tests.fakes import FakeClock, SeqIds, make_transcript, task_response

CRITERIA = Criteria(latency_limit_ms=1000, output_modes=["text/plain"])
TONE = ModelCheck(name="tone", criterion="the answer is polite", expected="yes_no", pass_rule="yes")


def failed_checks(criteria: Criteria, **kwargs: object) -> set[str]:
    judgement = judge_run(make_transcript(**kwargs), criteria)  # type: ignore[arg-type]
    return {c.name for c in judgement.checks if c.passed is False}


def test_a_conforming_task_passes_every_check() -> None:
    judgement = judge_run(make_transcript(), CRITERIA)
    assert (
        judgement.verdict is RunVerdict.PASS and judgement.judge_layer is JudgeLayer.DETERMINISTIC
    )
    assert {c.name for c in judgement.checks} == {
        "valid_schema",
        "final_task_state",
        "latency_limit",
        "response_present",
        "output_modes",
    }
    assert judgement.summary == "pass: every Layer 1 check passed"


def test_final_task_state_must_match_the_criteria() -> None:
    assert failed_checks(CRITERIA, final_response=task_response(state="TASK_STATE_FAILED")) == {
        "final_task_state"
    }
    assert failed_checks(
        CRITERIA, final_response=task_response(state="TASK_STATE_INPUT_REQUIRED")
    ) == {"final_task_state"}


def test_latency_limit() -> None:
    assert failed_checks(CRITERIA, latency_ms=1001) == {"latency_limit"}
    assert failed_checks(CRITERIA, latency_ms=1000) == set()


def test_response_present_needs_a_part_with_content() -> None:
    empty = task_response(text="   ")
    assert failed_checks(CRITERIA, final_response=empty) == {"response_present"}
    no_artifacts = task_response()
    del no_artifacts["artifacts"]
    assert failed_checks(CRITERIA, final_response=no_artifacts) == {"response_present"}
    assert (
        failed_checks(
            Criteria(latency_limit_ms=1000, response_present=False), final_response=no_artifacts
        )
        == set()
    )


def test_output_modes_are_checked_against_the_declared_list() -> None:
    assert failed_checks(CRITERIA, final_response=task_response(media_type="application/json")) == {
        "output_modes"
    }
    assert failed_checks(CRITERIA, final_response=task_response(media_type=None)) == set(), (
        "text defaults to text/plain"
    )
    data_part = task_response()
    data_part["artifacts"][0]["parts"] = [{"data": {"a": 1}}]
    assert failed_checks(CRITERIA, final_response=data_part) == {"output_modes"}


def test_valid_schema_rejects_malformed_tasks_and_messages() -> None:
    broken = task_response()
    broken["artifacts"][0]["parts"] = [{"text": "a", "data": 1}]
    assert "valid_schema" in failed_checks(CRITERIA, final_response=broken)
    no_status = task_response()
    del no_status["status"]
    judgement = judge_run(make_transcript(final_response=no_status), CRITERIA)
    assert judgement.verdict is RunVerdict.FAIL and "valid_schema" in judgement.summary


def test_required_fields_are_json_pointers() -> None:
    criteria = Criteria(
        latency_limit_ms=1000,
        required_fields=["/artifacts/0/parts/0/text", "/metadata", "/contextId"],
    )
    judgement = judge_run(make_transcript(), criteria)
    names = {c.name: c for c in judgement.checks}
    assert names["required_field /artifacts/0/parts/0/text"].passed is True
    assert (
        names["required_field /metadata"].passed is False
        and names["required_field /metadata"].detail == "missing"
    )
    assert names["required_field /contextId"].passed is True
    assert resolve_pointer({"a~b": {"c/d": [1, 2]}}, "/a~0b/c~1d/1") == 2
    with pytest.raises(KeyError):
        resolve_pointer({"a": []}, "/a/5")


def test_response_schema_is_validated() -> None:
    schema = {
        "type": "object",
        "required": ["artifacts"],
        "properties": {"id": {"type": "integer"}},
    }
    judgement = judge_run(
        make_transcript(), Criteria(latency_limit_ms=1000, response_schema=schema)
    )
    check = next(c for c in judgement.checks if c.name == "response_schema")
    assert check.passed is False and "integer" in check.detail


def test_model_checks_are_undecided_by_layer_1_and_make_the_run_inconclusive() -> None:
    judgement = judge_run(make_transcript(), Criteria(latency_limit_ms=1000, model_checks=[TONE]))
    assert judgement.verdict is RunVerdict.INCONCLUSIVE
    assert "model_check tone" in judgement.summary
    check = next(c for c in judgement.checks if c.name == "model_check tone")
    assert check.passed is None and "needs Layer 2" in check.detail


def test_a_failed_check_wins_over_an_undecided_one() -> None:
    criteria = Criteria(latency_limit_ms=1, model_checks=[TONE])
    assert judge_run(make_transcript(latency_ms=50), criteria).verdict is RunVerdict.FAIL


def test_direct_message_replies() -> None:
    message = {
        "messageId": "m",
        "role": "ROLE_AGENT",
        "parts": [{"text": "hi", "mediaType": "text/plain"}],
    }
    strict = judge_run(
        make_transcript(outcome=RunOutcome.RESPONDED_MESSAGE, final_response=message), CRITERIA
    )
    assert strict.verdict is RunVerdict.FAIL and {
        c.name for c in strict.checks if c.passed is False
    } == {"final_task_state"}
    lenient = Criteria(latency_limit_ms=1000, accept_direct_message=True)
    assert (
        judge_run(
            make_transcript(outcome=RunOutcome.RESPONDED_MESSAGE, final_response=message), lenient
        ).verdict
        is RunVerdict.PASS
    )


def test_outcomes_without_a_judgeable_response() -> None:
    assert judge_run(None, CRITERIA).verdict is RunVerdict.INCONCLUSIVE
    assert (
        judge_run(
            make_transcript(outcome=RunOutcome.UNREACHABLE, failure="refused"), CRITERIA
        ).verdict
        is RunVerdict.INCONCLUSIVE
    )
    timeout = judge_run(make_transcript(outcome=RunOutcome.TIMEOUT, final_response=None), CRITERIA)
    assert timeout.verdict is RunVerdict.FAIL and timeout.checks[0].name == "latency_limit"
    protocol = judge_run(
        make_transcript(outcome=RunOutcome.PROTOCOL_ERROR, final_response=None, failure="HTTP 500"),
        CRITERIA,
    )
    assert protocol.verdict is RunVerdict.FAIL and protocol.checks[0].name == "valid_schema"


def test_judge_service_stores_the_evidence_document_then_records_the_run(tmp_path: Path) -> None:
    now = datetime(2026, 10, 4, tzinfo=UTC)
    store = FileEvidenceStore(tmp_path / "store")
    storage = LocalTranscriptStorage(tmp_path / "transcripts")
    agent = Agent(id=UUID(int=1), name="A", owner="o", risk_level=RiskLevel.LOW)
    store.add_agent(agent)
    card_version = CardVersion(
        id=UUID(int=2), agent_id=agent.id, card_hash="sha256:c", raw_json="{}", fetched_at=now
    )
    store.add_card_version(card_version)
    contract = Contract(
        id=UUID(int=3),
        card_version_id=card_version.id,
        version=1,
        status=ContractStatus.DRAFT,
        created_at=now,
    )
    test_case = TestCase(
        id=UUID(int=4),
        contract_id=contract.id,
        skill_id="s",
        input={"text": "x"},
        criteria={"latency_limit_ms": 1000},
        kind=TestCaseKind.SKILL,
    )
    store.add_contract(contract, [test_case])
    store.approve_contract(contract.id, "alice", now)
    attestation = Attestation(
        id=UUID(int=5),
        contract_id=contract.id,
        card_version_id=card_version.id,
        trigger=AttestationTrigger.MANUAL,
        status=AttestationStatus.QUEUED,
        started_at=now,
        budget_limit=Decimal(2),
        cost_total=Decimal(0),
    )
    store.add_attestation(attestation)

    service = JudgeService(store, storage, FakeClock(), SeqIds())
    transcript = make_transcript().model_copy(
        update={"attestation_id": attestation.id, "test_case_id": test_case.id}
    )
    run, judgement = service.record(transcript, test_case)
    assert judgement.verdict is RunVerdict.PASS and run.verdict is RunVerdict.PASS
    assert run.judge_layer is JudgeLayer.DETERMINISTIC and run.rationale is None
    assert run.transcript_ref == f"{attestation.id}/{test_case.id}-1.json"
    document = storage.get(run.transcript_ref)
    assert b'"judgement"' in document and b'"transcript"' in document
    assert store.list_runs(attestation.id) == [run]
    with pytest.raises(StoreError, match="DR-001"):
        service.record(transcript, test_case)
