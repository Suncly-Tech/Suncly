"""Scheduled re-evaluation and the housekeeping tick (schema §4: the ``schedule`` trigger).

An unchanged Agent Card does not mean unchanged behaviour, so a registration
can be re-evaluated on a schedule. The tick enqueues a re-evaluation job for
every due schedule; the job starts a new attestation with the latest approved
contract of the registration's current card and the policy's regression rule
compares it with the previous completed one (``core/worker.py``). The tick
also recovers expired leases and relays the outbox.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from suncly.core.app import AppServices
from suncly.core.attestations_app import AttestationWorkflow, StartAttestationRequest
from suncly.core.authz import AuthorizedContext
from suncly.core.jobs import JobContext
from suncly.domain.errors import ConflictError, NotFoundError, QuotaError
from suncly.domain.jobs import Job, JobKind, JobStatus
from suncly.domain.models import AttestationTrigger, ContractStatus
from suncly.domain.tenancy import Membership, Organization, Principal, Role
from suncly.ports.app_store import ReevaluationSchedule

SCHEDULER_SUBJECT = "system:scheduler"


def scheduler_context(organization: Organization, now_iso: str) -> AuthorizedContext:
    """The scheduler acts as a reviewer-role principal of the organization."""
    principal = Principal(
        subject=SCHEDULER_SUBJECT,
        issuer="suncly",
        email=None,
        display_name="Suncly scheduler",
        verified_by="system",
    )
    from datetime import datetime

    membership = Membership(
        id=UUID(int=0),
        organization_id=organization.id,
        subject=SCHEDULER_SUBJECT,
        role=Role.REVIEWER,
        created_at=datetime.fromisoformat(now_iso),
    )
    return AuthorizedContext(principal, organization, membership)


class ReevaluationJobHandler:
    kind = JobKind.REEVALUATION

    def __init__(self, services: AppServices) -> None:
        self._s = services

    def handle(self, context: JobContext) -> None:
        s = self._s
        schedule_id = UUID(str(context.job.payload["schedule_id"]))
        organization = s.app_store.get_organization(context.job.organization_id)
        if organization is None:
            raise NotFoundError("The schedule's organization does not exist.")
        schedules = {sc.id: sc for sc in s.app_store.list_schedules(organization.id)}
        schedule = schedules.get(schedule_id)
        if schedule is None or not schedule.enabled:
            context.update_progress(phase="finished", note="schedule disabled or gone")
            return
        registration = s.app_store.get_registration(organization.id, schedule.registration_id)
        if registration is None or not registration.active:
            context.update_progress(phase="finished", note="registration archived")
            return
        contract = self._latest_approved_contract(registration.agent_id)
        if contract is None:
            context.update_progress(phase="finished", note="no approved contract to run")
            return
        ctx = scheduler_context(organization, s.clock.now().isoformat())
        try:
            view = AttestationWorkflow(s).start(
                ctx,
                StartAttestationRequest(
                    registration_id=registration.id,
                    contract_id=contract,
                    runs=schedule.runs_per_test_case,
                    budget_limit=Decimal(schedule.budget_limit),
                    trigger=AttestationTrigger.SCHEDULE,
                ),
            )
        except (QuotaError, ConflictError) as exc:
            context.update_progress(phase="finished", note=f"not started: {exc.what}")
            return
        context.update_progress(phase="finished", attestation_id=str(view.attestation.id))

    def exhausted(self, context: JobContext, job: Job) -> None:
        context.update_progress(phase="finished", note=f"failed {job.attempts} time(s)")

    def _latest_approved_contract(self, agent_id: UUID) -> UUID | None:
        s = self._s
        best = None
        for card_version in s.store.list_card_versions(agent_id):
            for contract in s.store.list_contracts(card_version.id):
                if contract.status is ContractStatus.APPROVED and (
                    best is None or contract.approved_at > best.approved_at  # type: ignore[operator]
                ):
                    best = contract
        return best.id if best else None


def enqueue_due_reevaluations(services: AppServices) -> list[Job]:
    """Create one re-evaluation job per due schedule and move the schedule forward."""
    s = services
    now = s.clock.now()
    created: list[Job] = []
    for schedule in s.app_store.due_schedules(now):
        job = Job(
            id=s.ids.new_id(),
            organization_id=schedule.organization_id,
            kind=JobKind.REEVALUATION,
            logical_id=s.ids.new_id(),
            payload={"schedule_id": str(schedule.id), "due_at": schedule.next_run_at.isoformat()},
            status=JobStatus.QUEUED,
            created_at=now,
            run_after=now,
            max_attempts=2,
        )
        s.app_store.enqueue_job(job)
        advanced: ReevaluationSchedule = schedule.model_copy(
            update={"next_run_at": now + timedelta(hours=schedule.interval_hours)}
        )
        s.app_store.update_schedule(advanced)
        created.append(job)
    return created


def relay_outbox(services: AppServices, limit: int = 100) -> list[str]:
    """Deliver pending outbox messages at least once. Usage lines go to the meter."""
    s = services
    outcomes: list[str] = []
    for message in s.app_store.claim_outbox(limit, s.clock.now()):
        try:
            if message.topic == "usage.settled":
                s.billing.report_pending_usage(limit=limit)
            s.app_store.mark_outbox(message.id, s.clock.now(), None)
            outcomes.append(f"{message.topic}: delivered")
        except Exception as exc:
            s.app_store.mark_outbox(message.id, s.clock.now(), f"{type(exc).__name__}: {exc}")
            outcomes.append(f"{message.topic}: failed ({type(exc).__name__})")
    return outcomes


def housekeeping_tick(services: AppServices) -> dict[str, object]:
    """What the dispatcher does on every tick. Idempotent; safe to run from several processes."""
    recovered = services.app_store.recover_expired_leases(services.clock.now())
    enqueued = enqueue_due_reevaluations(services)
    relayed = relay_outbox(services)
    reported = services.billing.report_pending_usage()
    return {
        "recovered_jobs": [str(job.id) for job in recovered],
        "reevaluations_enqueued": [str(job.id) for job in enqueued],
        "outbox": relayed,
        "meter_reports": reported,
    }
