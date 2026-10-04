"""Applying and checking ``db/migrations`` without a bookkeeping table.

A migrations table would be an eighth table, which the data model forbids, so
the state of the schema is read from ``information_schema`` instead. The
packaged copy of the migration is byte-identical to ``db/migrations``; a test
guards that.
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
MIGRATION_NAME = "0001_initial_schema.sql"


def migration_sql() -> str:
    return (
        resources.files("suncly.adapters.postgres")
        .joinpath("migrations", MIGRATION_NAME)
        .read_text(encoding="utf-8")
    )


def existing_tables(conn: psycopg.Connection[tuple[object, ...]]) -> set[str]:
    rows = conn.execute(
        "SELECT table_name FROM information_schema.tables"
        " WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def check_schema(database_url: str) -> list[str]:
    """Problems with the schema; empty when the migration is fully applied."""
    problems: list[str] = []
    with psycopg.connect(database_url) as conn:
        tables = existing_tables(conn)
        problems.extend(f"table {name} is missing" for name in TABLES if name not in tables)
        enum_rows = conn.execute("SELECT typname FROM pg_type WHERE typtype = 'e'").fetchall()
        enums = {str(row[0]) for row in enum_rows}
        problems.extend(f"enum {name} is missing" for name in ENUMS if name not in enums)
        trigger_rows = conn.execute(
            "SELECT DISTINCT tgname FROM pg_trigger WHERE NOT tgisinternal"
        ).fetchall()
        triggers = {str(row[0]) for row in trigger_rows}
        problems.extend(f"trigger {name} is missing" for name in TRIGGERS if name not in triggers)
        extra = sorted(tables - set(TABLES))
        problems.extend(f"unexpected table {name}" for name in extra)
    return problems


def apply_migration(database_url: str) -> str:
    """Apply ``0001_initial_schema.sql`` if no table exists yet. Returns what happened."""
    with psycopg.connect(database_url, autocommit=True) as conn:
        tables = existing_tables(conn)
        present = [name for name in TABLES if name in tables]
        if len(present) == len(TABLES):
            return "already applied"
        if present:
            raise StoreError(
                "The database holds part of the schema.",
                f"Present: {', '.join(present)}; missing: "
                f"{', '.join(n for n in TABLES if n not in tables)}.",
                "Restore the database to empty, or apply the missing parts by hand.",
            )
        conn.execute(migration_sql())
    return "applied"
