"""The durable attestation job: run, sign, bill, settle; crash, resume, cancel, lose a lease."""

from __future__ import annotations

import json
import threading
import time
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from suncly.core import integrity
from suncly.core.attestations_app import AttestationWorkflow
from suncly.core.reevaluation import enqueue_due_reevaluations, housekeeping_tick
from suncly.domain.errors import StoreError
from suncly.domain.evidence import NotExecutedReason
from suncly.domain.jobs import AttemptOutcome, JobKind, JobStatus
from suncly.domain.ledger import ReservationState, UsageOperation, UsageOutcome
from suncly.domain.models import AttestationStatus, AttestationTrigger, DecisionOutcome, RiskLevel
from suncly.domain.policy import PolicyConfiguration, PolicyRecord, RegressionRule, RiskThresholds
from suncly.domain.tenancy import Role
from suncly.ports.app_store import ReevaluationSchedule
from suncly.ports.run_executor import RunJob, RunResult
from tests.fakes import FakeExecutor, StaticFetcher, card_text, make_transcript, task_response
from tests.hosted import ISSUER, HostedWorld, build_world, prepare_attestation

CARD_URL = "https://agent.example.test/.well-known/agent-card.json"


def world_with(tmp_path: Path, executor: FakeExecutor | None = None, **kwargs: Any) -> HostedWorld:
    clock = kwargs.pop("clock", None)
    return build_world(
        tmp_path,
        fetcher=StaticFetcher({CARD_URL: card_text()}, clock),
        executor_factory=(lambda registration: executor) if executor else None,
        clock=clock,
        **kwargs,
    )


def passing(world: HostedWorld, delay_s: float = 0.0) -> FakeExecutor:
    def behaviour(job: RunJob, n: int) -> RunResult:
        if delay_s:
            time.sleep(delay_s)
        return RunResult(transcript=make_transcript(job, clock=world.clock))

    return FakeExecutor(behaviour)


def low_risk_policy(org_id: UUID, world: HostedWorld, **extra: Any) -> PolicyRecord:
    configuration = PolicyConfiguration.model_validate(
        {
            "policy_version": "acme-1",
            "thresholds": {
                RiskLevel.LOW: RiskThresholds(min_pass_ratio=0.5),
                RiskLevel.HIGH: RiskThresholds(min_pass_ratio=1.0, require_human_signoff=True),
            },
            **extra,
        }
    )
    record = PolicyRecord(
        id=world.ids.new_id(),
        organization_id=org_id,
        policy_version=configuration.policy_version,
        content_hash=configuration.content_hash(),
        configuration=configuration,
        created_at=world.clock.now(),
        created_by="admin@example.test",
    )
    world.services.app_store.add_policy(record)
    return record


def agent_lines(world: HostedWorld, org_id: UUID, attestation_id: UUID) -> list[Any]:
    return [
        e
        for e in world.services.app_store.list_usage_events(org_id)
        if e.attestation_id == attestation_id and e.operation is UsageOperation.AGENT_CALL
    ]


def test_a_queued_attestation_runs_to_a_signed_flagged_result(tmp_path: Path) -> None:
    world = world_with(tmp_path)
    executor = passing(world)
    world.services.executor_factory = lambda registration: executor
    acme = world.organization("acme", {"rev": Role.REVIEWER})
    _, detail, view = prepare_attestation(world, "rev", acme, CARD_URL, runs=2)
    s = world.services
    planned = 2 * len(detail.test_cases)
    assert view.attestation.status is AttestationStatus.QUEUED and view.job is not None
    reservation_id = UUID(str(view.job.payload["reservation_id"]))
    held = s.app_store.get_reservation(reservation_id)
    assert held is not None and held.state is ReservationState.HELD

    log: list[str] = []
    worker = world.worker(log=log)
    assert worker.run_once() is True
    assert worker.run_once() is False, "nothing else is queued"

    attestation = s.store.get_attestation(view.attestation.id)
    assert attestation is not None and attestation.status is AttestationStatus.COMPLETED
    assert attestation.signing_key_id and attestation.signature
    decisions = s.store.list_decisions(attestation.id)
    assert [d.outcome for d in decisions] == [DecisionOutcome.FLAG]
    assert decisions[0].policy_version == "unconfigured" and decisions[0].decided_by == "policy"

    job = s.app_store.find_job(JobKind.ATTESTATION, attestation.id)
    assert job is not None and job.status is JobStatus.SUCCEEDED and job.attempts == 1
    assert job.progress["phase"] == "finished" and job.progress["recorded_runs"] == planned
    assert [a.outcome for a in s.app_store.list_attempts(job.id)] == [AttemptOutcome.SUCCEEDED]

    payload = json.loads(s.transcripts.get(f"{attestation.id}/signature-payload.json"))
    assert payload["payload_version"] == integrity.PAYLOAD_VERSION_2
    assert payload["issuer"] == ISSUER and payload["attestation_id"] == str(attestation.id)
    assert payload["contract"]["content_hash"] == detail.content_hash
    assert payload["environment"]["sandbox_declared"] is True
    meta = s.app_store.get_attestation_meta(attestation.id)
    assert meta is not None and meta.payload_version == integrity.PAYLOAD_VERSION_2
    assert meta.issued_at is not None and meta.expires_at == meta.issued_at + timedelta(days=90)
    assert s.app_store.get_signing_key(attestation.signing_key_id) is not None

    lines = agent_lines(world, acme.id, attestation.id)
    assert len(lines) == planned and {e.outcome for e in lines} == {UsageOutcome.SETTLED}
    assert len({e.logical_run_id for e in lines}) == planned, "one line per run"
    reservation = s.app_store.get_reservation(reservation_id)
    assert reservation is not None and reservation.state is ReservationState.SETTLED
    assert reservation.settled_minor == sum(e.billable_minor for e in lines)
    topics = [m.topic for m in s.app_store.claim_outbox(10, world.clock.now())]
    assert "attestation.queued" in topics and "attestation.finished" in topics

    bundle = AttestationWorkflow(s).evidence(
        world.context("rev", acme.id, "evidence:read"), attestation.id
    )
    assert len(bundle.runs) == planned and bundle.policy_evaluation is not None
    assert bundle.policy_evaluation["policy_version"] == "unconfigured"
    assert any("claimed job" in line for line in log) and any("succeeded" in line for line in log)


def test_a_policy_approves_low_risk_and_a_high_risk_agent_always_waits_for_a_human(
    tmp_path: Path,
) -> None:
    world = world_with(tmp_path)
    executor = passing(world)
    world.services.executor_factory = lambda registration: executor
    acme = world.organization("acme", {"rev": Role.REVIEWER})
    policy = low_risk_policy(acme.id, world)
    _, _, low = prepare_attestation(world, "rev", acme, CARD_URL)
    _, _, high = prepare_attestation(world, "rev", acme, CARD_URL, risk_level=RiskLevel.HIGH)
    worker = world.worker()
    assert worker.run_once() and worker.run_once()
    s = world.services
    low_decision = s.store.list_decisions(low.attestation.id)[-1]
    high_decision = s.store.list_decisions(high.attestation.id)[-1]
    assert low_decision.outcome is DecisionOutcome.APPROVE
    assert low_decision.policy_version == "acme-1"
    assert high_decision.outcome is DecisionOutcome.FLAG
    payload = json.loads(s.transcripts.get(f"{low.attestation.id}/signature-payload.json"))
    assert payload["policy"] == {"version": "acme-1", "content_hash": policy.content_hash}
    meta = s.app_store.get_attestation_meta(low.attestation.id)
    assert meta is not None and meta.policy_content_hash == policy.content_hash
    high_meta = s.app_store.get_attestation_meta(high.attestation.id)
    assert high_meta is not None
    high_job = s.app_store.find_job(JobKind.ATTESTATION, high.attestation.id)
    assert high_job is not None
    evaluation = high_job.progress["policy_evaluation"]
    assert evaluation["requires_human"] is True
    assert any("human sign-off" in r for r in evaluation["reasons"])


@pytest.mark.parametrize("idempotent", [False, True])
def test_a_crashed_attempt_is_retried_and_resumed_without_duplicate_evidence_or_billing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, idempotent: bool
) -> None:
    world = world_with(tmp_path)
    executor = passing(world)
    world.services.executor_factory = lambda registration: executor
    world.services.config = world.services.config.with_overrides(concurrency=1)
    acme = world.organization("acme", {"rev": Role.REVIEWER})
    _, detail, view = prepare_attestation(
        world, "rev", acme, CARD_URL, sandbox_idempotent=idempotent, runs=2
    )
    s = world.services
    planned = 2 * len(detail.test_cases)
    original = s.store.add_run
    calls = {"n": 0}

    def dying_add_run(run: Any) -> None:
        calls["n"] += 1
        if calls["n"] == 2:
            raise StoreError("the worker lost its database connection while recording a run")
        original(run)

    monkeypatch.setattr(s.store, "add_run", dying_add_run)
    worker = world.worker()
    assert worker.run_once() is True
    job = s.app_store.find_job(JobKind.ATTESTATION, view.attestation.id)
    assert job is not None and job.status is JobStatus.QUEUED and job.attempts == 1
    assert job.last_error and "lost its database connection" in job.last_error
    assert job.progress["in_flight"], "the key whose outcome is unknown was persisted"
    in_flight = list(job.progress["in_flight"])
    attestation = s.store.get_attestation(view.attestation.id)
    assert attestation is not None and attestation.status is AttestationStatus.RUNNING
    assert agent_lines(world, acme.id, attestation.id) == [], "the dead attempt billed nothing"

    assert worker.run_once() is True, "the backoff of the first retry has elapsed"
    job = s.app_store.find_job(JobKind.ATTESTATION, view.attestation.id)
    assert job is not None and job.status is JobStatus.SUCCEEDED and job.attempts == 2
    attestation = s.store.get_attestation(view.attestation.id)
    assert attestation is not None and attestation.status is AttestationStatus.COMPLETED
    runs = s.store.list_runs(attestation.id)
    keys = {(str(r.test_case_id), r.attempt) for r in runs}
    assert len(keys) == len(runs), "no duplicate evidence under one key"
    executions = executor.attempts
    not_executed = job.progress["not_executed"]
    lines = agent_lines(world, acme.id, attestation.id)
    if idempotent:
        assert len(runs) == planned and not_executed == []
        assert max(executions.values()) == 2, (
            "the in-flight run was repeated: the sandbox allows it"
        )
        assert len(lines) == planned
        reservation = s.app_store.get_reservation(UUID(str(job.payload["reservation_id"])))
        assert reservation is not None and reservation.state is ReservationState.SETTLED
    else:
        assert len(runs) == planned - 1
        assert [n["reason"] for n in not_executed] == [NotExecutedReason.UNKNOWN_OUTCOME.value]
        assert f"{not_executed[0]['test_case_id']}:{not_executed[0]['attempt']}" == in_flight[0]
        assert max(executions.values()) == 1, "nothing was repeated"
        settled = [e for e in lines if e.outcome is UsageOutcome.SETTLED]
        unknown = [e for e in lines if e.outcome is UsageOutcome.UNKNOWN]
        assert len(settled) == planned - 1 and len(unknown) == 1
        assert unknown[0].billable_minor == 0 and unknown[0].provider_cost_minor is None
        reservation = s.app_store.get_reservation(UUID(str(job.payload["reservation_id"])))
        assert reservation is not None and reservation.state is ReservationState.HELD, (
            "an unknown outcome leaves the reservation for a person to reconcile"
        )
    first_run_lines = [e for e in lines if e.logical_run_id == runs[0].id]
    assert len(first_run_lines) == 1, "the run recorded by the dead attempt is billed exactly once"


def test_cancellation_mid_run_stops_the_remaining_runs_and_settles_what_ran(tmp_path: Path) -> None:
    world = world_with(tmp_path)
    s = world.services
    cancelled_once = {"done": False}

    def behaviour(job: RunJob, n: int) -> RunResult:
        if not cancelled_once["done"]:
            cancelled_once["done"] = True
            running = s.app_store.find_job(JobKind.ATTESTATION, job.attestation_id)
            assert running is not None
            s.app_store.request_cancel(running.id, world.clock.now())
        time.sleep(0.2)  # long enough for a heartbeat to carry the request back
        return RunResult(transcript=make_transcript(job, clock=world.clock))

    executor = FakeExecutor(behaviour)
    s.executor_factory = lambda registration: executor
    s.config = s.config.with_overrides(concurrency=1)
    acme = world.organization("acme", {"rev": Role.REVIEWER})
    _, detail, view = prepare_attestation(world, "rev", acme, CARD_URL, runs=3)
    assert world.worker().run_once() is True
    attestation = s.store.get_attestation(view.attestation.id)
    assert attestation is not None and attestation.status is AttestationStatus.CANCELLED
    assert s.store.list_decisions(attestation.id) == [], (
        "a cancelled attestation carries no decision"
    )
    job = s.app_store.find_job(JobKind.ATTESTATION, attestation.id)
    assert job is not None and job.status is JobStatus.CANCELLED
    assert [a.outcome for a in s.app_store.list_attempts(job.id)] == [AttemptOutcome.CANCELLED]
    reasons = {n["reason"] for n in job.progress["not_executed"]}
    assert reasons == {NotExecutedReason.CANCELLED.value}
    recorded = len(s.store.list_runs(attestation.id))
    assert 0 < recorded < 3 * len(detail.test_cases)
    assert len(agent_lines(world, acme.id, attestation.id)) == recorded
    reservation = s.app_store.get_reservation(UUID(str(job.payload["reservation_id"])))
    assert reservation is not None and reservation.state is ReservationState.SETTLED
    payload = json.loads(s.transcripts.get(f"{attestation.id}/signature-payload.json"))
    assert payload["decision"] is None and payload["attestation_id"] == str(attestation.id)


def test_cancelling_a_queued_attestation_releases_its_reservation_at_once(tmp_path: Path) -> None:
    world = world_with(tmp_path)
    acme = world.organization("acme", {"rev": Role.REVIEWER})
    _, _, view = prepare_attestation(world, "rev", acme, CARD_URL)
    s = world.services
    ctx = world.context("rev", acme.id, "attestations:cancel")
    cancelled = AttestationWorkflow(s).cancel(ctx, view.attestation.id)
    assert cancelled.attestation.status is AttestationStatus.CANCELLED
    assert cancelled.job is not None and cancelled.job.status is JobStatus.CANCELLED
    assert view.job is not None
    reservation = s.app_store.get_reservation(UUID(str(view.job.payload["reservation_id"])))
    assert reservation is not None and reservation.state is ReservationState.RELEASED
    assert world.worker().run_once() is False
    with pytest.raises(Exception, match="already final"):
        AttestationWorkflow(s).cancel(ctx, view.attestation.id)


def test_a_lost_lease_stops_the_worker_and_another_worker_resumes_the_job(tmp_path: Path) -> None:
    world = world_with(tmp_path)
    s = world.services
    stolen = {"done": False}

    def behaviour(job: RunJob, n: int) -> RunResult:
        if not stolen["done"]:
            stolen["done"] = True
            # The reaper decides this worker is dead: the lease expires and the job is requeued.
            far_future = world.clock.now() + timedelta(hours=1)
            assert s.app_store.recover_expired_leases(far_future)
        time.sleep(0.2)
        return RunResult(transcript=make_transcript(job, clock=world.clock))

    executor = FakeExecutor(behaviour)
    s.executor_factory = lambda registration: executor
    s.config = s.config.with_overrides(concurrency=1)
    acme = world.organization("acme", {"rev": Role.REVIEWER})
    _, detail, view = prepare_attestation(world, "rev", acme, CARD_URL, runs=2)
    log: list[str] = []
    assert world.worker("worker-a", log).run_once() is True
    assert any("lease" in line and "lost" in line for line in log), log
    job = s.app_store.find_job(JobKind.ATTESTATION, view.attestation.id)
    assert job is not None and job.status is JobStatus.QUEUED
    attempts = s.app_store.list_attempts(job.id)
    assert [a.outcome for a in attempts] == [AttemptOutcome.LOST]
    running = s.store.get_attestation(view.attestation.id)
    assert running is not None and running.status is AttestationStatus.RUNNING

    assert job.run_after > world.clock.now(), "the recovered job waits out its backoff"
    assert world.worker("worker-b").run_once() is False
    world.clock.advance(hours=2)
    assert world.worker("worker-b").run_once() is True
    job = s.app_store.find_job(JobKind.ATTESTATION, view.attestation.id)
    assert job is not None and job.status is JobStatus.SUCCEEDED
    attempts = s.app_store.list_attempts(job.id)
    assert [a.outcome for a in attempts] == [AttemptOutcome.LOST, AttemptOutcome.SUCCEEDED]
    assert attempts[1].worker_id == "worker-b"
    attestation = s.store.get_attestation(view.attestation.id)
    assert attestation is not None and attestation.status is AttestationStatus.COMPLETED
    runs = s.store.list_runs(attestation.id)
    planned = 2 * len(detail.test_cases)
    assert len({(str(r.test_case_id), r.attempt) for r in runs}) == len(runs) <= planned


def test_two_workers_respect_the_tenant_concurrency_limit_and_never_share_a_job(
    tmp_path: Path,
) -> None:
    world = world_with(tmp_path)
    s = world.services
    lock = threading.Lock()
    state = {"running": 0, "peak": 0}

    def behaviour(job: RunJob, n: int) -> RunResult:
        with lock:
            state["running"] += 1
            state["peak"] = max(state["peak"], state["running"])
        time.sleep(0.05)
        with lock:
            state["running"] -= 1
        return RunResult(transcript=make_transcript(job, clock=world.clock))

    s.executor_factory = lambda registration: FakeExecutor(behaviour)
    acme = world.organization("acme", {"rev": Role.REVIEWER}, max_concurrent_jobs=1)
    views = [prepare_attestation(world, "rev", acme, CARD_URL, runs=1)[2] for _ in range(3)]
    s.config = s.config.with_overrides(concurrency=1)
    ran = {"a": 0, "b": 0}

    def drive(name: str) -> None:
        worker = world.worker(f"worker-{name}")
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if worker.run_once():
                ran[name] += 1
            elif all(
                (s.app_store.find_job(JobKind.ATTESTATION, v.attestation.id) or v.job).is_final
                for v in views
            ):
                return
            else:
                time.sleep(0.01)

    threads = [threading.Thread(target=drive, args=(name,)) for name in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert ran["a"] + ran["b"] == 3, ran
    assert state["peak"] == 1, "the tenant limit of one job at a time held across both workers"
    for view in views:
        job = s.app_store.find_job(JobKind.ATTESTATION, view.attestation.id)
        assert job is not None and job.status is JobStatus.SUCCEEDED and job.attempts == 1
        assert len(s.app_store.list_attempts(job.id)) == 1


def test_scheduled_reevaluation_runs_through_the_queue_and_compares_with_the_baseline(
    tmp_path: Path,
) -> None:
    world = world_with(tmp_path)
    s = world.services
    answers = {"fail": False}

    def behaviour(job: RunJob, n: int) -> RunResult:
        if answers["fail"]:
            failed = task_response(text="I cannot do that", state="TASK_STATE_FAILED")
            return RunResult(
                transcript=make_transcript(job, clock=world.clock, final_response=failed)
            )
        return RunResult(transcript=make_transcript(job, clock=world.clock))

    s.executor_factory = lambda registration: FakeExecutor(behaviour)
    acme = world.organization("acme", {"rev": Role.REVIEWER, "admin": Role.ADMINISTRATOR})
    low_risk_policy(
        acme.id,
        world,
        regression=RegressionRule(baseline="previous_completed", max_pass_ratio_drop=0.1),
    )
    registration, _, first = prepare_attestation(world, "rev", acme, CARD_URL, runs=2)
    worker = world.worker()
    assert worker.run_once()
    assert s.store.list_decisions(first.attestation.id)[-1].outcome is DecisionOutcome.APPROVE

    schedule = ReevaluationSchedule(
        id=world.ids.new_id(),
        organization_id=acme.id,
        registration_id=registration.id,
        interval_hours=24,
        runs_per_test_case=2,
        budget_limit="50",
        next_run_at=world.clock.now() - timedelta(minutes=1),
        created_by="admin@example.test",
        created_at=world.clock.now(),
    )
    s.app_store.add_schedule(schedule)
    assert enqueue_due_reevaluations(s) and not enqueue_due_reevaluations(s), "moved forward once"
    answers["fail"] = True
    assert worker.run_once(), "the re-evaluation job starts a new attestation"
    assert worker.run_once(), "which the worker then runs"
    ctx = world.context("rev", acme.id, "attestations:read")
    views = AttestationWorkflow(s).list(ctx, registration.id)
    assert len(views) == 2
    latest = views[0]
    assert latest.attestation.trigger is AttestationTrigger.SCHEDULE
    assert latest.meta.created_by == "system:scheduler"
    decision = s.store.list_decisions(latest.attestation.id)[-1]
    assert decision.outcome is not DecisionOutcome.APPROVE
    assert latest.job is not None
    evaluation = latest.job.progress["policy_evaluation"]
    assert any("dropping" in r or "below min_pass_ratio" in r for r in evaluation["reasons"]), (
        evaluation
    )
    tick = housekeeping_tick(s)
    assert tick["reevaluations_enqueued"] == [] and isinstance(tick["outbox"], list)
