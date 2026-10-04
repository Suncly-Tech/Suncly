"""The entities enforce the invariants that need no database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from suncly.domain.models import (
    Attestation,
    AttestationStatus,
    AttestationTrigger,
    Contract,
    ContractStatus,
    Decision,
    DecisionOutcome,
    JudgeLayer,
    Run,
    RunKey,
    RunVerdict,
    TestCase,
    TestCaseKind,
)

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
ID = UUID(int=1)


def contract(**overrides: object) -> Contract:
    data: dict[str, object] = {
        "id": ID,
        "card_version_id": ID,
        "version": 1,
        "status": ContractStatus.DRAFT,
        "created_at": NOW,
    }
    data.update(overrides)
    return Contract.model_validate(data)


def attestation(**overrides: object) -> Attestation:
    data: dict[str, object] = {
        "id": ID,
        "contract_id": ID,
        "card_version_id": ID,
        "trigger": AttestationTrigger.MANUAL,
        "status": AttestationStatus.QUEUED,
        "started_at": NOW,
        "budget_limit": Decimal(10),
        "cost_total": Decimal(0),
    }
    data.update(overrides)
    return Attestation.model_validate(data)


def run(**overrides: object) -> Run:
    data: dict[str, object] = {
        "id": ID,
        "attestation_id": ID,
        "test_case_id": UUID(int=2),
        "attempt": 1,
        "verdict": RunVerdict.PASS,
        "judge_layer": JudgeLayer.DETERMINISTIC,
        "latency_ms": 5,
        "cost": Decimal(1),
        "transcript_ref": "ref",
        "started_at": NOW,
        "finished_at": NOW,
    }
    data.update(overrides)
    return Run.model_validate(data)


def test_invariant_3_draft_and_rejected_contracts_have_no_approval_fields() -> None:
    for status in (ContractStatus.DRAFT, ContractStatus.REJECTED):
        contract(status=status)
        with pytest.raises(ValidationError, match="invariant 3"):
            contract(status=status, approved_by="x", approved_at=NOW)


def test_invariant_3_approved_and_superseded_contracts_carry_both_approval_fields() -> None:
    for status in (ContractStatus.APPROVED, ContractStatus.SUPERSEDED):
        contract(status=status, approved_by="reviewer", approved_at=NOW)
        with pytest.raises(ValidationError):
            contract(status=status)
        with pytest.raises(ValidationError):
            contract(status=status, approved_by="reviewer")
    with pytest.raises(ValidationError, match="blank"):
        contract(status=ContractStatus.APPROVED, approved_by="  ", approved_at=NOW)


def test_a_skill_test_case_names_its_skill() -> None:
    TestCase(id=ID, contract_id=ID, skill_id="echo", input={}, criteria={}, kind=TestCaseKind.SKILL)
    TestCase(
        id=ID,
        contract_id=ID,
        skill_id=None,
        input={},
        criteria={},
        kind=TestCaseKind.PROBE_INJECTION,
    )
    with pytest.raises(ValidationError, match="skill_id"):
        TestCase(
            id=ID, contract_id=ID, skill_id=None, input={}, criteria={}, kind=TestCaseKind.SKILL
        )


def test_finished_at_marks_exactly_the_final_statuses() -> None:
    for status in (AttestationStatus.QUEUED, AttestationStatus.RUNNING):
        attestation(status=status)
        with pytest.raises(ValidationError, match="finished_at"):
            attestation(status=status, finished_at=NOW)
    for status in (
        AttestationStatus.FAILED,
        AttestationStatus.CANCELLED,
        AttestationStatus.INVALIDATED,
    ):
        attestation(status=status, finished_at=NOW)
        with pytest.raises(ValidationError, match="finished_at"):
            attestation(status=status)
    with pytest.raises(ValidationError, match="precede"):
        attestation(status=AttestationStatus.FAILED, finished_at=NOW - timedelta(seconds=1))


def test_signature_fields_travel_together_and_completed_is_signed() -> None:
    with pytest.raises(ValidationError, match="together"):
        attestation(signature="s")
    with pytest.raises(ValidationError, match="together"):
        attestation(signing_key_id="k")
    with pytest.raises(ValidationError, match="signed"):
        attestation(status=AttestationStatus.COMPLETED, finished_at=NOW)
    signed = attestation(
        status=AttestationStatus.COMPLETED, finished_at=NOW, signature="s", signing_key_id="k"
    )
    assert signed.is_signed and signed.status.is_final


def test_invariant_7_a_model_verdict_needs_a_rationale() -> None:
    run(judge_layer=JudgeLayer.MODEL, rationale="because")
    with pytest.raises(ValidationError, match="invariant 7"):
        run(judge_layer=JudgeLayer.MODEL)
    with pytest.raises(ValidationError, match="invariant 7"):
        run(judge_layer=JudgeLayer.MODEL, rationale="   ")
    with pytest.raises(ValidationError, match="precede"):
        run(finished_at=NOW - timedelta(seconds=1))


def test_run_key_is_the_deterministic_triple() -> None:
    assert run(attempt=3).key == RunKey(ID, UUID(int=2), 3)
    with pytest.raises(ValidationError):
        run(attempt=0)
    with pytest.raises(ValidationError):
        run(latency_ms=-1)
    assert run(latency_ms=None).latency_ms is None


def test_decision_fields() -> None:
    decision = Decision(
        id=ID,
        attestation_id=ID,
        outcome=DecisionOutcome.FLAG,
        policy_version="v",
        decided_by="policy",
        decided_at=NOW,
    )
    assert decision.is_automatic
    with pytest.raises(ValidationError):
        Decision(
            id=ID,
            attestation_id=ID,
            outcome=DecisionOutcome.FLAG,
            policy_version="",
            decided_by="x",
            decided_at=NOW,
        )
    with pytest.raises(ValidationError, match="blank"):
        Decision(
            id=ID,
            attestation_id=ID,
            outcome=DecisionOutcome.FLAG,
            policy_version="v",
            decided_by="  ",
            decided_at=NOW,
        )


def test_entities_reject_unknown_fields_and_naive_datetimes() -> None:
    with pytest.raises(ValidationError):
        attestation(extra_field=1)
    with pytest.raises(ValidationError):
        attestation(started_at=datetime(2026, 1, 1))
