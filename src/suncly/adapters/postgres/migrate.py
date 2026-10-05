"""Applying and checking the migrations in ``db/migrations``.

Migration 0001 creates the seven core tables in the public schema and keeps no
bookkeeping (an eighth core table would break "seven entities are the complete
list"). Migration 0002 creates the ``suncly_app`` schema of the application
layer, which carries the bookkeeping table ``suncly_app.schema_migration``
for itself and every later migration. The packaged copies of the files are
byte-identical to ``db/migrations``; a test guards that.
"""

from __future__ import annotations

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
APP_SCHEMA = "suncly_app"
APP_TABLES = (
    "schema_migration",
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
#: Ordered migrations. The name without ``.sql`` is the recorded version.
MIGRATIONS = ("0001_initial_schema", "0002_application_layer")
MIGRATION_NAME = MIGRATIONS[0] + ".sql"


def migration_sql(name: str = MIGRATION_NAME) -> str:
    return (
        resources.files("suncly.adapters.postgres")
        .joinpath("migrations", name)
        .read_text(encoding="utf-8")
    )


def existing_tables(
    conn: psycopg.Connection[tuple[object, ...]], schema: str = "public"
) -> set[str]:
    rows = conn.execute(
        "SELECT table_name FROM information_schema.tables"
        " WHERE table_schema = %s AND table_type = 'BASE TABLE'",
        (schema,),
    ).fetchall()
    return {str(row[0]) for row in rows}


def applied_versions(conn: psycopg.Connection[tuple[object, ...]]) -> set[str]:
    """Versions recorded by the bookkeeping table; 0001 is inferred from its tables."""
    versions: set[str] = set()
    core = existing_tables(conn)
    if all(name in core for name in TABLES):
        versions.add(MIGRATIONS[0])
    if "schema_migration" in existing_tables(conn, APP_SCHEMA):
        rows = conn.execute(f"SELECT version FROM {APP_SCHEMA}.schema_migration").fetchall()
        versions.update(str(row[0]) for row in rows)
    return versions


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
        extra = sorted(tables - set(TABLES))
        problems.extend(f"unexpected table {name}" for name in extra)
        app_tables = existing_tables(conn, APP_SCHEMA)
        problems.extend(
            f"table {APP_SCHEMA}.{name} is missing" for name in APP_TABLES if name not in app_tables
        )
        versions = applied_versions(conn)
        problems.extend(
            f"migration {name} is not recorded" for name in MIGRATIONS if name not in versions
        )
    return problems


def apply_migrations(database_url: str) -> list[str]:
    """Apply every migration not yet applied, in order. Returns what was applied."""
    applied: list[str] = []
    with psycopg.connect(database_url, autocommit=True) as conn:
        versions = applied_versions(conn)
        core = existing_tables(conn)
        present = [name for name in TABLES if name in core]
        if present and len(present) != len(TABLES):
            raise StoreError(
                "The database holds part of the core schema.",
                f"Present: {', '.join(present)}; missing: "
                f"{', '.join(n for n in TABLES if n not in core)}.",
                "Restore the database to empty, or apply the missing parts by hand.",
            )
        for name in MIGRATIONS:
            if name in versions:
                continue
            conn.execute(migration_sql(name + ".sql"))
            applied.append(name)
    return applied


def apply_migration(database_url: str) -> str:
    """Apply every pending migration. Returns a one-line description of what happened."""
    applied = apply_migrations(database_url)
    if not applied:
        return "already applied"
    return "applied " + ", ".join(applied)
