"""The in-memory application store: one lock, the same semantics as Postgres.

Used by the unit tests, the API tests and local development without a
database. Every atomic operation of the port is atomic here under one
re-entrant lock, so the behaviour the contract suite checks is the same.
"""

from __future__ import annotations

import threading
from datetime import datetime
from uuid import UUID

from suncly.domain.billing import MeterReport, ProviderEvent, Subscription
from suncly.domain.errors import ConflictError, JobError
from suncly.domain.jobs import (
    AttemptOutcome,
    ExecutionAttempt,
    Job,
    JobKind,
    JobStatus,
    OutboxMessage,
)
from suncly.domain.ledger import (
    Reservation,
    ReservationState,
    SettlementState,
    SpendingLimit,
    UsageEvent,
    UsageOutcome,
)
from suncly.domain.models import JsonObject
from suncly.domain.policy import PolicyRecord
from suncly.domain.tenancy import AgentRegistration, Membership, Organization
from suncly.ports.app_store import (
    AttestationMeta,
    DecisionNote,
    ExternalArtifact,
    LedgerTotals,
    ReevaluationSchedule,
    SigningKeyRecord,
)
from suncly.ports.clock import IdGenerator


class MemoryApplicationStore:
    def __init__(self, ids: IdGenerator | None = None) -> None:
        self._lock = threading.RLock()
        self._ids = ids
        self.organizations: dict[UUID, Organization] = {}
        self.memberships: dict[UUID, Membership] = {}
        self.registrations: dict[UUID, AgentRegistration] = {}
        self.meta: dict[UUID, AttestationMeta] = {}
        self.policies: dict[UUID, PolicyRecord] = {}
        self.notes: dict[UUID, DecisionNote] = {}
        self.jobs: dict[UUID, Job] = {}
        self.attempts: dict[UUID, ExecutionAttempt] = {}
        self.outbox: dict[UUID, OutboxMessage] = {}
        self.usage: dict[UUID, UsageEvent] = {}
        self.reservations: dict[UUID, Reservation] = {}
        self.limits: list[SpendingLimit] = []
        self.subscriptions: dict[UUID, Subscription] = {}
        self.provider_events: dict[tuple[str, str], ProviderEvent] = {}
        self.meter_reports: dict[UUID, MeterReport] = {}
        self.keys: dict[str, SigningKeyRecord] = {}
        self.artifacts: dict[UUID, ExternalArtifact] = {}
        self.schedules: dict[UUID, ReevaluationSchedule] = {}

    # -- organizations ---------------------------------------------------------

    def add_organization(self, organization: Organization) -> None:
        with self._lock:
            if organization.id in self.organizations or any(
                o.slug == organization.slug for o in self.organizations.values()
            ):
                raise ConflictError("An organization with this id or slug already exists.")
            self.organizations[organization.id] = organization

    def get_organization(self, organization_id: UUID) -> Organization | None:
        return self.organizations.get(organization_id)

    def get_organization_by_slug(self, slug: str) -> Organization | None:
        return next((o for o in self.organizations.values() if o.slug == slug), None)

    def add_membership(self, membership: Membership) -> None:
        with self._lock:
            if membership.organization_id not in self.organizations:
                raise ConflictError("The organization does not exist.")
            if self.get_membership(membership.organization_id, membership.subject) is not None:
                raise ConflictError("The subject is already a member of this organization.")
            self.memberships[membership.id] = membership

    def get_membership(self, organization_id: UUID, subject: str) -> Membership | None:
        return next(
            (
                m
                for m in self.memberships.values()
                if m.organization_id == organization_id and m.subject == subject
            ),
            None,
        )

    def list_memberships(self, organization_id: UUID) -> list[Membership]:
        return sorted(
            (m for m in self.memberships.values() if m.organization_id == organization_id),
            key=lambda m: m.created_at,
        )

    def list_organizations_for_subject(self, subject: str) -> list[Organization]:
        ids = {m.organization_id for m in self.memberships.values() if m.subject == subject}
        return sorted((self.organizations[i] for i in ids), key=lambda o: o.created_at)

    # -- registrations ---------------------------------------------------------

    def add_registration(self, registration: AgentRegistration) -> None:
        with self._lock:
            if any(r.agent_id == registration.agent_id for r in self.registrations.values()):
                raise ConflictError("This agent is already registered.")
            self.registrations[registration.id] = registration

    def get_registration(
        self, organization_id: UUID, registration_id: UUID
    ) -> AgentRegistration | None:
        registration = self.registrations.get(registration_id)
        if registration is None or registration.organization_id != organization_id:
            return None
        return registration

    def get_registration_by_agent(self, agent_id: UUID) -> AgentRegistration | None:
        return next((r for r in self.registrations.values() if r.agent_id == agent_id), None)

    def list_registrations(self, organization_id: UUID) -> list[AgentRegistration]:
        return sorted(
            (r for r in self.registrations.values() if r.organization_id == organization_id),
            key=lambda r: r.created_at,
        )

    def archive_registration(
        self, organization_id: UUID, registration_id: UUID, at: datetime
    ) -> AgentRegistration | None:
        with self._lock:
            registration = self.get_registration(organization_id, registration_id)
            if registration is None:
                return None
            updated = registration.model_copy(update={"archived_at": at})
            self.registrations[registration_id] = updated
            return updated

    # -- attestation meta ------------------------------------------------------

    def add_attestation_meta(self, meta: AttestationMeta) -> None:
        with self._lock:
            if meta.attestation_id in self.meta:
                raise ConflictError("Attestation meta already exists.")
            self.meta[meta.attestation_id] = meta

    def get_attestation_meta(self, attestation_id: UUID) -> AttestationMeta | None:
        return self.meta.get(attestation_id)

    def update_attestation_meta(self, meta: AttestationMeta) -> None:
        with self._lock:
            if meta.attestation_id not in self.meta:
                raise ConflictError("Attestation meta does not exist.")
            self.meta[meta.attestation_id] = meta

    def list_attestation_meta(
        self, organization_id: UUID, registration_id: UUID | None = None
    ) -> list[AttestationMeta]:
        return [
            m
            for m in self.meta.values()
            if m.organization_id == organization_id
            and (registration_id is None or m.registration_id == registration_id)
        ]

    # -- policies and notes ----------------------------------------------------

    def add_policy(self, record: PolicyRecord) -> None:
        with self._lock:
            if any(
                p.organization_id == record.organization_id
                and p.policy_version == record.policy_version
                for p in self.policies.values()
            ):
                raise ConflictError(
                    "This policy_version already exists for the organization.",
                    "Policy versions are immutable; publish a new version.",
                )
            self.policies[record.id] = record

    def list_policies(self, organization_id: UUID) -> list[PolicyRecord]:
        return sorted(
            (p for p in self.policies.values() if p.organization_id == organization_id),
            key=lambda p: p.created_at,
        )

    def get_policy(self, organization_id: UUID, policy_id: UUID) -> PolicyRecord | None:
        record = self.policies.get(policy_id)
        return record if record and record.organization_id == organization_id else None

    def add_decision_note(self, note: DecisionNote) -> None:
        with self._lock:
            if note.decision_id in self.notes:
                raise ConflictError("A note for this decision exists; notes are append-only.")
            self.notes[note.decision_id] = note

    def list_decision_notes(self, attestation_id: UUID) -> list[DecisionNote]:
        return sorted(
            (n for n in self.notes.values() if n.attestation_id == attestation_id),
            key=lambda n: n.created_at,
        )

    # -- jobs ------------------------------------------------------------------

    def enqueue_job(self, job: Job, outbox: list[OutboxMessage] | None = None) -> None:
        with self._lock:
            if self.find_job(job.kind, job.logical_id) is not None:
                raise ConflictError(
                    "A job for this work already exists.",
                    f"{job.kind.value} {job.logical_id} is already queued or ran.",
                )
            self.jobs[job.id] = job
            for message in outbox or []:
                self.add_outbox(message)

    def get_job(self, job_id: UUID) -> Job | None:
        return self.jobs.get(job_id)

    def find_job(self, kind: JobKind, logical_id: UUID) -> Job | None:
        return next(
            (j for j in self.jobs.values() if j.kind is kind and j.logical_id == logical_id),
            None,
        )

    def list_jobs(self, organization_id: UUID, status: JobStatus | None = None) -> list[Job]:
        return sorted(
            (
                j
                for j in self.jobs.values()
                if j.organization_id == organization_id and (status is None or j.status is status)
            ),
            key=lambda j: j.created_at,
        )

    def _running_for(self, organization_id: UUID) -> int:
        return sum(
            1
            for j in self.jobs.values()
            if j.organization_id == organization_id and j.status is JobStatus.RUNNING
        )

    def claim_job(
        self, worker_id: str, now: datetime, lease_seconds: float, kinds: list[JobKind]
    ) -> tuple[Job, ExecutionAttempt] | None:
        from datetime import timedelta

        with self._lock:
            candidates = sorted(
                (
                    j
                    for j in self.jobs.values()
                    if j.status is JobStatus.QUEUED and j.run_after <= now and j.kind in kinds
                ),
                key=lambda j: (j.created_at, str(j.id)),
            )
            for job in candidates:
                organization = self.organizations[job.organization_id]
                if self._running_for(job.organization_id) >= organization.max_concurrent_jobs:
                    continue
                claimed = job.model_copy(
                    update={
                        "status": JobStatus.RUNNING,
                        "attempts": job.attempts + 1,
                        "lease_owner": worker_id,
                        "lease_expires_at": now + timedelta(seconds=lease_seconds),
                    }
                )
                attempt = ExecutionAttempt(
                    id=self._new_id(),
                    job_id=job.id,
                    number=claimed.attempts,
                    worker_id=worker_id,
                    started_at=now,
                    last_heartbeat_at=now,
                    outcome=AttemptOutcome.RUNNING,
                )
                self.jobs[job.id] = claimed
                self.attempts[attempt.id] = attempt
                return claimed, attempt
            return None

    def heartbeat(
        self, job_id: UUID, attempt_id: UUID, now: datetime, lease_seconds: float
    ) -> Job | None:
        from datetime import timedelta

        with self._lock:
            job = self.jobs.get(job_id)
            attempt = self.attempts.get(attempt_id)
            if (
                job is None
                or attempt is None
                or job.status is not JobStatus.RUNNING
                or attempt.outcome is not AttemptOutcome.RUNNING
                or job.lease_owner != attempt.worker_id
            ):
                return None
            self.attempts[attempt_id] = attempt.model_copy(update={"last_heartbeat_at": now})
            job = job.model_copy(
                update={"lease_expires_at": now + timedelta(seconds=lease_seconds)}
            )
            self.jobs[job_id] = job
            return job

    def update_progress(self, job_id: UUID, progress: JsonObject) -> None:
        with self._lock:
            job = self.jobs[job_id]
            self.jobs[job_id] = job.model_copy(update={"progress": dict(progress)})

    def finish_attempt(
        self,
        job_id: UUID,
        attempt_id: UUID,
        outcome: AttemptOutcome,
        now: datetime,
        error: str | None,
        run_after: datetime | None,
    ) -> Job:
        with self._lock:
            job = self.jobs.get(job_id)
            attempt = self.attempts.get(attempt_id)
            if job is None or attempt is None:
                raise JobError("The job or attempt does not exist.")
            if attempt.outcome is not AttemptOutcome.RUNNING:
                raise JobError(
                    "The attempt is already closed.",
                    f"Attempt {attempt_id} is {attempt.outcome.value}; its lease was lost.",
                )
            self.attempts[attempt_id] = attempt.model_copy(
                update={"outcome": outcome, "finished_at": now, "error": error}
            )
            status, finished = self._next_status(job, outcome)
            self.jobs[job_id] = job.model_copy(
                update={
                    "status": status,
                    "lease_owner": None,
                    "lease_expires_at": None,
                    "last_error": error,
                    "run_after": run_after or job.run_after,
                    "finished_at": now if finished else None,
                }
            )
            return self.jobs[job_id]

    @staticmethod
    def _next_status(job: Job, outcome: AttemptOutcome) -> tuple[JobStatus, bool]:
        if outcome is AttemptOutcome.SUCCEEDED:
            return JobStatus.SUCCEEDED, True
        if outcome is AttemptOutcome.CANCELLED or job.cancel_requested:
            return JobStatus.CANCELLED, True
        if job.attempts >= job.max_attempts:
            return JobStatus.FAILED, True
        return JobStatus.QUEUED, False

    def request_cancel(self, job_id: UUID, now: datetime) -> Job | None:
        with self._lock:
            job = self.jobs.get(job_id)
            if job is None or job.is_final:
                return job
            if job.status is JobStatus.QUEUED:
                job = job.model_copy(
                    update={
                        "status": JobStatus.CANCELLED,
                        "cancel_requested": True,
                        "finished_at": now,
                    }
                )
            else:
                job = job.model_copy(update={"cancel_requested": True})
            self.jobs[job_id] = job
            return job

    def recover_expired_leases(self, now: datetime) -> list[Job]:
        with self._lock:
            recovered: list[Job] = []
            for job in list(self.jobs.values()):
                if (
                    job.status is not JobStatus.RUNNING
                    or job.lease_expires_at is None
                    or job.lease_expires_at >= now
                ):
                    continue
                for attempt in self.attempts.values():
                    if attempt.job_id == job.id and attempt.outcome is AttemptOutcome.RUNNING:
                        self.attempts[attempt.id] = attempt.model_copy(
                            update={
                                "outcome": AttemptOutcome.LOST,
                                "finished_at": now,
                                "error": "lease expired without a heartbeat",
                            }
                        )
                status, finished = self._next_status(job, AttemptOutcome.LOST)
                job = job.model_copy(
                    update={
                        "status": status,
                        "lease_owner": None,
                        "lease_expires_at": None,
                        "last_error": "lease expired without a heartbeat",
                        "run_after": now,
                        "finished_at": now if finished else None,
                    }
                )
                self.jobs[job.id] = job
                recovered.append(job)
            return recovered

    def list_attempts(self, job_id: UUID) -> list[ExecutionAttempt]:
        return sorted(
            (a for a in self.attempts.values() if a.job_id == job_id), key=lambda a: a.number
        )

    # -- outbox ----------------------------------------------------------------

    def add_outbox(self, message: OutboxMessage) -> bool:
        with self._lock:
            if any(m.dedup_key == message.dedup_key for m in self.outbox.values()):
                return False
            self.outbox[message.id] = message
            return True

    def claim_outbox(self, limit: int, now: datetime) -> list[OutboxMessage]:
        with self._lock:
            pending = sorted(
                (m for m in self.outbox.values() if m.delivered_at is None),
                key=lambda m: m.created_at,
            )
            return pending[:limit]

    def mark_outbox(self, message_id: UUID, now: datetime, error: str | None) -> None:
        with self._lock:
            message = self.outbox[message_id]
            self.outbox[message_id] = message.model_copy(
                update={
                    "attempts": message.attempts + 1,
                    "delivered_at": now if error is None else None,
                    "last_error": error,
                }
            )

    # -- ledger ----------------------------------------------------------------

    def add_usage_event(self, event: UsageEvent) -> None:
        with self._lock:
            if event.id in self.usage:
                raise ConflictError("This usage event id was already recorded.")
            if event.provider_request_id is not None and any(
                u.provider == event.provider and u.provider_request_id == event.provider_request_id
                for u in self.usage.values()
            ):
                raise ConflictError(
                    "This provider request was already recorded.",
                    f"{event.provider} request {event.provider_request_id} exists in the ledger.",
                )
            self.usage[event.id] = event

    def list_usage_events(
        self, organization_id: UUID, since: datetime | None = None
    ) -> list[UsageEvent]:
        return sorted(
            (
                u
                for u in self.usage.values()
                if u.organization_id == organization_id
                and (since is None or u.recorded_at >= since)
            ),
            key=lambda u: u.recorded_at,
        )

    def try_reserve(
        self, reservation: Reservation, limit_minor: int | None, since: datetime | None
    ) -> bool:
        with self._lock:
            if limit_minor is not None:
                totals = self.ledger_totals(reservation.organization_id, since)
                if (
                    totals.settled_minor + totals.reserved_minor + reservation.amount_minor
                    > limit_minor
                ):
                    return False
            self.reservations[reservation.id] = reservation
            return True

    def get_reservation(self, reservation_id: UUID) -> Reservation | None:
        return self.reservations.get(reservation_id)

    def close_reservation(
        self, reservation_id: UUID, settled_minor: int, now: datetime, released: bool
    ) -> Reservation:
        with self._lock:
            reservation = self.reservations[reservation_id]
            if reservation.state is not ReservationState.HELD:
                raise ConflictError("The reservation is already closed.")
            updated = reservation.model_copy(
                update={
                    "state": ReservationState.RELEASED if released else ReservationState.SETTLED,
                    "settled_minor": settled_minor,
                    "closed_at": now,
                }
            )
            self.reservations[reservation_id] = updated
            return updated

    def list_reservations(self, organization_id: UUID) -> list[Reservation]:
        return sorted(
            (r for r in self.reservations.values() if r.organization_id == organization_id),
            key=lambda r: r.created_at,
        )

    def ledger_totals(self, organization_id: UUID, since: datetime | None) -> LedgerTotals:
        events = self.list_usage_events(organization_id, since)
        held = [
            r
            for r in self.reservations.values()
            if r.organization_id == organization_id and r.state is ReservationState.HELD
        ]
        return LedgerTotals(
            settled_minor=sum(
                e.billable_minor for e in events if e.outcome is UsageOutcome.SETTLED
            ),
            reserved_minor=sum(r.amount_minor for r in held),
            allowance_used_minor=sum(e.allowance_minor for e in events),
            unknown_held_minor=sum(r.amount_minor for r in held if r.note.startswith("unknown")),
            pending_report_minor=sum(
                e.overage_minor for e in events if e.settlement.value == "pending"
            ),
        )

    def add_spending_limit(self, limit: SpendingLimit) -> None:
        with self._lock:
            self.limits.append(limit)

    def get_spending_limit(self, organization_id: UUID) -> SpendingLimit | None:
        candidates = [lim for lim in self.limits if lim.organization_id == organization_id]
        return max(candidates, key=lambda lim: lim.set_at, default=None)

    def mark_usage_reported(self, report: MeterReport) -> bool:
        with self._lock:
            if report.usage_event_id in self.meter_reports:
                return False
            self.meter_reports[report.usage_event_id] = report
            event = self.usage[report.usage_event_id]
            self.usage[report.usage_event_id] = event.model_copy(
                update={"settlement": SettlementState.REPORTED}
            )
            return True

    def list_unreported_usage(self, limit: int) -> list[UsageEvent]:
        pending = sorted(
            (u for u in self.usage.values() if u.settlement.value == "pending"),
            key=lambda u: u.recorded_at,
        )
        return pending[:limit]

    # -- billing ---------------------------------------------------------------

    def upsert_subscription(self, subscription: Subscription) -> None:
        with self._lock:
            self.subscriptions[subscription.organization_id] = subscription

    def get_subscription(self, organization_id: UUID) -> Subscription | None:
        return self.subscriptions.get(organization_id)

    def find_subscription_by_customer(self, provider: str, customer_id: str) -> Subscription | None:
        return next(
            (
                s
                for s in self.subscriptions.values()
                if s.provider == provider and s.provider_customer_id == customer_id
            ),
            None,
        )

    def record_provider_event(self, event: ProviderEvent) -> bool:
        with self._lock:
            key = (event.provider, event.event_id)
            if key in self.provider_events:
                return False
            self.provider_events[key] = event
            return True

    def mark_provider_event(self, provider: str, event_id: str, result: str) -> None:
        with self._lock:
            event = self.provider_events[(provider, event_id)]
            self.provider_events[(provider, event_id)] = event.model_copy(
                update={"processed": True, "result": result}
            )

    # -- keys, artifacts, schedules --------------------------------------------

    def add_signing_key(self, record: SigningKeyRecord) -> None:
        with self._lock:
            if record.key_id in self.keys:
                raise ConflictError("This key id is already registered.")
            self.keys[record.key_id] = record

    def get_signing_key(self, key_id: str) -> SigningKeyRecord | None:
        return self.keys.get(key_id)

    def revoke_signing_key(self, key_id: str, at: datetime, reason: str) -> SigningKeyRecord | None:
        with self._lock:
            record = self.keys.get(key_id)
            if record is None:
                return None
            if record.revoked_at is not None:
                return record
            updated = record.model_copy(update={"revoked_at": at, "revocation_reason": reason})
            self.keys[key_id] = updated
            return updated

    def list_signing_keys(self) -> list[SigningKeyRecord]:
        return sorted(self.keys.values(), key=lambda k: k.created_at)

    def add_external_artifact(self, artifact: ExternalArtifact) -> None:
        with self._lock:
            self.artifacts[artifact.id] = artifact

    def list_external_artifacts(self, attestation_id: UUID) -> list[ExternalArtifact]:
        return sorted(
            (a for a in self.artifacts.values() if a.attestation_id == attestation_id),
            key=lambda a: a.created_at,
        )

    def add_schedule(self, schedule: ReevaluationSchedule) -> None:
        with self._lock:
            self.schedules[schedule.id] = schedule

    def list_schedules(self, organization_id: UUID) -> list[ReevaluationSchedule]:
        return sorted(
            (s for s in self.schedules.values() if s.organization_id == organization_id),
            key=lambda s: s.created_at,
        )

    def due_schedules(self, now: datetime) -> list[ReevaluationSchedule]:
        return sorted(
            (s for s in self.schedules.values() if s.enabled and s.next_run_at <= now),
            key=lambda s: s.next_run_at,
        )

    def update_schedule(self, schedule: ReevaluationSchedule) -> None:
        with self._lock:
            self.schedules[schedule.id] = schedule

    def close(self) -> None:
        return None

    def _new_id(self) -> UUID:
        import uuid

        return self._ids.new_id() if self._ids is not None else uuid.uuid4()
