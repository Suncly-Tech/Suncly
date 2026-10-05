"""Migration 0002: row level security on the seven tables, fixed search paths on the guards.

Supabase's Security Advisor flagged both. The tests apply the migrations to the
test database in different orders and assert what the migration promises: it is
idempotent, ``suncly db migrate`` and ``db check`` detect it, the table owner
keeps full access, a role without policies gets none, and the guards still
reject what they rejected before. Tests run only when DATABASE_URL is set.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
from click.testing import CliRunner  # noqa: E402
from psycopg import errors  # noqa: E402

from suncly.adapters.postgres.migrate import (  # noqa: E402
    FUNCTIONS,
    MIGRATIONS,
    TABLES,
    apply_migration,
    check_schema,
    expected_function_bodies,
    function_search_paths,
    function_state,
    rls_state,
)
from suncly.cli import exit_codes  # noqa: E402
from suncly.cli.main import main  # noqa: E402
from tests.db.helpers import (  # noqa: E402
    Conn,
    approved_contract,
    insert_agent,
    insert_attestation,
    insert_contract,
    insert_decision,
    insert_run,
    rejects,
)

pytestmark = pytest.mark.db

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"
EMPTY_SEARCH_PATH = '""'  # what ``SET search_path = ''`` stores in pg_proc.proconfig
#: The guards that read other tables; 0002 qualifies their bodies. The other two guards
#: (suncly_forbid_change, suncly_contract_guard) keep the bodies of 0001.
QUALIFIED_FUNCTIONS = (
    "suncly_test_case_guard",
    "suncly_attestation_guard",
    "suncly_run_guard",
    "suncly_decision_guard",
)


def sql(name: str) -> str:
    return (MIGRATIONS_DIR / name).read_text(encoding="utf-8")


def reset_schema(database_url: str, *names: str) -> None:
    """Recreate ``public`` and apply the named migration files, in order."""
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        for name in names:
            conn.execute(sql(name))


@pytest.fixture
def fresh_database(database_url: str) -> Iterator[str]:
    """An empty ``public`` schema for one test; every migration is applied again afterwards."""
    reset_schema(database_url)
    try:
        yield database_url
    finally:
        reset_schema(database_url, *MIGRATIONS)


def rls_problems(problems: list[str]) -> list[str]:
    return [p for p in problems if p.startswith("row level security")]


def search_path_problems(problems: list[str]) -> list[str]:
    return [p for p in problems if p.endswith("has no fixed search_path")]


def body_problems(problems: list[str]) -> list[str]:
    return [p for p in problems if " does not have the body of " in p]


# -- applying the migration ------------------------------------------------------


def test_a_fresh_database_gets_both_migrations(fresh_database: str) -> None:
    assert apply_migration(fresh_database) == "applied " + ", ".join(MIGRATIONS)
    assert check_schema(fresh_database) == []
    with psycopg.connect(fresh_database) as conn:
        assert rls_state(conn) == dict.fromkeys(TABLES, (True, False))
        assert function_search_paths(conn) == dict.fromkeys(FUNCTIONS, EMPTY_SEARCH_PATH)
    assert apply_migration(fresh_database) == "already applied"


def test_a_database_holding_only_0001_gets_0002(fresh_database: str) -> None:
    reset_schema(fresh_database, MIGRATIONS[0])
    with psycopg.connect(fresh_database) as conn:
        assert rls_state(conn) == dict.fromkeys(TABLES, (False, False))
        assert function_search_paths(conn) == dict.fromkeys(FUNCTIONS)

    problems = check_schema(fresh_database)
    assert rls_problems(problems) == [
        f"row level security is disabled on table {name}" for name in TABLES
    ]
    assert search_path_problems(problems) == [
        f"function {name} has no fixed search_path" for name in FUNCTIONS
    ]
    assert body_problems(problems) == [
        f"function {name} does not have the body of {MIGRATIONS[1]}" for name in QUALIFIED_FUNCTIONS
    ]
    assert len(problems) == len(TABLES) + len(FUNCTIONS) + len(QUALIFIED_FUNCTIONS)

    assert apply_migration(fresh_database) == f"applied {MIGRATIONS[1]}"
    assert check_schema(fresh_database) == []
    assert apply_migration(fresh_database) == "already applied"


def test_0002_is_idempotent_and_safe_after_rls_was_enabled_by_hand(fresh_database: str) -> None:
    reset_schema(fresh_database, MIGRATIONS[0])
    with psycopg.connect(fresh_database, autocommit=True) as conn:
        for name in TABLES:
            conn.execute(f"ALTER TABLE public.{name} ENABLE ROW LEVEL SECURITY")
        conn.execute(sql(MIGRATIONS[1]))
        conn.execute(sql(MIGRATIONS[1]))
        policies = conn.execute(
            "SELECT count(*) FROM pg_policies WHERE schemaname = 'public'"
        ).fetchone()
        assert policies is not None and policies[0] == 0
        assert rls_state(conn) == dict.fromkeys(TABLES, (True, False))
        assert function_search_paths(conn) == dict.fromkeys(FUNCTIONS, EMPTY_SEARCH_PATH)
    assert check_schema(fresh_database) == []
    assert apply_migration(fresh_database) == "already applied"


def test_forced_row_level_security_is_reported_and_cleared(fresh_database: str) -> None:
    """FORCE would apply the empty policy set to the owner too and lock the store out."""
    reset_schema(fresh_database, *MIGRATIONS)
    with psycopg.connect(fresh_database, autocommit=True) as conn:
        conn.execute("ALTER TABLE public.run FORCE ROW LEVEL SECURITY")
    assert check_schema(fresh_database) == [
        "row level security is forced on table run, which locks out the table owner"
    ]
    assert apply_migration(fresh_database) == f"applied {MIGRATIONS[1]}"
    assert check_schema(fresh_database) == []
    with psycopg.connect(fresh_database) as conn:
        assert rls_state(conn) == dict.fromkeys(TABLES, (True, False))


def test_a_hand_run_alter_function_on_the_0001_bodies_is_detected_and_repaired(
    fresh_database: str,
) -> None:
    """Supabase's advisor suggests ``ALTER FUNCTION ... SET search_path = ''``.

    Run on the bodies of 0001, that satisfies the lint but breaks every guard that
    reads another table, because nothing resolves under an empty search_path. The
    check compares the bodies with 0002, and migrate repairs them.
    """
    reset_schema(fresh_database, MIGRATIONS[0])
    with psycopg.connect(fresh_database, autocommit=True) as conn:
        for name in FUNCTIONS:
            conn.execute(f"ALTER FUNCTION public.{name}() SET search_path = ''")
        assert function_search_paths(conn) == dict.fromkeys(FUNCTIONS, EMPTY_SEARCH_PATH)
    problems = check_schema(fresh_database)
    assert search_path_problems(problems) == []
    assert body_problems(problems) == [
        f"function {name} does not have the body of {MIGRATIONS[1]}" for name in QUALIFIED_FUNCTIONS
    ]
    assert len(problems) == len(TABLES) + len(QUALIFIED_FUNCTIONS)
    assert apply_migration(fresh_database) == f"applied {MIGRATIONS[1]}"
    assert check_schema(fresh_database) == []
    with psycopg.connect(fresh_database) as conn:
        bodies = expected_function_bodies()
        assert {name: body for name, (_, body) in function_state(conn).items()} == bodies


def test_check_reports_a_guard_whose_search_path_was_reset(fresh_database: str) -> None:
    reset_schema(fresh_database, *MIGRATIONS)
    with psycopg.connect(fresh_database, autocommit=True) as conn:
        conn.execute("ALTER FUNCTION public.suncly_run_guard() RESET search_path")
    assert check_schema(fresh_database) == ["function suncly_run_guard has no fixed search_path"]
    assert apply_migration(fresh_database) == f"applied {MIGRATIONS[1]}"
    assert check_schema(fresh_database) == []


def test_the_cli_migrates_checks_and_repairs_the_database(
    fresh_database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``suncly db migrate`` and ``suncly db check`` detect and verify both changes."""
    monkeypatch.setenv("DATABASE_URL", fresh_database)
    home = ["--home", str(tmp_path / "home")]
    runner = CliRunner()

    checked = runner.invoke(main, [*home, "db", "check"])
    assert checked.exit_code == exit_codes.VERIFICATION_FAILED
    assert "table agent is missing" in checked.output

    migrated = runner.invoke(main, [*home, "db", "migrate"])
    assert migrated.exit_code == exit_codes.OK
    assert migrated.output.strip() == "Migrations: applied " + ", ".join(MIGRATIONS) + "."
    checked = runner.invoke(main, [*home, "db", "check"])
    assert checked.exit_code == exit_codes.OK
    assert "Schema check passed" in checked.output
    assert "row level security is enabled on every table" in checked.output
    assert runner.invoke(main, [*home, "db", "migrate"]).output.strip() == (
        "Migrations: already applied."
    )

    with psycopg.connect(fresh_database, autocommit=True) as conn:
        conn.execute("ALTER TABLE public.decision FORCE ROW LEVEL SECURITY")
        conn.execute("ALTER FUNCTION public.suncly_run_guard() RESET search_path")
    checked = runner.invoke(main, [*home, "db", "check"])
    assert checked.exit_code == exit_codes.VERIFICATION_FAILED
    assert "row level security is forced on table decision" in checked.output
    assert "function suncly_run_guard has no fixed search_path" in checked.output
    assert "Run `suncly db migrate`" in checked.output
    repaired = runner.invoke(main, [*home, "db", "migrate"])
    assert repaired.output.strip() == f"Migrations: applied {MIGRATIONS[1]}."
    assert runner.invoke(main, [*home, "db", "check"]).exit_code == exit_codes.OK


# -- the migrated database -------------------------------------------------------


def test_rls_is_enabled_but_not_forced_on_the_seven_tables(db: Conn) -> None:
    assert rls_state(db) == dict.fromkeys(TABLES, (True, False))


def test_the_six_guard_functions_have_an_empty_fixed_search_path(db: Conn) -> None:
    assert function_search_paths(db) == dict.fromkeys(FUNCTIONS, EMPTY_SEARCH_PATH)


def test_the_table_owner_keeps_full_access_with_rls_enabled(db: Conn) -> None:
    """The store connects as the role that ran the migrations; RLS never restricts the owner."""
    current_user = db.execute("SELECT current_user").fetchone()[0]
    owners = db.execute(
        "SELECT DISTINCT tableowner FROM pg_tables"
        " WHERE schemaname = current_schema() AND tablename = ANY(%s)",
        (list(TABLES),),
    ).fetchall()
    assert [row[0] for row in owners] == [current_user]

    agent_id = insert_agent(db)
    assert db.execute("SELECT name FROM agent WHERE id = %s", (agent_id,)).fetchone() == ("Agent",)
    db.execute("UPDATE agent SET name = 'renamed' WHERE id = %s", (agent_id,))
    assert db.execute("SELECT name FROM agent WHERE id = %s", (agent_id,)).fetchone() == (
        "renamed",
    )
    card_version_id, contract_id, test_case_id = approved_contract(db)
    attestation_id = insert_attestation(db, contract_id, card_version_id)
    insert_run(db, attestation_id, test_case_id)
    insert_decision(db, attestation_id)
    counts = db.execute(
        "SELECT (SELECT count(*) FROM run WHERE attestation_id = %s),"
        " (SELECT count(*) FROM decision WHERE attestation_id = %s)",
        (attestation_id, attestation_id),
    ).fetchone()
    assert counts == (1, 1)


def test_a_role_without_policies_sees_no_rows_and_cannot_insert(db: Conn) -> None:
    """With row level security on and no policies, any other role is locked out."""
    # The insert comes first so that the connection is inside the fixture's transaction
    # when the role is created: the block below is then a savepoint, and the role is
    # rolled back with the test instead of being committed to the cluster.
    agent_id = insert_agent(db)
    assert db.info.transaction_status == psycopg.pq.TransactionStatus.INTRANS
    role = f"suncly_rls_probe_{uuid.uuid4().hex[:8]}"
    try:
        with db.transaction():
            db.execute(f'CREATE ROLE "{role}" NOLOGIN')
    except errors.InsufficientPrivilege:
        pytest.skip("the test database role may not create roles")
    db.execute(f'GRANT USAGE ON SCHEMA public TO "{role}"')
    db.execute(f'GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO "{role}"')

    db.execute(f'SET ROLE "{role}"')
    try:
        assert db.execute("SELECT count(*) FROM agent").fetchone() == (0,)
        rejects(
            db,
            errors.InsufficientPrivilege,
            "INSERT INTO agent (name, owner, risk_level) VALUES ('x', 'y', 'low'::risk_level)",
        )
    finally:
        db.execute("RESET ROLE")
    assert db.execute("SELECT count(*) FROM agent WHERE id = %s", (agent_id,)).fetchone() == (1,)
    # The role is created inside the test's transaction and rolled back with it.


# -- the guards after the change ---------------------------------------------------


def test_the_guards_still_reject_update_delete_and_truncate(db: Conn) -> None:
    card_version_id, contract_id, test_case_id = approved_contract(db)
    attestation_id = insert_attestation(db, contract_id, card_version_id)
    run_id = insert_run(db, attestation_id, test_case_id)
    decision_id = insert_decision(db, attestation_id)
    for statement, params in (
        ("UPDATE run SET verdict = 'fail' WHERE id = %s", (run_id,)),
        ("DELETE FROM run WHERE id = %s", (run_id,)),
        ("TRUNCATE run", ()),
        ("UPDATE decision SET outcome = 'approve' WHERE id = %s", (decision_id,)),
        ("DELETE FROM decision WHERE id = %s", (decision_id,)),
        ("TRUNCATE decision", ()),
        ("UPDATE contract SET version = 2 WHERE id = %s", (contract_id,)),
        ("DELETE FROM contract WHERE id = %s", (contract_id,)),
        ("UPDATE test_case SET skill_id = 'other' WHERE id = %s", (test_case_id,)),
        ("DELETE FROM test_case WHERE id = %s", (test_case_id,)),
    ):
        rejects(db, errors.RaiseException, statement, params)


def test_the_guards_that_read_other_tables_still_resolve_them(db: Conn) -> None:
    """With an empty search_path, every table and type a guard uses is schema-qualified.

    A wrong qualification would surface as an undefined table or type, not as the
    guard's own exception, and the permitted operations below would fail too.
    """
    card_version_id, contract_id, _ = approved_contract(db)
    attestation_id = insert_attestation(db, contract_id, card_version_id)

    # decision_guard reads attestation and decision.
    rejects(
        db,
        errors.RaiseException,
        "INSERT INTO decision (attestation_id, outcome, policy_version, decided_by)"
        " VALUES (%s, 'flag'::decision_outcome, 'v1', 'reviewer@example.com')",
        (attestation_id,),
    )
    insert_decision(db, attestation_id, decided_by="policy")
    insert_decision(db, attestation_id, decided_by="reviewer@example.com")

    # attestation_guard reads contract on insert, and decision on a status change.
    rejects(
        db,
        errors.RaiseException,
        "UPDATE attestation SET status = 'failed', finished_at = now() WHERE id = %s",
        (attestation_id,),
    )
    draft_id = insert_contract(db, card_version_id, status="draft")
    rejects(
        db,
        errors.RaiseException,
        "INSERT INTO attestation (contract_id, card_version_id, trigger, budget_limit)"
        " VALUES (%s, %s, 'manual'::attestation_trigger, 1)",
        (draft_id, card_version_id),
    )

    # test_case_guard reads contract.
    rejects(
        db,
        errors.RaiseException,
        "INSERT INTO test_case (contract_id, skill_id, input, criteria, kind)"
        " VALUES (%s, 's', '{}', '{}', 'skill'::test_case_kind)",
        (contract_id,),
    )

    # run_guard reads attestation and test_case.
    _, _, foreign_test_case_id = approved_contract(db)
    with pytest.raises(errors.RaiseException), db.transaction():
        insert_run(db, attestation_id, foreign_test_case_id)

    # The permitted operations still go through: a second decision above, and here
    # the move to superseded and a completed, signed attestation.
    db.execute("UPDATE contract SET status = 'superseded' WHERE id = %s", (contract_id,))
    db.execute(
        "UPDATE attestation SET status = 'completed', finished_at = now(),"
        " signature = 'sig', signing_key_id = 'key' WHERE id = %s",
        (attestation_id,),
    )
    assert db.execute(
        "SELECT status FROM attestation WHERE id = %s", (attestation_id,)
    ).fetchone() == ("completed",)
