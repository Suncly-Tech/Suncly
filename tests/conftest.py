"""Shared fixtures.

The Postgres fixtures run only when ``DATABASE_URL`` is set; every test that
uses them is skipped otherwise. They never connect anywhere but that URL.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = REPO_ROOT / "db" / "migrations" / "0001_initial_schema.sql"


@pytest.fixture(scope="session")
def database_url() -> str:
    """The test database, or skip."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set; database tests need a Postgres instance")
    return url


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    """A database holding exactly the schema of ``db/migrations/0001_initial_schema.sql``.

    The public schema is dropped and the migration file applied as-is, so the
    tests exercise the committed file and nothing else.
    """
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute(MIGRATION.read_text(encoding="utf-8"))
    return database_url


@pytest.fixture
def db(migrated_database: str) -> Iterator[object]:
    """A connection inside a transaction that is rolled back after the test."""
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(migrated_database) as conn:
        try:
            yield conn
        finally:
            conn.rollback()
