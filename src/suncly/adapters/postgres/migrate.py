"""Applying and checking the migrations in ``db/migrations``.

A migrations table would be an eighth core table, which the data model forbids,
so the state of the schema is read from the catalog instead: 0001 is applied
when the seven tables exist, 0002 when row level security is enabled (and not
forced) on all of them and every guard function has a fixed ``search_path`` and
the body 0002 gives it, 0003 when the tables of the ``suncly_app`` schema exist.
The packaged copies of the migrations are byte-identical to ``db/migrations``;
a test guards that.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from importlib import resources

import psycopg

from suncly.domain.errors import StoreError

TABLES = ("agent", "card_version", "contract", "test_case", "attestation", "run", "decision")
ENUMS = (
    "risk_level",
    "contract_status",
    "test_case_kind",
    "attestation_trigger",
    "attestation_status",
    "run_verdict",
    "judge_layer",
    "decision_outcome",
)
TRIGGERS = (
    "run_append_only",
    "run_no_truncate",
    "decision_append_only",
    "decision_no_truncate",
    "contract_guard",
    "test_case_guard",
    "attestation_guard",
    "run_guard",
    "decision_guard",
)
#: The trigger functions; migration 0002 gives each a fixed search_path.
FUNCTIONS = (
    "suncly_forbid_change",
    "suncly_contract_guard",
    "suncly_test_case_guard",
    "suncly_attestation_guard",
    "suncly_run_guard",
    "suncly_decision_guard",
)
#: The application layer (SCHEMA.md §12) lives in its own schema, created by 0003.
APP_SCHEMA = "suncly_app"
APP_TABLES = (
    "organization",
    "membership",
    "agent_registration",
    "attestation_meta",
    "policy_record",
    "decision_note",
    "job",
    "job_attempt",
    "outbox",
    "reservation",
    "usage_event",
    "spending_limit",
    "subscription",
    "provider_event",
    "meter_report",
    "signing_key",
    "external_artifact",
    "reevaluation_schedule",
)
#: Every migration, in the order it is applied.
MIGRATIONS = (
    "0001_initial_schema.sql",
    "0002_rls_and_search_path.sql",
    "0003_application_layer.sql",
)

Connection = psycopg.Connection[tuple[object, ...]]

#: One guard function definition in migration 0002: its name and its body.
_FUNCTION_DEFINITION = re.compile(
    r"CREATE OR REPLACE FUNCTION public\.(\w+)\(\) RETURNS trigger\s+"
    r"LANGUAGE plpgsql\s+SET search_path = ''\s+AS \$\$(.*?)\$\$;",
    re.DOTALL,
)


def migration_sql(name: str) -> str:
    return (
        resources.files("suncly.adapters.postgres")
        .joinpath("migrations", name)
        .read_text(encoding="utf-8")
    )


def existing_tables(conn: Connection, schema: str | None = None) -> set[str]:
    """Base tables of ``schema``, or of the connection's current schema."""
    if schema is None:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_schema = %s AND table_type = 'BASE TABLE'",
            (schema,),
        ).fetchall()
    return {str(row[0]) for row in rows}


def rls_state(conn: Connection) -> dict[str, tuple[bool, bool]]:
    """``table -> (enabled, forced)`` for the seven tables that exist in the current schema."""
    rows = conn.execute(
        "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity"
        " FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace"
        " WHERE n.nspname = current_schema() AND c.relkind = 'r' AND c.relname = ANY(%s)",
        (list(TABLES),),
    ).fetchall()
    return {str(row[0]): (bool(row[1]), bool(row[2])) for row in rows}


def expected_function_bodies() -> dict[str, str]:
    """``function -> body`` as migration 0002 defines them: what ``pg_proc.prosrc`` holds."""
    text = migration_sql(MIGRATIONS[1]).replace("\r\n", "\n")
    return {match.group(1): match.group(2) for match in _FUNCTION_DEFINITION.finditer(text)}


def function_state(conn: Connection) -> dict[str, tuple[str | None, str]]:
    """``function -> (search_path setting, body)`` for the guard functions that exist.

    The setting is what ``SET search_path`` stored (``""`` for an empty path), or
    None when the function has no fixed search_path.
    """
    rows = conn.execute(
        "SELECT p.proname, p.proconfig, p.prosrc"
        " FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace"
        " WHERE n.nspname = current_schema() AND p.proname = ANY(%s)",
        (list(FUNCTIONS),),
    ).fetchall()
    state: dict[str, tuple[str | None, str]] = {}
    for row in rows:
        config = row[1]  # text[] -> list[str], or None when the function has no settings
        settings = [str(entry) for entry in config] if isinstance(config, list) else []
        setting = next(
            (entry.partition("=")[2] for entry in settings if entry.startswith("search_path=")),
            None,
        )
        state[str(row[0])] = (setting, str(row[2]).replace("\r\n", "\n"))
    return state


def function_search_paths(conn: Connection) -> dict[str, str | None]:
    """``function -> its search_path setting`` for the guard functions that exist."""
    return {name: setting for name, (setting, _body) in function_state(conn).items()}


def _initial_schema_applied(conn: Connection) -> bool:
    return set(TABLES) <= existing_tables(conn)


def _rls_and_search_path_applied(conn: Connection) -> bool:
    tables = rls_state(conn)
    functions = function_state(conn)
    bodies = expected_function_bodies()
    return all(tables.get(name) == (True, False) for name in TABLES) and all(
        name in functions and functions[name][0] is not None and functions[name][1] == bodies[name]
        for name in FUNCTIONS
    )


def _application_layer_applied(conn: Connection) -> bool:
    return set(APP_TABLES) <= existing_tables(conn, APP_SCHEMA)


#: How each migration is recognised in the catalog, in place of a bookkeeping table.
APPLIED: dict[str, Callable[[Connection], bool]] = {
    MIGRATIONS[0]: _initial_schema_applied,
    MIGRATIONS[1]: _rls_and_search_path_applied,
    MIGRATIONS[2]: _application_layer_applied,
}


def check_schema(database_url: str) -> list[str]:
    """Problems with the schema; empty when every migration is fully applied."""
    problems: list[str] = []
    with psycopg.connect(database_url) as conn:
        tables = existing_tables(conn)
        problems.extend(f"table {name} is missing" for name in TABLES if name not in tables)
        enum_rows = conn.execute(
            "SELECT typname FROM pg_type WHERE typtype = 'e'"
            " AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')"
        ).fetchall()
        enums = {str(row[0]) for row in enum_rows}
        problems.extend(f"enum {name} is missing" for name in ENUMS if name not in enums)
        trigger_rows = conn.execute(
            "SELECT DISTINCT tgname FROM pg_trigger WHERE NOT tgisinternal"
        ).fetchall()
        triggers = {str(row[0]) for row in trigger_rows}
        problems.extend(f"trigger {name} is missing" for name in TRIGGERS if name not in triggers)

        state = rls_state(conn)
        for name in TABLES:
            if name not in tables:
                continue
            enabled, forced = state.get(name, (False, False))
            if not enabled:
                problems.append(f"row level security is disabled on table {name}")
            elif forced:
                problems.append(
                    f"row level security is forced on table {name}, which locks out the table owner"
                )
        functions = function_state(conn)
        bodies = expected_function_bodies()
        for name in FUNCTIONS:
            if name not in functions:
                problems.append(f"function {name} is missing")
                continue
            setting, body = functions[name]
            if setting is None:
                problems.append(f"function {name} has no fixed search_path")
            if body != bodies[name]:
                problems.append(f"function {name} does not have the body of {MIGRATIONS[1]}")

        extra = sorted(tables - set(TABLES))
        problems.extend(f"unexpected table {name}" for name in extra)
        app_tables = existing_tables(conn, APP_SCHEMA)
        problems.extend(
            f"table {APP_SCHEMA}.{name} is missing" for name in APP_TABLES if name not in app_tables
        )
    return problems


def apply_migration(database_url: str) -> str:
    """Apply, in order, every migration the database does not hold yet. Returns what happened.

    Each migration is recognised from the catalog (``APPLIED``), and 0002 is
    itself idempotent, so this is safe on an empty database, on one holding
    only 0001, and on one where row level security was already enabled by hand.
    0002 is applied again when a table forces row level security or a guard's
    body differs from the migration's, so ``check_schema`` passes afterwards.
    """
    applied: list[str] = []
    with psycopg.connect(database_url, autocommit=True) as conn:
        tables = existing_tables(conn)
        present = [name for name in TABLES if name in tables]
        if present and len(present) < len(TABLES):
            raise StoreError(
                "The database holds part of the core schema.",
                f"Present: {', '.join(present)}; missing: "
                f"{', '.join(n for n in TABLES if n not in tables)}.",
                "Restore the database to empty, or apply the missing parts by hand.",
            )
        for name in MIGRATIONS:
            if APPLIED[name](conn):
                continue
            conn.execute(migration_sql(name))
            applied.append(name)
    if not applied:
        return "already applied"
    return "applied " + ", ".join(applied)
