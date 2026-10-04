"""The Postgres Evidence store, on exactly the seven tables of ``db/migrations``.

Selected when ``DATABASE_URL`` is set. The database enforces the rules with
constraints and triggers; the store checks the same rules first so both stores
answer with the same ``StoreError`` messages, and maps anything the database
still refuses to ``StoreError``.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from suncly.domain import rules
from suncly.domain.errors import StoreError
from suncly.domain.models import (
    Agent,
    Attestation,
    CardVersion,
    Contract,
    ContractStatus,
    Decision,
    Run,
    TestCase,
)

Row = dict[str, Any]

INSERT_CONTRACT = """
INSERT INTO contract (id, card_version_id, version, status, created_at, approved_by, approved_at)
VALUES (%s, %s, %s, %s::contract_status, %s, %s, %s)
"""
INSERT_TEST_CASE = """
INSERT INTO test_case (id, contract_id, skill_id, input, criteria, kind)
VALUES (%s, %s, %s, %s, %s, %s::test_case_kind)
"""
UPDATE_CONTRACT = """
UPDATE contract SET status = %s::contract_status, approved_by = %s, approved_at = %s WHERE id = %s
"""
INSERT_ATTESTATION = """
INSERT INTO attestation (id, contract_id, card_version_id, trigger, status, started_at,
                         finished_at, budget_limit, cost_total, signature, signing_key_id)
VALUES (%s, %s, %s, %s::attestation_trigger, %s::attestation_status, %s, %s, %s, %s, %s, %s)
"""
UPDATE_ATTESTATION = """
UPDATE attestation SET status = %s::attestation_status, cost_total = %s, finished_at = %s,
                       signature = %s, signing_key_id = %s
WHERE id = %s
"""
INSERT_RUN = """
INSERT INTO run (id, attestation_id, test_case_id, attempt, verdict, judge_layer, rationale,
                 latency_ms, cost, transcript_ref, started_at, finished_at)
VALUES (%s, %s, %s, %s, %s::run_verdict, %s::judge_layer, %s, %s, %s, %s, %s, %s)
"""
INSERT_DECISION = """
INSERT INTO decision (id, attestation_id, outcome, policy_version, decided_by, decided_at)
VALUES (%s, %s, %s::decision_outcome, %s, %s, %s)
"""


class PostgresEvidenceStore:
    def __init__(self, database_url: str) -> None:
        try:
            self._conn = psycopg.connect(database_url, row_factory=dict_row, autocommit=True)
        except psycopg.Error as exc:
            raise StoreError(
                "The database cannot be reached.",
                f"Connecting with DATABASE_URL failed: {type(exc).__name__}.",
                "Check DATABASE_URL and that the database accepts connections; "
                "run `suncly db check`.",
            ) from exc
        self._lock = threading.RLock()

    @contextmanager
    def _tx(self) -> Iterator[psycopg.Connection[Row]]:
        with self._lock:
            try:
                with self._conn.transaction():
                    yield self._conn
            except psycopg.Error as exc:
                raise StoreError(
                    "The database refused the operation.",
                    (exc.diag.message_primary or str(exc)).strip(),
                ) from exc

    def _one(self, query: str, params: Sequence[object]) -> Row | None:
        with self._lock:
            return self._conn.execute(query, params).fetchone()

    def _all(self, query: str, params: Sequence[object]) -> list[Row]:
        with self._lock:
            return self._conn.execute(query, params).fetchall()

    # -- agent -------------------------------------------------------------------

    def get_agent(self, agent_id: UUID) -> Agent | None:
        row = self._one("SELECT * FROM agent WHERE id = %s", (agent_id,))
        return Agent.model_validate(row) if row else None

    def add_agent(self, agent: Agent) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO agent (id, name, owner, risk_level)"
                " VALUES (%s, %s, %s, %s::risk_level)",
                (agent.id, agent.name, agent.owner, agent.risk_level.value),
            )

    # -- card_version ------------------------------------------------------------

    def get_card_version(self, card_version_id: UUID) -> CardVersion | None:
        row = self._one("SELECT * FROM card_version WHERE id = %s", (card_version_id,))
        return CardVersion.model_validate(row) if row else None

    def find_card_version(self, agent_id: UUID, card_hash: str) -> CardVersion | None:
        row = self._one(
            "SELECT * FROM card_version WHERE agent_id = %s AND card_hash = %s"
            " ORDER BY fetched_at LIMIT 1",
            (agent_id, card_hash),
        )
        return CardVersion.model_validate(row) if row else None

    def add_card_version(self, card_version: CardVersion) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO card_version (id, agent_id, card_hash, raw_json, fetched_at)"
                " VALUES (%s, %s, %s, %s, %s)",
                (
                    card_version.id,
                    card_version.agent_id,
                    card_version.card_hash,
                    card_version.raw_json,
                    card_version.fetched_at,
                ),
            )

    # -- contract and test_case --------------------------------------------------

    def get_contract(self, contract_id: UUID) -> Contract | None:
        row = self._one("SELECT * FROM contract WHERE id = %s", (contract_id,))
        return Contract.model_validate(row) if row else None

    def list_contracts(self, card_version_id: UUID) -> list[Contract]:
        rows = self._all(
            "SELECT * FROM contract WHERE card_version_id = %s ORDER BY version, created_at",
            (card_version_id,),
        )
        return [Contract.model_validate(row) for row in rows]

    def add_contract(self, contract: Contract, test_cases: list[TestCase]) -> None:
        if any(tc.contract_id != contract.id for tc in test_cases):
            raise StoreError("Every test case must belong to the contract being added.")
        with self._tx() as conn:
            conn.execute(
                INSERT_CONTRACT,
                (
                    contract.id,
                    contract.card_version_id,
                    contract.version,
                    contract.status.value,
                    contract.created_at,
                    contract.approved_by,
                    contract.approved_at,
                ),
            )
            for tc in test_cases:
                conn.execute(
                    INSERT_TEST_CASE,
                    (
                        tc.id,
                        tc.contract_id,
                        tc.skill_id,
                        Jsonb(tc.input),
                        Jsonb(tc.criteria),
                        tc.kind.value,
                    ),
                )

    def list_test_cases(self, contract_id: UUID) -> list[TestCase]:
        rows = self._all(
            "SELECT * FROM test_case WHERE contract_id = %s ORDER BY id", (contract_id,)
        )
        return [TestCase.model_validate(row) for row in rows]

    def _transition(
        self, contract_id: UUID, new_status: ContractStatus, **changes: object
    ) -> Contract:
        with self._tx() as conn:
            contract = self.get_contract(contract_id)
            if contract is None:
                raise StoreError(f"Contract {contract_id} does not exist.")
            rules.check_contract_transition(contract, new_status)
            data = contract.model_dump()
            data.update(changes)
            data["status"] = new_status
            updated = Contract.model_validate(data)
            conn.execute(
                UPDATE_CONTRACT,
                (updated.status.value, updated.approved_by, updated.approved_at, contract_id),
            )
            return updated

    def approve_contract(
        self, contract_id: UUID, approved_by: str, approved_at: datetime
    ) -> Contract:
        return self._transition(
            contract_id, ContractStatus.APPROVED, approved_by=approved_by, approved_at=approved_at
        )

    def reject_contract(self, contract_id: UUID) -> Contract:
        return self._transition(contract_id, ContractStatus.REJECTED)

    def supersede_contract(self, contract_id: UUID) -> Contract:
        return self._transition(contract_id, ContractStatus.SUPERSEDED)

    # -- attestation -------------------------------------------------------------

    def get_attestation(self, attestation_id: UUID) -> Attestation | None:
        row = self._one("SELECT * FROM attestation WHERE id = %s", (attestation_id,))
        return Attestation.model_validate(row) if row else None

    def list_attestations(self, card_version_id: UUID) -> list[Attestation]:
        rows = self._all(
            "SELECT * FROM attestation WHERE card_version_id = %s ORDER BY started_at",
            (card_version_id,),
        )
        return [Attestation.model_validate(row) for row in rows]

    def add_attestation(self, attestation: Attestation) -> None:
        rules.check_attestation_insert(attestation, self.get_contract(attestation.contract_id))
        with self._tx() as conn:
            conn.execute(
                INSERT_ATTESTATION,
                (
                    attestation.id,
                    attestation.contract_id,
                    attestation.card_version_id,
                    attestation.trigger.value,
                    attestation.status.value,
                    attestation.started_at,
                    attestation.finished_at,
                    attestation.budget_limit,
                    attestation.cost_total,
                    attestation.signature,
                    attestation.signing_key_id,
                ),
            )

    def update_attestation(self, attestation: Attestation) -> None:
        with self._tx() as conn:
            old = self.get_attestation(attestation.id)
            if old is None:
                raise StoreError(f"Attestation {attestation.id} does not exist.")
            has_decision = bool(self.list_decisions(attestation.id))
            rules.check_attestation_update(old, attestation, has_decision)
            conn.execute(
                UPDATE_ATTESTATION,
                (
                    attestation.status.value,
                    attestation.cost_total,
                    attestation.finished_at,
                    attestation.signature,
                    attestation.signing_key_id,
                    attestation.id,
                ),
            )

    # -- run (append-only) -------------------------------------------------------

    def add_run(self, run: Run) -> None:
        with self._tx() as conn:
            attestation = self.get_attestation(run.attestation_id)
            row = self._one("SELECT * FROM test_case WHERE id = %s", (run.test_case_id,))
            test_case = TestCase.model_validate(row) if row else None
            existing = {r.key for r in self.list_runs(run.attestation_id)}
            rules.check_run_insert(run, attestation, test_case, existing)
            conn.execute(
                INSERT_RUN,
                (
                    run.id,
                    run.attestation_id,
                    run.test_case_id,
                    run.attempt,
                    run.verdict.value,
                    run.judge_layer.value,
                    run.rationale,
                    run.latency_ms,
                    run.cost,
                    run.transcript_ref,
                    run.started_at,
                    run.finished_at,
                ),
            )

    def list_runs(self, attestation_id: UUID) -> list[Run]:
        rows = self._all(
            "SELECT * FROM run WHERE attestation_id = %s ORDER BY test_case_id::text, attempt",
            (attestation_id,),
        )
        return [Run.model_validate(row) for row in rows]

    # -- decision (append-only) --------------------------------------------------

    def add_decision(self, decision: Decision) -> None:
        with self._tx() as conn:
            existing = self.list_decisions(decision.attestation_id)
            attestation = self.get_attestation(decision.attestation_id)
            rules.check_decision_insert(decision, attestation, existing)
            conn.execute(
                INSERT_DECISION,
                (
                    decision.id,
                    decision.attestation_id,
                    decision.outcome.value,
                    decision.policy_version,
                    decision.decided_by,
                    decision.decided_at,
                ),
            )

    def list_decisions(self, attestation_id: UUID) -> list[Decision]:
        rows = self._all(
            "SELECT * FROM decision WHERE attestation_id = %s ORDER BY decided_at, id",
            (attestation_id,),
        )
        return [Decision.model_validate(row) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
