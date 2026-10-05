"""Payload version 2: what it binds, how tampering shows, and the four verification layers."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest

from suncly.core import integrity, signing
from suncly.core.ci_gate import (
    GATE_APPROVED,
    GATE_EXECUTION_FAILED,
    GATE_NOT_APPROVED,
    GATE_UNREADABLE,
    GATE_VERIFICATION_FAILED,
    evaluate_gate,
)
from suncly.core.verify import verify_result
from suncly.domain.canonical import sha256_hex
from suncly.domain.card import compute_card_hash
from suncly.domain.evidence import TestCaseResult
from suncly.domain.models import (
    Attestation,
    AttestationStatus,
    AttestationTrigger,
    Contract,
    ContractStatus,
    Decision,
    DecisionOutcome,
    TestCaseKind,
)
from suncly.ports.app_store import SigningKeyRecord
from tests.fakes import MemorySigner, card_json

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
ISSUED = NOW - timedelta(days=1)
EXPIRES = NOW + timedelta(days=29)


def _attestation() -> Attestation:
    return Attestation(
        id=UUID(int=10),
        contract_id=UUID(int=11),
        card_version_id=UUID(int=12),
        trigger=AttestationTrigger.CI,
        status=AttestationStatus.RUNNING,
        started_at=ISSUED,
        budget_limit=4,
        cost_total=2,
    )


def _contract() -> Contract:
    return Contract(
        id=UUID(int=11),
        card_version_id=UUID(int=12),
        version=3,
        status=ContractStatus.APPROVED,
        created_at=ISSUED,
        approved_by="alice",
        approved_at=ISSUED,
    )


def _decision(outcome: DecisionOutcome = DecisionOutcome.APPROVE, by: str = "policy") -> Decision:
    return Decision(
        id=UUID(int=30),
        attestation_id=UUID(int=10),
        outcome=outcome,
        policy_version="v1",
        decided_by=by,
        decided_at=ISSUED,
    )


def make_result(
    signer: MemorySigner | None = None,
    decision: Decision | None = None,
    human: Decision | None = None,
) -> tuple[dict[str, Any], dict[str, bytes], MemorySigner]:
    """A consistent result.json with one run and a version 2 payload."""
    signer = signer or MemorySigner()
    decision = decision or _decision()
    card = card_json()
    raw = json.dumps(card)
    transcript = json.dumps(
        {"transcript": {"outcome": "responded_task"}, "judgement": {"verdict": "pass"}}
    ).encode()
    run_id = str(UUID(int=40))
    result_row = TestCaseResult(
        test_case_id=UUID(int=20),
        skill_id="echo",
        kind=TestCaseKind.SKILL,
        pass_count=1,
        fail_count=0,
        inconclusive_count=0,
    )
    payload = integrity.build_payload_v2(
        attestation=_attestation(),
        card_hash=compute_card_hash(card),
        contract=_contract(),
        contract_content_hash="sha256:contract",
        suite_version="behavioral-suite/1",
        judge_version="suncly-judge/2",
        rubric_versions={"r1": "2"},
        policy_version="v1",
        policy_content_hash="sha256:policy",
        results=[result_row],
        transcript_hashes={run_id: sha256_hex(transcript)},
        artifact_hashes={"tck/compatibility.json": "sha256:tck"},
        environment=integrity.EnvironmentBinding(
            target_url="https://agent.example.com/rpc",
            deployment_mode="public",
            sandbox_declared=True,
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        ),
        deployment_identity=integrity.DeploymentIdentity(
            agent_version="1.0.0", source="agent-card.version (self-declared by the agent)"
        ),
        issued_at=ISSUED,
        expires_at=EXPIRES,
        decision=decision,
        reviewer=None,
        issuer="suncly-test",
    )
    signature, key_id = signing.sign_payload(signer, payload)
    attestation = _attestation().model_copy(
        update={
            "status": AttestationStatus.COMPLETED,
            "finished_at": ISSUED,
            "signature": signature,
            "signing_key_id": key_id,
        }
    )
    decisions = [decision.model_dump(mode="json")]
    if human is not None:
        decisions.append(human.model_dump(mode="json"))
    result: dict[str, Any] = {
        "format": "suncly-result/1",
        "attestation": attestation.model_dump(mode="json"),
        "contract": _contract().model_dump(mode="json"),
        "card_version": {
            "id": str(UUID(int=12)),
            "card_hash": compute_card_hash(card),
            "raw_json": raw,
        },
        "runs": [
            {
                "run": {"id": run_id, "test_case_id": str(UUID(int=20)), "verdict": "pass"},
                "document_hash": sha256_hex(transcript),
            }
        ],
        "decisions": decisions,
        "signer_public_key": signing.b64url(signer.public_key),
        "signature_payload": payload,
    }
    return result, {run_id: transcript}, signer


def trusted(
    signer: MemorySigner, revoked_at: datetime | None = None, issuer: str = "suncly-test"
) -> dict[str, SigningKeyRecord]:
    return {
        signer.key_id: SigningKeyRecord(
            key_id=signer.key_id,
            issuer=issuer,
            public_key=signer.public_key,
            created_at=ISSUED - timedelta(days=10),
            revoked_at=revoked_at,
            revocation_reason="rotated" if revoked_at else None,
        )
    }


def test_payload_v2_binds_every_field_and_is_order_independent() -> None:
    result, _, _ = make_result()
    payload = result["signature_payload"]
    assert payload["payload_version"] == 2 and payload["issuer"] == "suncly-test"
    assert payload["contract"] == {
        "id": str(UUID(int=11)),
        "version": 3,
        "content_hash": "sha256:contract",
    }
    assert payload["policy"] == {"version": "v1", "content_hash": "sha256:policy"}
    assert payload["versions"] == {
        "suite": "behavioral-suite/1",
        "judge": "suncly-judge/2",
        "rubrics": {"r1": "2"},
    }
    assert payload["environment"]["target_url"] == "https://agent.example.com/rpc"
    assert payload["deployment_identity"]["source"].startswith("agent-card.version")
    assert payload["issued_at"] == ISSUED.isoformat(timespec="seconds")
    assert payload["decision"]["decided_by"] == "policy" and payload["artifact_hashes"]
    assert verify_result(result, make_result()[1]).ok


BOUND_FIELDS = [
    ("card_hash", "sha256:other"),
    ("contract", {"id": "x", "version": 3, "content_hash": "sha256:contract"}),
    ("contract", {"id": str(UUID(int=11)), "version": 4, "content_hash": "sha256:contract"}),
    ("contract", {"id": str(UUID(int=11)), "version": 3, "content_hash": "sha256:changed"}),
    ("policy", {"version": "v2", "content_hash": "sha256:policy"}),
    ("policy", {"version": "v1", "content_hash": "sha256:tampered"}),
    ("versions", {"suite": "other", "judge": "suncly-judge/2", "rubrics": {"r1": "2"}}),
    (
        "versions",
        {"suite": "behavioral-suite/1", "judge": "suncly-judge/1", "rubrics": {"r1": "2"}},
    ),
    (
        "versions",
        {"suite": "behavioral-suite/1", "judge": "suncly-judge/2", "rubrics": {"r1": "9"}},
    ),
    ("transcript_hashes", {}),
    ("artifact_hashes", {"tck/compatibility.json": "sha256:other"}),
    (
        "environment",
        {
            "target_url": "https://prod.example.com/rpc",
            "deployment_mode": "public",
            "sandbox_declared": True,
            "protocol_binding": "JSONRPC",
            "protocol_version": "1.0",
        },
    ),
    (
        "environment",
        {
            "target_url": "https://agent.example.com/rpc",
            "deployment_mode": "private_network",
            "sandbox_declared": True,
            "protocol_binding": "JSONRPC",
            "protocol_version": "1.0",
        },
    ),
    ("deployment_identity", None),
    (
        "deployment_identity",
        {"agent_version": "2.0.0", "source": "agent-card.version (self-declared by the agent)"},
    ),
    ("issued_at", (ISSUED - timedelta(days=5)).isoformat(timespec="seconds")),
    ("expires_at", (EXPIRES + timedelta(days=365)).isoformat(timespec="seconds")),
    (
        "decision",
        {"outcome": "approve", "policy_version": "v2", "decided_by": "policy", "reviewer": None},
    ),
    (
        "decision",
        {"outcome": "approve", "policy_version": "v1", "decided_by": "mallory", "reviewer": None},
    ),
    ("issuer", "someone-else"),
    ("results", []),
]


@pytest.mark.parametrize(("field", "value"), BOUND_FIELDS)
def test_tampering_with_any_bound_field_breaks_the_signature(field: str, value: object) -> None:
    result, files, _ = make_result()
    tampered = copy.deepcopy(result)
    tampered["signature_payload"][field] = value
    verification = verify_result(tampered, files)
    assert not verification.ok
    assert not next(c for c in verification.checks if c.name == "signature valid").ok


def test_tampering_with_the_decision_record_shows_even_when_the_signature_holds() -> None:
    result, files, _ = make_result()
    result["decisions"][0]["outcome"] = "block"
    verification = verify_result(result, files)
    assert next(c for c in verification.checks if c.name == "signature valid").ok
    assert not next(c for c in verification.checks if c.name == "decision").ok


def test_the_four_layers_are_separate_questions() -> None:
    result, files, signer = make_result()
    trust = integrity.TrustContext(
        now=NOW,
        trusted_keys=trusted(signer),
        expected_issuer="suncly-test",
        current_policy_hash="sha256:policy",
    )
    layers = integrity.verify_layers(result, files, trust)
    assert layers.accepted and layers.to_json()["accepted"]

    untrusted = integrity.verify_layers(result, files, integrity.TrustContext(now=NOW))
    assert (
        untrusted.cryptographically_valid
        and not untrusted.issuer_trusted
        and not untrusted.accepted
    )

    wrong_issuer = integrity.verify_layers(
        result,
        files,
        integrity.TrustContext(
            now=NOW, trusted_keys=trusted(signer, issuer="other"), expected_issuer="suncly-test"
        ),
    )
    assert wrong_issuer.cryptographically_valid and not wrong_issuer.issuer_trusted

    revoked_before = integrity.verify_layers(
        result,
        files,
        integrity.TrustContext(
            now=NOW, trusted_keys=trusted(signer, revoked_at=ISSUED - timedelta(hours=1))
        ),
    )
    assert not revoked_before.issuer_trusted, "issued after the revocation"
    revoked_after = integrity.verify_layers(
        result,
        files,
        integrity.TrustContext(
            now=NOW, trusted_keys=trusted(signer, revoked_at=ISSUED + timedelta(hours=1))
        ),
    )
    assert revoked_after.issuer_trusted, "issued while the key was still good"

    expired = integrity.verify_layers(
        result,
        files,
        integrity.TrustContext(now=EXPIRES + timedelta(seconds=1), trusted_keys=trusted(signer)),
    )
    assert expired.cryptographically_valid and expired.issuer_trusted and not expired.fresh
    future = integrity.verify_layers(
        result,
        files,
        integrity.TrustContext(now=ISSUED - timedelta(days=1), trusted_keys=trusted(signer)),
    )
    assert not future.fresh

    other_policy = integrity.verify_layers(
        result,
        files,
        integrity.TrustContext(
            now=NOW, trusted_keys=trusted(signer), current_policy_hash="sha256:new-policy"
        ),
    )
    assert other_policy.fresh and other_policy.issuer_trusted and not other_policy.policy_acceptable

    flagged, flagged_files, flagged_signer = make_result(decision=_decision(DecisionOutcome.FLAG))
    pending = integrity.verify_layers(
        flagged,
        flagged_files,
        integrity.TrustContext(now=NOW, trusted_keys=trusted(flagged_signer)),
    )
    assert pending.cryptographically_valid and not pending.policy_acceptable
    resolved, resolved_files, resolved_signer = make_result(
        decision=_decision(DecisionOutcome.FLAG),
        human=_decision(DecisionOutcome.APPROVE, by="bob@example.com").model_copy(
            update={"id": UUID(int=31)}
        ),
    )
    accepted = integrity.verify_layers(
        resolved,
        resolved_files,
        integrity.TrustContext(now=NOW, trusted_keys=trusted(resolved_signer)),
    )
    assert accepted.policy_acceptable, "a human approve resolves the flag"
    blocked, blocked_files, blocked_signer = make_result(
        decision=_decision(DecisionOutcome.FLAG),
        human=_decision(DecisionOutcome.BLOCK, by="bob@example.com").model_copy(
            update={"id": UUID(int=31)}
        ),
    )
    assert not integrity.verify_layers(
        blocked,
        blocked_files,
        integrity.TrustContext(now=NOW, trusted_keys=trusted(blocked_signer)),
    ).policy_acceptable


def test_version_1_results_still_verify_cryptographically() -> None:
    signer = MemorySigner()
    card = card_json()
    transcript = b'{"transcript": {}, "judgement": {}}'
    run_id = str(UUID(int=40))
    decision = _decision(DecisionOutcome.FLAG)
    payload = signing.build_payload(
        attestation=_attestation(),
        card_hash=compute_card_hash(card),
        contract=_contract(),
        results=[
            TestCaseResult(
                test_case_id=UUID(int=20),
                skill_id="echo",
                kind=TestCaseKind.SKILL,
                pass_count=1,
                fail_count=0,
                inconclusive_count=0,
            )
        ],
        transcript_hashes={run_id: sha256_hex(transcript)},
        decision=decision,
    )
    signature, key_id = signing.sign_payload(signer, payload)
    result = {
        "attestation": _attestation()
        .model_copy(
            update={
                "status": AttestationStatus.COMPLETED,
                "finished_at": ISSUED,
                "signature": signature,
                "signing_key_id": key_id,
            }
        )
        .model_dump(mode="json"),
        "contract": _contract().model_dump(mode="json"),
        "card_version": {"card_hash": compute_card_hash(card), "raw_json": json.dumps(card)},
        "runs": [
            {
                "run": {"id": run_id, "test_case_id": str(UUID(int=20)), "verdict": "pass"},
                "document_hash": sha256_hex(transcript),
            }
        ],
        "decisions": [decision.model_dump(mode="json")],
        "signer_public_key": signing.b64url(signer.public_key),
        "signature_payload": payload,
    }
    assert payload["payload_version"] == 1 and verify_result(result, {run_id: transcript}).ok
    layers = integrity.verify_layers(
        result, {run_id: transcript}, integrity.TrustContext(now=NOW, trusted_keys=trusted(signer))
    )
    assert layers.cryptographically_valid and layers.issuer_trusted
    assert not layers.fresh, "a version 1 payload has no validity window"
    assert integrity.payload_version_of(result) == 1


def test_the_gate_answers_three_questions_separately() -> None:
    result, files, signer = make_result()
    trust = integrity.TrustContext(
        now=NOW, trusted_keys=trusted(signer), expected_issuer="suncly-test"
    )
    assert evaluate_gate(result, files, trust).exit_code == GATE_APPROVED
    assert evaluate_gate({"nope": 1}, files, trust).exit_code == GATE_UNREADABLE

    failed = copy.deepcopy(result)
    failed["attestation"]["status"] = "failed"
    assert evaluate_gate(failed, files, trust).exit_code == GATE_EXECUTION_FAILED

    tampered = copy.deepcopy(result)
    tampered["signature_payload"]["card_hash"] = "sha256:x"
    assert evaluate_gate(tampered, files, trust).exit_code == GATE_VERIFICATION_FAILED
    assert (
        evaluate_gate(result, files, integrity.TrustContext(now=NOW)).exit_code
        == GATE_VERIFICATION_FAILED
    ), "untrusted issuer"
    assert (
        evaluate_gate(
            result, files, integrity.TrustContext(now=NOW), require_trusted_issuer=False
        ).exit_code
        == GATE_APPROVED
    )
    assert (
        evaluate_gate(
            result,
            files,
            integrity.TrustContext(now=EXPIRES + timedelta(days=1), trusted_keys=trusted(signer)),
        ).exit_code
        == GATE_VERIFICATION_FAILED
    )

    flagged, flagged_files, flagged_signer = make_result(decision=_decision(DecisionOutcome.FLAG))
    gate = evaluate_gate(
        flagged,
        flagged_files,
        integrity.TrustContext(now=NOW, trusted_keys=trusted(flagged_signer)),
    )
    assert gate.exit_code == GATE_NOT_APPROVED and gate.execution_ok and gate.verification_ok
    assert "flag" in gate.policy_detail and not gate.to_json()["approved"]
