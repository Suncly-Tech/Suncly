"""Row helpers for the database tests: insert the seven entities and assert rejections.

Shared by the constraint tests of migration 0001 and the tests of migration 0002.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

Conn = Any  # psycopg.Connection; kept loose so the module imports without psycopg stubs


def _uuid(row: Any) -> uuid.UUID:
    value: uuid.UUID = row[0]
    return value


def insert_agent(conn: Conn) -> uuid.UUID:
    row = conn.execute(
        "INSERT INTO agent (name, owner, risk_level) VALUES (%s, %s, %s::risk_level) RETURNING id",
        ("Agent", "team", "low"),
    ).fetchone()
    return _uuid(row)


def insert_card_version(
    conn: Conn, agent_id: uuid.UUID, raw_json: str = '{"name": "Agent"}'
) -> uuid.UUID:
    row = conn.execute(
        "INSERT INTO card_version (agent_id, card_hash, raw_json) VALUES (%s, %s, %s) RETURNING id",
        (agent_id, "hash-" + uuid.uuid4().hex, raw_json),
    ).fetchone()
    return _uuid(row)


def insert_contract(conn: Conn, card_version_id: uuid.UUID, status: str = "approved") -> uuid.UUID:
    approved = status == "approved"
    row = conn.execute(
        """
        INSERT INTO contract (card_version_id, version, status, approved_by, approved_at)
        VALUES (%s, 1, %s::contract_status, %s, CASE WHEN %s THEN now() END)
        RETURNING id
        """,
        (card_version_id, status, "reviewer" if approved else None, approved),
    ).fetchone()
    return _uuid(row)


def insert_test_case(conn: Conn, contract_id: uuid.UUID) -> uuid.UUID:
    row = conn.execute(
        """
        INSERT INTO test_case (contract_id, skill_id, input, criteria, kind)
        VALUES (%s, 'skill-1', '{"text": "hi"}', '{}', 'skill'::test_case_kind) RETURNING id
        """,
        (contract_id,),
    ).fetchone()
    return _uuid(row)


def insert_attestation(
    conn: Conn, contract_id: uuid.UUID, card_version_id: uuid.UUID, status: str = "running"
) -> uuid.UUID:
    row = conn.execute(
        """
        INSERT INTO attestation (contract_id, card_version_id, trigger, status, budget_limit)
        VALUES (%s, %s, 'manual'::attestation_trigger, %s::attestation_status, 10) RETURNING id
        """,
        (contract_id, card_version_id, status),
    ).fetchone()
    return _uuid(row)


def insert_run(
    conn: Conn,
    attestation_id: uuid.UUID,
    test_case_id: uuid.UUID,
    attempt: int = 1,
    judge_layer: str = "deterministic",
    rationale: str | None = None,
) -> uuid.UUID:
    row = conn.execute(
        """
        INSERT INTO run (attestation_id, test_case_id, attempt, verdict, judge_layer, rationale,
                         latency_ms, cost, transcript_ref, started_at, finished_at)
        VALUES (%s, %s, %s, 'pass'::run_verdict, %s::judge_layer, %s, 10, 1, 'ref', now(), now())
        RETURNING id
        """,
        (attestation_id, test_case_id, attempt, judge_layer, rationale),
    ).fetchone()
    return _uuid(row)


def insert_decision(conn: Conn, attestation_id: uuid.UUID, decided_by: str = "policy") -> uuid.UUID:
    row = conn.execute(
        """
        INSERT INTO decision (attestation_id, outcome, policy_version, decided_by)
        VALUES (%s, 'flag'::decision_outcome, 'v1', %s) RETURNING id
        """,
        (attestation_id, decided_by),
    ).fetchone()
    return _uuid(row)


def approved_contract(conn: Conn) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """An agent, card version and approved contract with one test case.

    Test cases are added while the contract is a draft; approving it afterwards
    is the only order the migration allows (schema §2).
    """
    agent_id = insert_agent(conn)
    card_version_id = insert_card_version(conn, agent_id)
    contract_id = insert_contract(conn, card_version_id, status="draft")
    test_case_id = insert_test_case(conn, contract_id)
    conn.execute(
        "UPDATE contract SET status = 'approved', approved_by = 'reviewer', approved_at = now()"
        " WHERE id = %s",
        (contract_id,),
    )
    return card_version_id, contract_id, test_case_id


def rejects(
    conn: Conn, error: type[Exception], statement: str, params: tuple[Any, ...] = ()
) -> None:
    """Assert the statement fails with ``error`` without poisoning the outer transaction."""
    with pytest.raises(error), conn.transaction():
        conn.execute(statement, params)
