"""The Evidence store port (schema §2).

Both implementations, the file store and the Postgres store, satisfy this
Protocol and pass the same contract test suite. Every rule the database
enforces with constraints and triggers (db/README.md) is enforced by every
implementation, so behaviour does not depend on the backend:

- ``run`` and ``decision`` records are append-only (schema §8, DR-002);
- a second run with an existing run key is rejected (DR-001, invariant 6);
- a run's test case belongs to the attestation's contract;
- an attestation is created only for an approved contract (invariant 4) and
  its ``card_version_id`` equals the contract's (invariant 5);
- only ``status``, ``cost_total``, ``finished_at``, ``signature`` and
  ``signing_key_id`` of an attestation change (DATA_MODEL.md: Mutability);
- no decision for a failed, invalidated or cancelled attestation (schema §11,
  OQ-D6), the first decision is the policy's (invariant 11), and a completed
  attestation has a decision and a signature (invariant 13);
- an approved contract and its test cases never change, except the move to
  ``superseded`` (schema §2, OQ-D5).

Violations raise ``StoreError``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from suncly.domain.models import (
    Agent,
    Attestation,
    CardVersion,
    Contract,
    Decision,
    Run,
    TestCase,
)


class EvidenceStore(Protocol):
    """Persistence for the seven entities."""

    # agent -----------------------------------------------------------------
    def get_agent(self, agent_id: UUID) -> Agent | None: ...

    def add_agent(self, agent: Agent) -> None: ...

    # card_version ----------------------------------------------------------
    def get_card_version(self, card_version_id: UUID) -> CardVersion | None: ...

    def find_card_version(self, agent_id: UUID, card_hash: str) -> CardVersion | None:
        """The card version of ``agent_id`` with ``card_hash``, if one was recorded."""
        ...

    def add_card_version(self, card_version: CardVersion) -> None: ...

    def list_card_versions(self, agent_id: UUID) -> list[CardVersion]:
        """Card versions of an agent, oldest fetch first."""
        ...

    # contract and test_case ------------------------------------------------
    def get_contract(self, contract_id: UUID) -> Contract | None: ...

    def list_contracts(self, card_version_id: UUID) -> list[Contract]:
        """Contracts of a card version, oldest version first."""
        ...

    def add_contract(self, contract: Contract, test_cases: list[TestCase]) -> None:
        """Record a contract with its test cases atomically."""
        ...

    def list_test_cases(self, contract_id: UUID) -> list[TestCase]: ...

    def approve_contract(
        self, contract_id: UUID, approved_by: str, approved_at: datetime
    ) -> Contract:
        """``draft`` → ``approved`` (schema §2). Any other transition is refused."""
        ...

    def reject_contract(self, contract_id: UUID) -> Contract:
        """``draft`` → ``rejected``."""
        ...

    def supersede_contract(self, contract_id: UUID) -> Contract:
        """``approved`` → ``superseded``, the only change allowed to an approved contract."""
        ...

    # attestation -----------------------------------------------------------
    def get_attestation(self, attestation_id: UUID) -> Attestation | None: ...

    def list_attestations(self, card_version_id: UUID) -> list[Attestation]:
        """Attestations of a card version, oldest first."""
        ...

    def add_attestation(self, attestation: Attestation) -> None: ...

    def update_attestation(self, attestation: Attestation) -> None:
        """Replace the stored record. Only the mutable fields may differ."""
        ...

    # run -------------------------------------------------------------------
    def add_run(self, run: Run) -> None: ...

    def list_runs(self, attestation_id: UUID) -> list[Run]:
        """Runs of an attestation, ordered by test case then attempt."""
        ...

    # decision --------------------------------------------------------------
    def add_decision(self, decision: Decision) -> None: ...

    def list_decisions(self, attestation_id: UUID) -> list[Decision]:
        """Decisions of an attestation, oldest first."""
        ...

    def close(self) -> None: ...
