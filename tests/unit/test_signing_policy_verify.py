"""Signing, the flag-only Policy engine, coverage and the verifier."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from suncly.adapters.file_store import FileEvidenceStore
from suncly.core import integrity, signing
from suncly.core.policy_engine import (
    FLAG_EXPLANATION,
    POLICY_VERSION_UNCONFIGURED,
    PolicyEngine,
    SigningBinding,
    aggregate,
)
from suncly.core.verify import verify_result
from suncly.domain.errors import SigningError
from suncly.domain.evidence import TestCaseResult
from suncly.domain.models import (
    Agent,
    Attestation,
    AttestationStatus,
    AttestationTrigger,
    CardVersion,
    Contract,
    ContractStatus,
    DecisionOutcome,
    JudgeLayer,
    RiskLevel,
    Run,
    RunVerdict,
    TestCase,
    TestCaseKind,
)
from tests.fakes import FailingSigner, FakeClock, MemorySigner, SeqIds, card_json

NOW = datetime(2026, 10, 4, tzinfo=UTC)


def attestation(status: AttestationStatus = AttestationStatus.RUNNING) -> Attestation:
    return Attestation(
        id=UUID(int=10),
        contract_id=UUID(int=11),
        card_version_id=UUID(int=12),
        trigger=AttestationTrigger.MANUAL,
        status=status,
        started_at=NOW,
        budget_limit=Decimal(4),
        cost_total=Decimal(2),
    )


def contract() -> Contract:
    return Contract(
        id=UUID(int=11),
        card_version_id=UUID(int=12),
        version=3,
        status=ContractStatus.APPROVED,
        created_at=NOW,
        approved_by="alice",
        approved_at=NOW,
    )


def result(**counts: int) -> TestCaseResult:
    return TestCaseResult(
        test_case_id=UUID(int=20),
        skill_id="s",
        kind=TestCaseKind.SKILL,
        pass_count=counts.get("p", 0),
        fail_count=counts.get("f", 0),
        inconclusive_count=counts.get("i", 0),
    )


def test_payload_has_the_schema_section_11_fields_and_a_null_decision_when_undecided() -> None:
    payload = signing.build_payload(
        attestation=attestation(),
        card_hash="sha256:c",
        contract=contract(),
        results=[result(p=1, i=2)],
        transcript_hashes={"b": "sha256:2", "a": "sha256:1"},
        decision=None,
    )
    assert payload == {
        "payload_version": 1,
        "attestation_id": str(UUID(int=10)),
        "card_hash": "sha256:c",
        "contract": {"id": str(UUID(int=11)), "version": 3},
        "results": [
            {
                "test_case_id": str(UUID(int=20)),
                "skill_id": "s",
                "kind": "skill",
                "pass": 1,
                "fail": 0,
                "inconclusive": 2,
            }
        ],
        "transcript_hashes": {"a": "sha256:1", "b": "sha256:2"},
        "decision": None,
    }


def test_sign_and_verify_round_trip_and_tamper_detection() -> None:
    signer = MemorySigner()
    payload = {"attestation_id": "x", "n": 1}
    signature, key_id = signing.sign_payload(signer, payload)
    assert signature.startswith("ed25519:") and key_id == signing.key_id_for(signer.public_key)
    assert signing.verify_payload(signer.public_key, payload, signature)
    assert not signing.verify_payload(signer.public_key, {"attestation_id": "x", "n": 2}, signature)
    assert not signing.verify_payload(MemorySigner().public_key, payload, signature)
    assert not signing.verify_payload(signer.public_key, payload, "rsa:abc")
    assert not signing.verify_payload(signer.public_key, payload, "ed25519:not-base64!!")
    with pytest.raises(SigningError, match="could not be signed"):
        signing.sign_payload(FailingSigner(), payload)


def test_aggregate_keeps_inconclusive_apart_and_lists_every_test_case() -> None:
    tcs = [
        TestCase(
            id=UUID(int=1),
            contract_id=UUID(int=9),
            skill_id="a",
            input={},
            criteria={},
            kind=TestCaseKind.SKILL,
        ),
        TestCase(
            id=UUID(int=2),
            contract_id=UUID(int=9),
            skill_id="b",
            input={},
            criteria={},
            kind=TestCaseKind.SKILL,
        ),
    ]

    def run(tc: UUID, verdict: RunVerdict, attempt: int) -> Run:
        return Run(
            id=uuid4(),
            attestation_id=UUID(int=10),
            test_case_id=tc,
            attempt=attempt,
            verdict=verdict,
            judge_layer=JudgeLayer.DETERMINISTIC,
            cost=Decimal(1),
            transcript_ref="r",
            started_at=NOW,
            finished_at=NOW,
        )

    runs = [
        run(UUID(int=1), RunVerdict.PASS, 1),
        run(UUID(int=1), RunVerdict.INCONCLUSIVE, 2),
        run(UUID(int=1), RunVerdict.FAIL, 3),
    ]
    results = aggregate(tcs, runs)
    assert [(r.pass_count, r.fail_count, r.inconclusive_count) for r in results] == [
        (1, 1, 1),
        (0, 0, 0),
    ]
    assert results[0].total == 3


def test_policy_engine_writes_flag_then_signs_then_completes(tmp_path: Path) -> None:
    store = FileEvidenceStore(tmp_path)
    agent = Agent(id=UUID(int=1), name="A", owner="o", risk_level=RiskLevel.LOW)
    store.add_agent(agent)
    cv = CardVersion(
        id=UUID(int=12),
        agent_id=agent.id,
        card_hash="sha256:c",
        raw_json=json.dumps(card_json()),
        fetched_at=NOW,
    )
    store.add_card_version(cv)
    draft = contract().model_copy(
        update={"status": ContractStatus.DRAFT, "approved_by": None, "approved_at": None}
    )
    tc = TestCase(
        id=UUID(int=20),
        contract_id=draft.id,
        skill_id="echo",
        input={"text": "x"},
        criteria={"latency_limit_ms": 1},
        kind=TestCaseKind.SKILL,
    )
    store.add_contract(draft, [tc])
    approved = store.approve_contract(draft.id, "alice", NOW)
    queued = attestation(AttestationStatus.QUEUED)
    store.add_attestation(queued)
    running = queued.model_copy(update={"status": AttestationStatus.RUNNING})
    store.update_attestation(running)
    signer = MemorySigner()
    engine = PolicyEngine(store, FakeClock(), SeqIds(), signer)

    binding = SigningBinding(
        issuer="suncly-test",
        contract_content_hash="sha256:contract",
        suite_version="contract/1",
        judge_version="suncly-judge/2",
        environment=integrity.EnvironmentBinding(
            target_url="https://agent.example.com/rpc",
            deployment_mode="local",
            sandbox_declared=True,
            protocol_binding="JSONRPC",
            protocol_version="1.0",
        ),
        deployment_identity=None,
        validity=timedelta(days=30),
    )
    decision, completed, results, evaluation, payload = engine.decide_and_sign(
        running, approved, "sha256:c", [tc], [], {}, binding
    )
    assert decision.outcome is DecisionOutcome.FLAG and evaluation.requires_human
    assert (
        decision.policy_version == POLICY_VERSION_UNCONFIGURED and decision.decided_by == "policy"
    )
    assert completed.status is AttestationStatus.COMPLETED and completed.finished_at is not None
    assert completed.signing_key_id == signer.key_id
    assert store.list_decisions(running.id) == [decision]
    assert payload["payload_version"] == 2 and payload["issuer"] == "suncly-test"
    assert payload["decision"]["decided_by"] == "policy" and payload["policy"] is None
    assert payload["contract"]["content_hash"] == "sha256:contract"
    assert results and payload["results"][0]["test_case_id"] == str(tc.id)
    assert signing.verify_payload(signer.public_key, payload, completed.signature or "")
    assert "human must review" in FLAG_EXPLANATION
    with pytest.raises(ValueError, match="only a running attestation"):
        engine.decide_and_sign(completed, approved, "sha256:c", [tc], [], {}, binding)


def test_policy_engine_has_no_numeric_thresholds() -> None:
    """Every number the engine applies comes from the customer's policy (POLICY.md)."""
    import inspect
    import re

    from suncly.core import policy_engine
    from suncly.domain import policy

    for module in (policy_engine, policy):
        source = inspect.getsource(module)
        body = source.split("\ndef ", 1)[1]
        assert not re.search(r"\b0\.[1-9]\d*\b", body), module.__name__
        assert "threshold =" not in body, module.__name__
    assert policy_engine.decide([result(p=100)]).outcome is DecisionOutcome.FLAG


def make_result_document() -> tuple[dict[str, object], dict[str, bytes], MemorySigner]:
    """A minimal consistent result.json with one run, signed with a fresh key."""
    signer = MemorySigner()
    card = card_json()
    raw = json.dumps(card)
    from suncly.domain.canonical import sha256_hex
    from suncly.domain.card import compute_card_hash

    card_hash = compute_card_hash(card)
    transcript_bytes = b'{"transcript": {}, "judgement": {"verdict": "pass"}}'
    run_id = str(UUID(int=30))
    payload = {
        "payload_version": 1,
        "attestation_id": str(UUID(int=10)),
        "card_hash": card_hash,
        "contract": {"id": str(UUID(int=11)), "version": 3},
        "results": [
            {
                "test_case_id": str(UUID(int=20)),
                "skill_id": "s",
                "kind": "skill",
                "pass": 1,
                "fail": 0,
                "inconclusive": 0,
            }
        ],
        "transcript_hashes": {run_id: sha256_hex(transcript_bytes)},
        "decision": {"outcome": "flag", "policy_version": "unconfigured"},
    }
    signature, key_id = signing.sign_payload(signer, payload)
    document: dict[str, object] = {
        "attestation": {"id": str(UUID(int=10)), "signature": signature, "signing_key_id": key_id},
        "signer_public_key": signing.b64url(signer.public_key),
        "signature_payload": payload,
        "card_version": {"raw_json": raw, "card_hash": card_hash},
        "contract": {"id": str(UUID(int=11)), "version": 3},
        "runs": [
            {
                "run": {"id": run_id, "test_case_id": str(UUID(int=20)), "verdict": "pass"},
                "document_hash": sha256_hex(transcript_bytes),
            }
        ],
        "decisions": [{"outcome": "flag", "policy_version": "unconfigured"}],
    }
    return document, {run_id: transcript_bytes}, signer


def mutated(document: dict[str, object], mutate: object) -> dict[str, object]:
    copy: dict[str, object] = json.loads(json.dumps(document))
    assert callable(mutate)
    mutate(copy)
    return copy


def failing_checks(
    document: dict[str, object], transcripts: dict[str, bytes], public_key: bytes | None = None
) -> list[str]:
    return [c.name for c in verify_result(document, transcripts, public_key).checks if not c.ok]


def test_verify_passes_a_consistent_result() -> None:
    document, transcripts, signer = make_result_document()
    report = verify_result(document, transcripts)
    assert report.ok and report.to_json()["ok"] is True
    assert signer.key_id == document["attestation"]["signing_key_id"]  # type: ignore[index]


def test_verify_explains_each_kind_of_mismatch() -> None:
    document, transcripts, _ = make_result_document()

    def approve(doc: dict[str, object]) -> None:
        doc["decisions"][0]["outcome"] = "approve"  # type: ignore[index]

    assert failing_checks(mutated(document, approve), transcripts) == ["decision"]

    def other_card(doc: dict[str, object]) -> None:
        doc["card_version"]["raw_json"] = json.dumps(card_json(name="other"))  # type: ignore[index]

    assert failing_checks(mutated(document, other_card), transcripts) == ["card_hash"]

    assert failing_checks(document, {k: v + b" " for k, v in transcripts.items()}) == [
        "transcript hashes"
    ]
    report = verify_result(document, {})
    assert "transcript file missing" in next(
        c.detail for c in report.checks if c.name == "transcript hashes"
    )

    def bad_signature(doc: dict[str, object]) -> None:
        doc["attestation"]["signature"] = "ed25519:AAAA"  # type: ignore[index]

    assert failing_checks(mutated(document, bad_signature), transcripts) == ["signature valid"]

    def flip_verdict(doc: dict[str, object]) -> None:
        doc["runs"][0]["run"]["verdict"] = "fail"  # type: ignore[index]

    assert failing_checks(mutated(document, flip_verdict), transcripts) == ["aggregated results"]

    assert set(failing_checks(document, transcripts, MemorySigner().public_key)) == {
        "public key matches signing_key_id",
        "signature valid",
    }

    def drop_payload(doc: dict[str, object]) -> None:
        del doc["signature_payload"]

    report = verify_result(mutated(document, drop_payload), transcripts)
    assert not report.ok and report.checks[-1].name == "signature payload present"
