"""Builds the ``Services`` the core runs on, from one ``Config``."""

from __future__ import annotations

from collections.abc import Mapping

from suncly.adapters.file_keys import FileSigningKeys
from suncly.adapters.file_store import FileEvidenceStore
from suncly.adapters.httpx_card_fetcher import HttpxCardFetcher
from suncly.adapters.judge_subprocess import SubprocessModelJudge
from suncly.adapters.local_transcripts import LocalTranscriptStorage
from suncly.adapters.report.writer import FolderReportWriter
from suncly.adapters.subprocess_executor import SubprocessRunExecutor
from suncly.adapters.system import SystemClock, UuidIds
from suncly.core.attestation import Services
from suncly.core.config import Config
from suncly.core.contract_builder import DeterministicDrafter
from suncly.ports.model_judge import ModelJudge
from suncly.ports.progress import NoProgress, ProgressListener
from suncly.ports.store import EvidenceStore


def build_store(config: Config) -> EvidenceStore:
    if config.uses_postgres:
        from suncly.adapters.postgres.store import PostgresEvidenceStore

        assert config.database_url is not None
        return PostgresEvidenceStore(config.database_url)
    return FileEvidenceStore(config.store_dir)


def build_model_judge(config: Config, env: Mapping[str, str]) -> ModelJudge | None:
    """The judge subprocess adapter when an endpoint is configured; the key stays in ``env``."""
    if not config.judge_endpoint:
        return None
    return SubprocessModelJudge(config.judge_endpoint, env)


def build_services(
    config: Config, progress: ProgressListener | None = None, env: Mapping[str, str] | None = None
) -> Services:
    """``env`` is the process environment; only the judge subprocess adapter looks into it."""
    transcripts = LocalTranscriptStorage(config.transcripts_dir)
    return Services(
        config=config,
        store=build_store(config),
        transcripts=transcripts,
        fetcher=HttpxCardFetcher(config.card_timeout_s, config.card_max_bytes),
        drafter=DeterministicDrafter(),
        executor=SubprocessRunExecutor(),
        keys=FileSigningKeys(config.keys_dir),
        clock=SystemClock(),
        ids=UuidIds(),
        report_writer=FolderReportWriter(config.reports_dir, transcripts),
        progress=progress or NoProgress(),
        model_judge=build_model_judge(config, env or {}),
    )
