"""The database rejects what docs/DATA_MODEL.md forbids.

Each test performs real inserts and updates against the migrated schema and
asserts that Postgres refuses the forbidden operation. The list of cases is
CLAUDE_CODE_BRIEF.md section 2.4. Tests run only when DATABASE_URL is set, and
against the database with every migration applied (tests/conftest.py).
"""

from __future__ import annotations

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import errors  # noqa: E402

from tests.db.helpers import (  # noqa: E402
    Conn,
    approved_contract,
    insert_agent,
    insert_attestation,
    insert_card_version,
    insert_contract,
    insert_decision,
    insert_run,
    rejects,
)

pytestmark = pytest.mark.db


def test_rejects_attestation_for_a_contract_that_is_not_approved(db: Conn) -> None:
    agent_id = insert_agent(db)
    card_version_id = insert_card_version(db, agent_id)
    for status in ("draft", "rejected", "superseded"):
        contract_id = insert_contract(db, card_version_id, status=status)
        rejects(
            db,
            errors.RaiseException,
            "INSERT INTO attestation (contract_id, card_version_id, trigger, budget_limit)"
            " VALUES (%s, %s, 'manual'::attestation_trigger, 1)",
            (contract_id, card_version_id),
        )


def test_rejects_changes_to_an_approved_contract_and_its_test_cases(db: Conn) -> None:
    _, contract_id, test_case_id = approved_contract(db)

    rejects(
        db, errors.RaiseException, "UPDATE contract SET version = 2 WHERE id = %s", (contract_id,)
    )
    rejects(
        db,
        errors.RaiseException,
        "UPDATE contract SET approved_by = 'x' WHERE id = %s",
        (contract_id,),
    )
    rejects(
        db,
        errors.RaiseException,
        "UPDATE contract SET status = 'draft' WHERE id = %s",
        (contract_id,),
    )
    rejects(db, errors.RaiseException, "DELETE FROM contract WHERE id = %s", (contract_id,))

    rejects(
        db,
        errors.RaiseException,
        "INSERT INTO test_case (contract_id, skill_id, input, criteria, kind)"
        " VALUES (%s, 's', '{}', '{}', 'skill'::test_case_kind)",
        (contract_id,),
    )
    rejects(
        db,
        errors.RaiseException,
        "UPDATE test_case SET skill_id = 'other' WHERE id = %s",
        (test_case_id,),
    )
    rejects(db, errors.RaiseException, "DELETE FROM test_case WHERE id = %s", (test_case_id,))

    # The one permitted change: approved -> superseded with every other field untouched.
    db.execute("UPDATE contract SET status = 'superseded' WHERE id = %s", (contract_id,))
    assert (
        db.execute("SELECT status FROM contract WHERE id = %s", (contract_id,)).fetchone()[0]
        == "superseded"
    )
    rejects(
        db,
        errors.RaiseException,
        "UPDATE contract SET status = 'approved' WHERE id = %s",
        (contract_id,),
    )


def test_rejects_attestation_whose_card_version_differs_from_its_contract(db: Conn) -> None:
    _, contract_id, _ = approved_contract(db)
    other_card_version_id = insert_card_version(db, insert_agent(db))
    rejects(
        db,
        errors.ForeignKeyViolation,
        "INSERT INTO attestation (contract_id, card_version_id, trigger, budget_limit)"
        " VALUES (%s, %s, 'manual'::attestation_trigger, 1)",
        (contract_id, other_card_version_id),
    )


def test_rejects_a_second_run_with_an_existing_run_key(db: Conn) -> None:
    card_version_id, contract_id, test_case_id = approved_contract(db)
    attestation_id = insert_attestation(db, contract_id, card_version_id)
    insert_run(db, attestation_id, test_case_id, attempt=1)
    with pytest.raises(errors.UniqueViolation), db.transaction():
        insert_run(db, attestation_id, test_case_id, attempt=1)
    insert_run(db, attestation_id, test_case_id, attempt=2)


def test_rejects_a_model_run_without_rationale(db: Conn) -> None:
    card_version_id, contract_id, test_case_id = approved_contract(db)
    attestation_id = insert_attestation(db, contract_id, card_version_id)
    with pytest.raises(errors.CheckViolation), db.transaction():
        insert_run(db, attestation_id, test_case_id, judge_layer="model", rationale=None)
    with pytest.raises(errors.CheckViolation), db.transaction():
        insert_run(db, attestation_id, test_case_id, judge_layer="model", rationale="   ")
    insert_run(db, attestation_id, test_case_id, judge_layer="model", rationale="because")


def test_rejects_a_run_whose_test_case_belongs_to_another_contract(db: Conn) -> None:
    card_version_id, contract_id, _ = approved_contract(db)
    _, _, foreign_test_case_id = approved_contract(db)
    attestation_id = insert_attestation(db, contract_id, card_version_id)
    with pytest.raises(errors.RaiseException), db.transaction():
        insert_run(db, attestation_id, foreign_test_case_id)


def test_rejects_update_delete_and_truncate_on_run_and_decision(db: Conn) -> None:
    card_version_id, contract_id, test_case_id = approved_contract(db)
    attestation_id = insert_attestation(db, contract_id, card_version_id)
    run_id = insert_run(db, attestation_id, test_case_id)
    decision_id = insert_decision(db, attestation_id)

    rejects(db, errors.RaiseException, "UPDATE run SET verdict = 'fail' WHERE id = %s", (run_id,))
    rejects(db, errors.RaiseException, "DELETE FROM run WHERE id = %s", (run_id,))
    rejects(db, errors.RaiseException, "TRUNCATE run")
    rejects(
        db,
        errors.RaiseException,
        "UPDATE decision SET outcome = 'approve' WHERE id = %s",
        (decision_id,),
    )
    rejects(db, errors.RaiseException, "DELETE FROM decision WHERE id = %s", (decision_id,))
    rejects(db, errors.RaiseException, "TRUNCATE decision")


def test_rejects_a_decision_for_a_failed_invalidated_or_cancelled_attestation(db: Conn) -> None:
    card_version_id, contract_id, _ = approved_contract(db)
    for status in ("failed", "invalidated", "cancelled"):
        attestation_id = insert_attestation(db, contract_id, card_version_id, status="running")
        db.execute(
            "UPDATE attestation SET status = %s::attestation_status, finished_at = now() WHERE id = %s",
            (status, attestation_id),
        )
        with pytest.raises(errors.RaiseException), db.transaction():
            insert_decision(db, attestation_id)


def test_rejects_a_first_decision_whose_decided_by_is_not_policy(db: Conn) -> None:
    card_version_id, contract_id, _ = approved_contract(db)
    attestation_id = insert_attestation(db, contract_id, card_version_id)
    with pytest.raises(errors.RaiseException), db.transaction():
        insert_decision(db, attestation_id, decided_by="reviewer@example.com")
    insert_decision(db, attestation_id, decided_by="policy")
    insert_decision(db, attestation_id, decided_by="reviewer@example.com")


def test_rejects_a_completed_attestation_without_decision_or_signature(db: Conn) -> None:
    card_version_id, contract_id, _ = approved_contract(db)
    attestation_id = insert_attestation(db, contract_id, card_version_id)

    # Without a decision the BEFORE UPDATE trigger refuses first (invariant 13), whether or
    # not a signature is present; the CHECK constraint is only reached once a decision exists.
    rejects(
        db,
        errors.RaiseException,
        "UPDATE attestation SET status = 'completed', finished_at = now() WHERE id = %s",
        (attestation_id,),
    )
    rejects(
        db,
        errors.RaiseException,
        "UPDATE attestation SET status = 'completed', finished_at = now(),"
        " signature = 'sig', signing_key_id = 'key' WHERE id = %s",
        (attestation_id,),
    )
    insert_decision(db, attestation_id)
    rejects(
        db,
        errors.CheckViolation,
        "UPDATE attestation SET status = 'completed', finished_at = now() WHERE id = %s",
        (attestation_id,),
    )
    db.execute(
        "UPDATE attestation SET status = 'completed', finished_at = now(),"
        " signature = 'sig', signing_key_id = 'key' WHERE id = %s",
        (attestation_id,),
    )
    assert (
        db.execute("SELECT status FROM attestation WHERE id = %s", (attestation_id,)).fetchone()[0]
        == "completed"
    )


def test_rejects_a_final_status_without_finished_at_and_the_reverse(db: Conn) -> None:
    card_version_id, contract_id, _ = approved_contract(db)
    attestation_id = insert_attestation(db, contract_id, card_version_id)
    rejects(
        db,
        errors.CheckViolation,
        "UPDATE attestation SET status = 'failed' WHERE id = %s",
        (attestation_id,),
    )
    rejects(
        db,
        errors.CheckViolation,
        "UPDATE attestation SET finished_at = now() WHERE id = %s",
        (attestation_id,),
    )
    db.execute(
        "UPDATE attestation SET status = 'failed', finished_at = now() WHERE id = %s",
        (attestation_id,),
    )


def test_raw_json_is_returned_byte_for_byte(db: Conn) -> None:
    raw = '{ "z":  1,\n\t"a": "two",  "a": "dup" }  '
    agent_id = insert_agent(db)
    card_version_id = insert_card_version(db, agent_id, raw_json=raw)
    stored = db.execute(
        "SELECT raw_json FROM card_version WHERE id = %s", (card_version_id,)
    ).fetchone()[0]
    assert stored == raw
