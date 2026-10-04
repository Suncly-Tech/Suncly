"""One contract suite for every Evidence store: the file store and the Postgres store.

Every rule listed in ``suncly/ports/store.py`` is asserted here against each
implementation, so both stores refuse the same operations.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from suncly.adapters.file_store import FileEvidenceStore
from suncly.domain.errors import StoreError
from suncly.domain.models import (
    Agent,
    Attestation,
    AttestationStatus,
    AttestationTrigger,
    CardVersion,
    Contract,
    ContractStatus,
    Decision,
    DecisionOutcome,
    JudgeLayer,
    RiskLevel,
    Run,
    RunVerdict,
    TestCase,
    TestCaseKind,
)
from suncly.ports.store import EvidenceStore

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _postgres_available() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


STORE_KINDS = ["file"] + (["postgres"] if _postgres_available() else [])


@pytest.fixture(params=STORE_KINDS)
def store(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[EvidenceStore]:
    if request.param == "file":
        yield FileEvidenceStore(tmp_path / "store")
        return
    migrated = request.getfixturevalue("migrated_database")
    from suncly.adapters.postgres.store import PostgresEvidenceStore

    instance = PostgresEvidenceStore(migrated)
    try:
        yield instance
    finally:
        instance.close()


class Fixture:
    """A fresh agent, card version and approved contract with one test case."""

    def __init__(self, store: EvidenceStore, approved: bool = True) -> None:
        self.store = store
        self.agent = Agent(id=uuid4(), name="Agent", owner="team", risk_level=RiskLevel.LOW)
        store.add_agent(self.agent)
        self.card_version = CardVersion(
            id=uuid4(),
            agent_id=self.agent.id,
            card_hash=f"sha256:{uuid4().hex}",
            raw_json="{}",
            fetched_at=NOW,
        )
        store.add_card_version(self.card_version)
        self.contract = Contract(
            id=uuid4(),
            card_version_id=self.card_version.id,
            version=1,
            status=ContractStatus.DRAFT,
            created_at=NOW,
        )
        self.test_case = TestCase(
            id=uuid4(),
            contract_id=self.contract.id,
            skill_id="echo",
            input={"text": "hi"},
            criteria={},
            kind=TestCaseKind.SKILL,
        )
        store.add_contract(self.contract, [self.test_case])
        if approved:
            self.contract = store.approve_contract(self.contract.id, "reviewer", NOW)

    def attestation(self, status: AttestationStatus = AttestationStatus.RUNNING) -> Attestation:
        attestation = Attestation(
            id=uuid4(),
            contract_id=self.contract.id,
            card_version_id=self.card_version.id,
            trigger=AttestationTrigger.MANUAL,
            status=AttestationStatus.QUEUED,
            started_at=NOW,
            budget_limit=Decimal(10),
            cost_total=Decimal(0),
        )
        self.store.add_attestation(attestation)
        if status is not AttestationStatus.QUEUED:
            final = status.is_final
            attestation = attestation.model_copy(
                update={"status": status, "finished_at": NOW if final else None}
            )
            self.store.update_attestation(attestation)
        return attestation

    def run(self, attestation: Attestation, attempt: int = 1, **overrides: object) -> Run:
        data = {
            "id": uuid4(),
            "attestation_id": attestation.id,
            "test_case_id": self.test_case.id,
            "attempt": attempt,
            "verdict": RunVerdict.PASS,
            "judge_layer": JudgeLayer.DETERMINISTIC,
            "rationale": None,
            "latency_ms": 10,
            "cost": Decimal(1),
            "transcript_ref": "ref",
            "started_at": NOW,
            "finished_at": NOW,
        }
        data.update(overrides)
        return Run.model_validate(data)

    def decision(self, attestation: Attestation, decided_by: str = "policy") -> Decision:
        return Decision(
            id=uuid4(),
            attestation_id=attestation.id,
            outcome=DecisionOutcome.FLAG,
            policy_version="unconfigured",
            decided_by=decided_by,
            decided_at=NOW,
        )


def test_round_trips_every_entity(store: EvidenceStore) -> None:
    f = Fixture(store)
    assert store.get_agent(f.agent.id) == f.agent
    assert store.get_card_version(f.card_version.id) == f.card_version
    assert store.find_card_version(f.agent.id, f.card_version.card_hash) == f.card_version
    assert store.find_card_version(f.agent.id, "sha256:other") is None
    assert store.get_contract(f.contract.id) == f.contract
    assert store.list_contracts(f.card_version.id) == [f.contract]
    assert store.list_test_cases(f.contract.id) == [f.test_case]
    attestation = f.attestation()
    assert store.get_attestation(attestation.id) == attestation
    assert store.list_attestations(f.card_version.id) == [attestation]
    run = f.run(attestation)
    store.add_run(run)
    assert store.list_runs(attestation.id) == [run]
    decision = f.decision(attestation)
    store.add_decision(decision)
    assert store.list_decisions(attestation.id) == [decision]


def test_raw_json_is_kept_byte_for_byte(store: EvidenceStore) -> None:
    f = Fixture(store)
    raw = '{ "z":  1,\n\t"a": "two",  "a": "dup" }  '
    card_version = CardVersion(
        id=uuid4(), agent_id=f.agent.id, card_hash="sha256:x", raw_json=raw, fetched_at=NOW
    )
    store.add_card_version(card_version)
    stored = store.get_card_version(card_version.id)
    assert stored is not None and stored.raw_json == raw


def test_rejects_an_attestation_for_a_contract_that_is_not_approved(store: EvidenceStore) -> None:
    f = Fixture(store, approved=False)
    with pytest.raises(StoreError, match="not approved"):
        f.attestation()


def test_rejects_an_attestation_whose_card_version_differs_from_its_contract(
    store: EvidenceStore,
) -> None:
    f = Fixture(store)
    other = CardVersion(
        id=uuid4(), agent_id=f.agent.id, card_hash="sha256:y", raw_json="{}", fetched_at=NOW
    )
    store.add_card_version(other)
    attestation = Attestation(
        id=uuid4(),
        contract_id=f.contract.id,
        card_version_id=other.id,
        trigger=AttestationTrigger.MANUAL,
        status=AttestationStatus.QUEUED,
        started_at=NOW,
        budget_limit=Decimal(1),
        cost_total=Decimal(0),
    )
    with pytest.raises(StoreError, match="card_version_id"):
        store.add_attestation(attestation)


def test_approved_contracts_never_change_except_to_superseded(store: EvidenceStore) -> None:
    f = Fixture(store)
    with pytest.raises(StoreError):
        store.approve_contract(f.contract.id, "again", NOW)
    with pytest.raises(StoreError):
        store.reject_contract(f.contract.id)
    superseded = store.supersede_contract(f.contract.id)
    assert superseded.status is ContractStatus.SUPERSEDED
    assert superseded.approved_by == "reviewer"
    with pytest.raises(StoreError):
        store.supersede_contract(f.contract.id)


def test_a_draft_can_be_rejected_but_a_rejected_contract_cannot_be_approved(
    store: EvidenceStore,
) -> None:
    f = Fixture(store, approved=False)
    rejected = store.reject_contract(f.contract.id)
    assert rejected.status is ContractStatus.REJECTED
    with pytest.raises(StoreError):
        store.approve_contract(f.contract.id, "reviewer", NOW)


def test_rejects_a_second_run_with_an_existing_run_key(store: EvidenceStore) -> None:
    """DR-001: retries never double count."""
    f = Fixture(store)
    attestation = f.attestation()
    store.add_run(f.run(attestation, attempt=1))
    with pytest.raises(StoreError, match="DR-001"):
        store.add_run(f.run(attestation, attempt=1, verdict=RunVerdict.FAIL))
    store.add_run(f.run(attestation, attempt=2))
    assert [r.attempt for r in store.list_runs(attestation.id)] == [1, 2]


def test_rejects_a_run_whose_test_case_belongs_to_another_contract(store: EvidenceStore) -> None:
    f = Fixture(store)
    other = Fixture(store)
    attestation = f.attestation()
    with pytest.raises(StoreError, match="does not belong"):
        store.add_run(f.run(attestation, test_case_id=other.test_case.id))


def test_runs_and_decisions_have_no_update_or_delete(store: EvidenceStore) -> None:
    """DR-002: the port offers no way to change or remove evidence."""
    forbidden = [
        name
        for name in dir(store)
        if name.startswith(("update_run", "delete_", "remove_", "update_decision"))
    ]
    assert forbidden == []


def test_only_mutable_attestation_fields_may_change(store: EvidenceStore) -> None:
    f = Fixture(store)
    attestation = f.attestation()
    with pytest.raises(StoreError, match="Only status"):
        store.update_attestation(attestation.model_copy(update={"budget_limit": Decimal(99)}))
    store.update_attestation(attestation.model_copy(update={"cost_total": Decimal(3)}))
    stored = store.get_attestation(attestation.id)
    assert stored is not None and stored.cost_total == Decimal(3)


def test_rejects_a_decision_for_a_failed_invalidated_or_cancelled_attestation(
    store: EvidenceStore,
) -> None:
    f = Fixture(store)
    for status in (
        AttestationStatus.FAILED,
        AttestationStatus.INVALIDATED,
        AttestationStatus.CANCELLED,
    ):
        attestation = f.attestation(status)
        with pytest.raises(StoreError, match="no decision is made"):
            store.add_decision(f.decision(attestation))


def test_rejects_a_first_decision_whose_decided_by_is_not_policy(store: EvidenceStore) -> None:
    f = Fixture(store)
    attestation = f.attestation()
    with pytest.raises(StoreError, match="policy"):
        store.add_decision(f.decision(attestation, decided_by="reviewer@example.com"))
    store.add_decision(f.decision(attestation))
    store.add_decision(f.decision(attestation, decided_by="reviewer@example.com"))
    assert [d.decided_by for d in store.list_decisions(attestation.id)] == [
        "policy",
        "reviewer@example.com",
    ]


def test_a_decided_attestation_cannot_become_failed_and_an_undecided_one_cannot_complete(
    store: EvidenceStore,
) -> None:
    f = Fixture(store)
    attestation = f.attestation()
    with pytest.raises(StoreError, match="no decision"):
        store.update_attestation(
            attestation.model_copy(
                update={
                    "status": AttestationStatus.COMPLETED,
                    "finished_at": NOW,
                    "signature": "s",
                    "signing_key_id": "k",
                }
            )
        )
    store.add_decision(f.decision(attestation))
    with pytest.raises(StoreError, match="already has a decision"):
        store.update_attestation(
            attestation.model_copy(update={"status": AttestationStatus.FAILED, "finished_at": NOW})
        )
    store.update_attestation(
        attestation.model_copy(
            update={
                "status": AttestationStatus.COMPLETED,
                "finished_at": NOW,
                "signature": "s",
                "signing_key_id": "k",
            }
        )
    )
    stored = store.get_attestation(attestation.id)
    assert stored is not None and stored.status is AttestationStatus.COMPLETED


def test_a_final_attestation_keeps_its_status(store: EvidenceStore) -> None:
    f = Fixture(store)
    attestation = f.attestation(AttestationStatus.FAILED)
    with pytest.raises(StoreError, match="final"):
        store.update_attestation(
            attestation.model_copy(
                update={"status": AttestationStatus.RUNNING, "finished_at": None}
            )
        )
    store.update_attestation(
        attestation.model_copy(update={"signature": "s", "signing_key_id": "k"})
    )


def test_list_runs_orders_by_test_case_then_attempt(store: EvidenceStore) -> None:
    f = Fixture(store)
    attestation = f.attestation()
    for attempt in (3, 1, 2):
        store.add_run(f.run(attestation, attempt=attempt))
    assert [r.attempt for r in store.list_runs(attestation.id)] == [1, 2, 3]


def test_unknown_ids_return_none(store: EvidenceStore) -> None:
    missing = UUID(int=0)
    assert store.get_agent(missing) is None
    assert store.get_card_version(missing) is None
    assert store.get_contract(missing) is None
    assert store.get_attestation(missing) is None
    assert store.list_runs(missing) == []
    assert store.list_decisions(missing) == []
