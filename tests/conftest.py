"""Shared fixtures.

The Postgres fixtures run only when ``DATABASE_URL`` is set; every test that
uses them is skipped otherwise. They never connect anywhere but that URL.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from suncly.adapters.file_store import FileEvidenceStore
from suncly.adapters.local_transcripts import LocalTranscriptStorage
from suncly.core.attestation import Services
from suncly.core.config import Config
from suncly.core.contract_builder import DeterministicDrafter
from suncly.ports.progress import NoProgress
from tests.fakes import (
    FakeClock,
    FakeExecutor,
    MemoryReportWriter,
    MemorySigningKeys,
    SeqIds,
    StaticFetcher,
    passing_executor,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ServicesFactory = Callable[..., Services]
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"


def apply_migrations(conn: Any) -> None:
    """Apply every file in ``db/migrations``, in order, exactly as committed."""
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        conn.execute(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def database_url() -> str:
    """The test database, or skip."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set; database tests need a Postgres instance")
    return url


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    """A database holding exactly the schema of the files in ``db/migrations``.

    The public schema is dropped and the migration files applied as-is, in
    order, so the tests exercise the committed files and nothing else.
    """
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        apply_migrations(conn)
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


# -- core services on fakes -------------------------------------------------------


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def ids() -> SeqIds:
    return SeqIds()


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        home=tmp_path / "home",
        reports_dir=tmp_path / "reports",
        runs=2,
        run_timeout_s=5.0,
        latency_limit_ms=2000,
        max_retries=1,
        concurrency=2,
        poll_interval_s=0.01,
    )


@pytest.fixture
def file_store(config: Config) -> FileEvidenceStore:
    return FileEvidenceStore(config.store_dir)


@pytest.fixture
def transcripts(config: Config) -> LocalTranscriptStorage:
    return LocalTranscriptStorage(config.transcripts_dir)


@pytest.fixture
def services_factory(
    config: Config,
    file_store: FileEvidenceStore,
    transcripts: LocalTranscriptStorage,
    clock: FakeClock,
    ids: SeqIds,
    tmp_path: Path,
) -> ServicesFactory:
    """Build ``Services`` on fakes; override the fetcher, executor or keys per test."""

    def build(
        fetcher: StaticFetcher,
        executor: FakeExecutor | None = None,
        keys: MemorySigningKeys | None = None,
    ) -> Services:
        return Services(
            config=config,
            store=file_store,
            transcripts=transcripts,
            fetcher=fetcher,
            drafter=DeterministicDrafter(),
            executor=executor or passing_executor(clock),
            keys=keys or MemorySigningKeys(),
            clock=clock,
            ids=ids,
            report_writer=MemoryReportWriter(tmp_path / "reports"),
            progress=NoProgress(),
        )

    return build
