"""Targeted checks from the pre-merge review: entitlement by fake webhook in deployed
environments, a tool's output never carrying its credential, exhausted jobs, and the
reservation limit under concurrent reservations on both stores."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from suncly.adapters.external import ToolProcess
from suncly.core.app_config import AppConfig, AuthConfig, BillingConfig, Environment
from suncly.core.jobs import JobContext, WorkerLoop
from suncly.domain.errors import ConfigError
from suncly.domain.jobs import AttemptOutcome, JobKind, JobStatus
from suncly.domain.ledger import Reservation, ReservationState
from suncly.domain.models import AttestationStatus, Contract
from suncly.domain.tenancy import DeploymentMode, Role
from tests.fakes import StaticFetcher, card_text
from tests.hosted import build_world, prepare_attestation
from tests.stores.test_app_store_contract import stores  # noqa: F401 - the two-store fixture

CARD_URL = "https://agent.example.test/.well-known/agent-card.json"
OIDC = AuthConfig(issuer="https://issuer.example.test/", audience="api", jwks_url="https://x/jwks")


def test_deployed_environments_refuse_the_fake_billing_provider() -> None:
    environments: list[Environment] = ["production", "staging"]
    for environment in environments:
        with pytest.raises(ConfigError, match="fake billing provider"):
            AppConfig(environment=environment, auth=OIDC, billing=BillingConfig(provider="fake"))
        AppConfig(environment=environment, auth=OIDC, billing=BillingConfig(provider="stripe"))
    AppConfig(environment="development", billing=BillingConfig(provider="fake"))


def test_a_tool_that_echoes_its_environment_leaks_no_credential(tmp_path: Path) -> None:
    script = tmp_path / "echo.py"
    script.write_text(
        "import os, sys; print(os.environ['SUNCLY_AGENT_AUTHORIZATION']); sys.stderr.write(os.environ['SUNCLY_AGENT_AUTHORIZATION'] + '\\n')"
    )
    tool = ToolProcess(
        dict(os.environ),
        DeploymentMode.LOCAL,
        {"SUNCLY_AGENT_AUTHORIZATION": "Bearer very-secret-token-value"},
    )
    result = tool.run([sys.executable, str(script)], tmp_path, 30.0)
    assert result.returncode == 0
    assert (
        b"very-secret-token-value" not in result.stdout
        and b"very-secret-token-value" not in result.stderr
    )
    assert b"[REDACTED]" in result.stdout and b"[REDACTED]" in result.stderr


def test_a_job_that_exhausts_its_attempts_fails_the_attestation_and_keeps_the_money_held(
    tmp_path: Path,
) -> None:
    world = build_world(tmp_path, fetcher=StaticFetcher({CARD_URL: card_text()}))
    s = world.services

    acme = world.organization("acme", {"rev": Role.REVIEWER})
    _, _, view = prepare_attestation(world, "rev", acme, CARD_URL, runs=1)
    # A crashing executor is a crashed run and an in-flight key is not repeated, so neither
    # exhausts the job; a store that fails on every attempt does.
    original = s.store.get_contract

    def dying(contract_id: UUID) -> Contract | None:
        raise OSError("evidence disk is full")

    s.store.get_contract = dying  # type: ignore[method-assign]
    worker = world.worker()
    for _ in range(s.app_config.worker.max_attempts):
        world.clock.advance(hours=1)
        assert worker.run_once() is True
    job = s.app_store.find_job(JobKind.ATTESTATION, view.attestation.id)
    assert (
        job is not None
        and job.status is JobStatus.FAILED
        and job.attempts == s.app_config.worker.max_attempts
    )
    assert [a.outcome for a in s.app_store.list_attempts(job.id)] == [
        AttemptOutcome.FAILED
    ] * job.attempts
    attestation = s.store.get_attestation(view.attestation.id)
    assert attestation is not None and attestation.status is AttestationStatus.FAILED
    assert attestation.finished_at is not None and s.store.list_decisions(attestation.id) == []
    assert job.progress["phase"] == "finished" and "disk is full" in job.progress["note"]
    reservation = s.app_store.get_reservation(UUID(str(job.payload["reservation_id"])))
    assert reservation is not None and reservation.state is ReservationState.HELD, (
        "a person reconciles it"
    )
    topics = [m.topic for m in s.app_store.claim_outbox(20, world.clock.now())]
    assert "attestation.failed" in topics
    s.store.get_contract = original  # type: ignore[method-assign]
    assert worker.run_once() is False, "a failed job is never claimed again"


def test_concurrent_reservations_never_exceed_the_hard_limit(stores: tuple[object, object]) -> None:  # noqa: F811
    from datetime import UTC, datetime

    from suncly.domain.tenancy import Organization

    app, _ = stores
    org = Organization(
        id=uuid4(), slug=f"race-{uuid4().hex[:8]}", name="Race", created_at=datetime.now(UTC)
    )
    app.add_organization(org)  # type: ignore[attr-defined]
    outcomes: list[bool] = []
    lock = threading.Lock()

    def reserve() -> None:
        reservation = Reservation(
            id=uuid4(),
            organization_id=org.id,
            attestation_id=None,
            amount_minor=300,
            currency="EUR",
            state=ReservationState.HELD,
            created_at=datetime.now(UTC),
            note="race",
        )
        ok = app.try_reserve(reservation, 1000, None)  # type: ignore[attr-defined]
        with lock:
            outcomes.append(ok)

    threads = [threading.Thread(target=reserve) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert len(outcomes) == 12 and outcomes.count(True) == 3, outcomes
    held = [r for r in app.list_reservations(org.id) if r.state is ReservationState.HELD]  # type: ignore[attr-defined]
    assert sum(r.amount_minor for r in held) == 900 <= 1000


def test_the_worker_loop_reports_exhaustion_through_the_handler(tmp_path: Path) -> None:
    """The loop calls ``exhausted`` exactly when the store marks the job failed."""
    world = build_world(tmp_path, fetcher=StaticFetcher({CARD_URL: card_text()}))
    s = world.services
    seen: list[str] = []

    class Boom:
        kind = JobKind.REEVALUATION

        def handle(self, context: JobContext) -> None:
            raise RuntimeError("no")

        def exhausted(self, context: JobContext, job: object) -> None:
            seen.append(str(getattr(job, "status", "")))

    from suncly.domain.jobs import Job

    acme = world.organization("acme", {"rev": Role.REVIEWER})
    job = Job(
        id=world.ids.new_id(),
        organization_id=acme.id,
        kind=JobKind.REEVALUATION,
        logical_id=world.ids.new_id(),
        payload={},
        status=JobStatus.QUEUED,
        created_at=world.clock.now(),
        run_after=world.clock.now(),
        max_attempts=2,
    )
    s.app_store.enqueue_job(job)
    loop = WorkerLoop(s.app_store, s.clock, s.app_config.worker, [Boom()], "w")
    assert loop.run_once() and seen == []
    world.clock.advance(hours=1)
    assert loop.run_once() and seen == ["failed"]
