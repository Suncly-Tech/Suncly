"""End to end on the Postgres store: the same attestation flow, with the evidence in Postgres.

Runs only when DATABASE_URL is set. Asserts that a completed attestation in
Postgres carries its decision and its signature, and that its report verifies.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from suncly.adapters.file_keys import FileSigningKeys
from suncly.adapters.httpx_card_fetcher import HttpxCardFetcher
from suncly.adapters.local_transcripts import LocalTranscriptStorage
from suncly.adapters.report.writer import FolderReportWriter, read_report_folder
from suncly.adapters.subprocess_executor import SubprocessRunExecutor
from suncly.adapters.system import SystemClock, UuidIds
from suncly.core.attestation import AttestationService, AttestRequest, Services
from suncly.core.config import Config
from suncly.core.contract_builder import DeterministicDrafter
from suncly.core.verify import verify_result
from suncly.domain.models import AttestationStatus, DecisionOutcome
from suncly.mock_agents import behaviours
from suncly.mock_agents.server import MockAgentServer
from suncly.ports.progress import NoProgress

pytestmark = [pytest.mark.e2e, pytest.mark.db]


def test_attestation_on_the_postgres_store_is_decided_signed_and_verifiable(
    migrated_database: str, tmp_path: Path
) -> None:
    psycopg = pytest.importorskip("psycopg")
    from suncly.adapters.postgres.store import PostgresEvidenceStore

    config = Config(
        home=tmp_path / "home",
        database_url=migrated_database,
        reports_dir=tmp_path / "reports",
        runs=1,
        run_timeout_s=8.0,
        max_retries=1,
        concurrency=3,
        poll_interval_s=0.05,
    )
    transcripts = LocalTranscriptStorage(config.transcripts_dir)
    store = PostgresEvidenceStore(migrated_database)
    services = Services(
        config=config,
        store=store,
        transcripts=transcripts,
        fetcher=HttpxCardFetcher(config.card_timeout_s, config.card_max_bytes),
        drafter=DeterministicDrafter(),
        executor=SubprocessRunExecutor(),
        keys=FileSigningKeys(config.keys_dir),
        clock=SystemClock(),
        ids=UuidIds(),
        report_writer=FolderReportWriter(config.reports_dir, transcripts),
        progress=NoProgress(),
    )
    try:
        with MockAgentServer(behaviours.Honest()) as server:
            outcome = AttestationService(services).attest(
                AttestRequest(
                    card_url=server.card_url, sandbox_declared=True, runs=1, approve_as="e2e-pg"
                )
            )
    finally:
        store.close()

    assert outcome.kind == "completed" and outcome.attestation is not None
    assert outcome.decision is not None and outcome.decision.outcome is DecisionOutcome.FLAG
    assert outcome.report_dir is not None
    result, files = read_report_folder(outcome.report_dir)
    assert verify_result(result, files).ok

    with psycopg.connect(migrated_database) as conn:
        row = conn.execute(
            "SELECT status, signature, signing_key_id FROM attestation WHERE id = %s",
            (outcome.attestation.id,),
        ).fetchone()
        assert row is not None
        assert row[0] == AttestationStatus.COMPLETED.value
        assert row[1] is not None and row[1].startswith("ed25519:") and row[2] is not None
        decisions = conn.execute(
            "SELECT outcome, decided_by FROM decision WHERE attestation_id = %s",
            (outcome.attestation.id,),
        ).fetchall()
        assert decisions == [("flag", "policy")]
        runs = conn.execute(
            "SELECT count(*) FROM run WHERE attestation_id = %s", (outcome.attestation.id,)
        ).fetchone()
        assert runs is not None and runs[0] == 3
