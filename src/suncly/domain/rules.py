"""The store rules every Evidence store implementation enforces (ports/store.py).

These are the application-level twins of the constraints and triggers in
``db/migrations/0001_initial_schema.sql``. The file store applies them because
it has no database; the Postgres store applies them too, so both stores refuse
the same operations with the same messages before the database ever sees them.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence

from suncly.domain.errors import StoreError
from suncly.domain.models import (
    POLICY_DECIDED_BY,
    UNDECIDED_ATTESTATION_STATUSES,
    Attestation,
    AttestationStatus,
    Contract,
    ContractStatus,
    Decision,
    Run,
    RunKey,
    TestCase,
)

#: The attestation fields that may change after creation (DATA_MODEL.md: Mutability).
MUTABLE_ATTESTATION_FIELDS = frozenset(
    {"status", "cost_total", "finished_at", "signature", "signing_key_id"}
)


def check_attestation_insert(attestation: Attestation, contract: Contract | None) -> None:
    """Invariants 4 and 5: an approved contract, and the contract's own card version."""
    if contract is None:
        raise StoreError(
            "The attestation references a contract that does not exist.",
            f"No contract has id {attestation.contract_id}.",
        )
    if contract.status is not ContractStatus.APPROVED:
        raise StoreError(
            "An attestation cannot be created for this contract.",
            f"Contract {contract.id} is {contract.status.value}, not approved (schema §4).",
            "Approve the contract first; nothing runs before a human approves it.",
        )
    if contract.card_version_id != attestation.card_version_id:
        raise StoreError(
            "The attestation's card_version_id differs from its contract's.",
            "Proposed invariant 5 (OQ-D6) requires them to be equal.",
        )


def check_attestation_update(old: Attestation, new: Attestation, has_decision: bool) -> None:
    """Only the mutable fields change; status transitions respect schema §11."""
    if old.id != new.id:
        raise StoreError("An attestation update must keep the same id.")
    changed = {
        name
        for name in Attestation.model_fields
        if getattr(old, name) != getattr(new, name) and name not in MUTABLE_ATTESTATION_FIELDS
    }
    if changed:
        raise StoreError(
            "Only status, cost_total, finished_at, signature and signing_key_id of an "
            "attestation may change.",
            f"The update also changes {', '.join(sorted(changed))}.",
        )
    if old.status.is_final and new.status is not old.status:
        raise StoreError(
            "A final attestation does not change status.",
            f"Attestation {old.id} is already {old.status.value}.",
        )
    if new.status is not old.status:
        if new.status in UNDECIDED_ATTESTATION_STATUSES and has_decision:
            raise StoreError(
                f"Attestation {old.id} already has a decision and cannot become "
                f"{new.status.value} (schema §11)."
            )
        if new.status is AttestationStatus.COMPLETED and not has_decision:
            raise StoreError(
                f"Attestation {old.id} has no decision and cannot become completed (invariant 13)."
            )


def check_run_insert(
    run: Run,
    attestation: Attestation | None,
    test_case: TestCase | None,
    existing_keys: Collection[RunKey],
) -> None:
    """DR-001 (unique run key) and the derived rule that the test case is the contract's."""
    if attestation is None:
        raise StoreError(f"Run {run.id} references an attestation that does not exist.")
    if test_case is None:
        raise StoreError(f"Run {run.id} references a test case that does not exist.")
    if run.key in existing_keys:
        raise StoreError(
            "A run with this run key is already recorded.",
            f"Run key {run.key} exists; retries never double count (DR-001).",
        )
    if test_case.contract_id != attestation.contract_id:
        raise StoreError(
            f"test_case {run.test_case_id} does not belong to the contract of attestation "
            f"{run.attestation_id}."
        )


def check_decision_insert(
    decision: Decision, attestation: Attestation | None, existing: Sequence[Decision]
) -> None:
    """Schema §11 and invariant 11."""
    if attestation is None:
        raise StoreError(f"Decision {decision.id} references an attestation that does not exist.")
    if attestation.status in UNDECIDED_ATTESTATION_STATUSES:
        raise StoreError(
            f"Attestation {attestation.id} is {attestation.status.value}: no decision is made "
            "for it (schema §11)."
        )
    if not existing and decision.decided_by != POLICY_DECIDED_BY:
        raise StoreError(
            f"The first decision for attestation {attestation.id} must have decided_by = "
            f"'{POLICY_DECIDED_BY}' (schema §4)."
        )


def check_contract_transition(contract: Contract, new_status: ContractStatus) -> None:
    """Schema §2: approved contracts never change, except the move to superseded (OQ-D5)."""
    allowed = {
        ContractStatus.DRAFT: {ContractStatus.APPROVED, ContractStatus.REJECTED},
        ContractStatus.APPROVED: {ContractStatus.SUPERSEDED},
        ContractStatus.REJECTED: set[ContractStatus](),
        ContractStatus.SUPERSEDED: set[ContractStatus](),
    }
    if new_status not in allowed[contract.status]:
        raise StoreError(
            f"Contract {contract.id} is {contract.status.value} and cannot become "
            f"{new_status.value}.",
            "An approved contract is immutable; an edit creates a new version (schema §2).",
        )
