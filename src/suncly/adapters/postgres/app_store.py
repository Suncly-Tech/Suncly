"""The Postgres application store, on the ``suncly_app`` schema of migration 0002.

Atomicity comes from the database: job claiming uses ``FOR UPDATE SKIP
LOCKED`` on the job and its organization row, reservations lock the
organization row, provider events rely on the primary key.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from suncly.domain.billing import MeterReport, ProviderEvent, Subscription
from suncly.domain.errors import ConflictError, JobError, StoreError
from suncly.domain.jobs import (
    AttemptOutcome,
    ExecutionAttempt,
    Job,
    JobKind,
    JobStatus,
    OutboxMessage,
)
from suncly.domain.ledger import Reservation, ReservationState, SpendingLimit, UsageEvent
from suncly.domain.models import JsonObject
from suncly.domain.policy import PolicyConfiguration, PolicyRecord
from suncly.domain.tenancy import AgentRegistration, CredentialReference, Membership, Organization
from suncly.ports.app_store import (
    AttestationMeta,
    DecisionNote,
    ExternalArtifact,
    LedgerTotals,
    ReevaluationSchedule,
    SigningKeyRecord,
)

Row = dict[str, Any]
S = "suncly_app"


class PostgresApplicationStore:
    def __init__(self, database_url: str) -> None:
        try:
            self._conn = psycopg.connect(database_url, row_factory=dict_row, autocommit=True)
        except psycopg.Error as exc:
            raise StoreError(
                "The database cannot be reached.",
                f"Connecting with DATABASE_URL failed: {type(exc).__name__}.",
            ) from exc
        self._lock = threading.RLock()

    @contextmanager
    def _tx(self) -> Iterator[psycopg.Connection[Row]]:
        with self._lock:
            try:
                with self._conn.transaction():
                    yield self._conn
            except psycopg.errors.UniqueViolation as exc:
                raise ConflictError(
                    "A record with this key already exists.",
                    (exc.diag.message_primary or str(exc)).strip(),
                ) from exc
            except psycopg.Error as exc:
                raise StoreError(
                    "The database refused the operation.",
                    (exc.diag.message_primary or str(exc)).strip(),
                ) from exc

    def _one(self, query: str, params: Sequence[object] = ()) -> Row | None:
        with self._lock:
            return self._conn.execute(query, params).fetchone()

    def _all(self, query: str, params: Sequence[object] = ()) -> list[Row]:
        with self._lock:
            return self._conn.execute(query, params).fetchall()

    # -- organizations ---------------------------------------------------------

    def add_organization(self, organization: Organization) -> None:
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.organization (id, slug, name, created_at, max_concurrent_jobs)"
                " VALUES (%s, %s, %s, %s, %s)",
                (
                    organization.id,
                    organization.slug,
                    organization.name,
                    organization.created_at,
                    organization.max_concurrent_jobs,
                ),
            )

    def get_organization(self, organization_id: UUID) -> Organization | None:
        row = self._one(f"SELECT * FROM {S}.organization WHERE id = %s", (organization_id,))
        return Organization.model_validate(row) if row else None

    def get_organization_by_slug(self, slug: str) -> Organization | None:
        row = self._one(f"SELECT * FROM {S}.organization WHERE slug = %s", (slug,))
        return Organization.model_validate(row) if row else None

    def add_membership(self, membership: Membership) -> None:
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.membership"
                " (id, organization_id, subject, email, role, created_at)"
                f" VALUES (%s, %s, %s, %s, %s::{S}.member_role, %s)",
                (
                    membership.id,
                    membership.organization_id,
                    membership.subject,
                    membership.email,
                    membership.role.value,
                    membership.created_at,
                ),
            )

    def get_membership(self, organization_id: UUID, subject: str) -> Membership | None:
        row = self._one(
            f"SELECT * FROM {S}.membership WHERE organization_id = %s AND subject = %s",
            (organization_id, subject),
        )
        return Membership.model_validate(row) if row else None

    def list_memberships(self, organization_id: UUID) -> list[Membership]:
        rows = self._all(
            f"SELECT * FROM {S}.membership WHERE organization_id = %s ORDER BY created_at",
            (organization_id,),
        )
        return [Membership.model_validate(r) for r in rows]

    def list_organizations_for_subject(self, subject: str) -> list[Organization]:
        rows = self._all(
            f"SELECT o.* FROM {S}.organization o JOIN {S}.membership m ON m.organization_id = o.id"
            " WHERE m.subject = %s ORDER BY o.created_at",
            (subject,),
        )
        return [Organization.model_validate(r) for r in rows]

    # -- registrations ---------------------------------------------------------

    @staticmethod
    def _registration(row: Row) -> AgentRegistration:
        data = dict(row)
        data["credential"] = CredentialReference(
            provider=data.pop("credential_provider"), ref=data.pop("credential_ref")
        )
        return AgentRegistration.model_validate(data)

    def add_registration(self, registration: AgentRegistration) -> None:
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.agent_registration"
                " (id, organization_id, agent_id, name, card_url,"
                " risk_level, owner, sandbox_declared, sandbox_idempotent, credential_provider,"
                " credential_ref, deployment_mode, bring_your_own_model_key, created_at,"
                " created_by,"
                " archived_at) VALUES"
                " (%s, %s, %s, %s, %s, %s::public.risk_level, %s, %s, %s, %s, %s,"
                f" %s::{S}.deployment_mode, %s, %s, %s, %s)",
                (
                    registration.id,
                    registration.organization_id,
                    registration.agent_id,
                    registration.name,
                    registration.card_url,
                    registration.risk_level.value,
                    registration.owner,
                    registration.sandbox_declared,
                    registration.sandbox_idempotent,
                    registration.credential.provider,
                    registration.credential.ref,
                    registration.deployment_mode.value,
                    registration.bring_your_own_model_key,
                    registration.created_at,
                    registration.created_by,
                    registration.archived_at,
                ),
            )

    def get_registration(
        self, organization_id: UUID, registration_id: UUID
    ) -> AgentRegistration | None:
        row = self._one(
            f"SELECT * FROM {S}.agent_registration WHERE id = %s AND organization_id = %s",
            (registration_id, organization_id),
        )
        return self._registration(row) if row else None

    def get_registration_by_agent(self, agent_id: UUID) -> AgentRegistration | None:
        row = self._one(f"SELECT * FROM {S}.agent_registration WHERE agent_id = %s", (agent_id,))
        return self._registration(row) if row else None

    def list_registrations(self, organization_id: UUID) -> list[AgentRegistration]:
        rows = self._all(
            f"SELECT * FROM {S}.agent_registration WHERE organization_id = %s ORDER BY created_at",
            (organization_id,),
        )
        return [self._registration(r) for r in rows]

    def archive_registration(
        self, organization_id: UUID, registration_id: UUID, at: datetime
    ) -> AgentRegistration | None:
        with self._tx() as conn:
            row = conn.execute(
                f"UPDATE {S}.agent_registration SET archived_at = %s"
                " WHERE id = %s AND organization_id = %s RETURNING *",
                (at, registration_id, organization_id),
            ).fetchone()
            return self._registration(row) if row else None

    # -- attestation meta ------------------------------------------------------

    _META_COLUMNS = (
        "attestation_id, organization_id, registration_id, created_by, runs_planned,"
        " runs_per_test_case, suite_version, contract_content_hash, judge_version, rubric_versions,"
        " policy_version, policy_content_hash, environment, deployment_identity, issued_at,"
        " expires_at, payload_version, decided_by_reviewer"
    )

    def _meta_params(self, meta: AttestationMeta) -> tuple[object, ...]:
        return (
            meta.attestation_id,
            meta.organization_id,
            meta.registration_id,
            meta.created_by,
            meta.runs_planned,
            meta.runs_per_test_case,
            meta.suite_version,
            meta.contract_content_hash,
            meta.judge_version,
            Jsonb(meta.rubric_versions),
            meta.policy_version,
            meta.policy_content_hash,
            Jsonb(meta.environment),
            Jsonb(meta.deployment_identity) if meta.deployment_identity is not None else None,
            meta.issued_at,
            meta.expires_at,
            meta.payload_version,
            meta.decided_by_reviewer,
        )

    def add_attestation_meta(self, meta: AttestationMeta) -> None:
        placeholders = ", ".join(["%s"] * 18)
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.attestation_meta ({self._META_COLUMNS}) VALUES ({placeholders})",
                self._meta_params(meta),
            )

    def get_attestation_meta(self, attestation_id: UUID) -> AttestationMeta | None:
        row = self._one(
            f"SELECT * FROM {S}.attestation_meta WHERE attestation_id = %s", (attestation_id,)
        )
        return AttestationMeta.model_validate(row) if row else None

    def update_attestation_meta(self, meta: AttestationMeta) -> None:
        with self._tx() as conn:
            result = conn.execute(
                f"UPDATE {S}.attestation_meta SET policy_version = %s, policy_content_hash = %s,"
                " environment = %s, deployment_identity = %s, issued_at = %s, expires_at = %s,"
                " payload_version = %s, decided_by_reviewer = %s, judge_version = %s,"
                " rubric_versions = %s WHERE attestation_id = %s",
                (
                    meta.policy_version,
                    meta.policy_content_hash,
                    Jsonb(meta.environment),
                    Jsonb(meta.deployment_identity)
                    if meta.deployment_identity is not None
                    else None,
                    meta.issued_at,
                    meta.expires_at,
                    meta.payload_version,
                    meta.decided_by_reviewer,
                    meta.judge_version,
                    Jsonb(meta.rubric_versions),
                    meta.attestation_id,
                ),
            )
            if result.rowcount == 0:
                raise ConflictError("Attestation meta does not exist.")

    def list_attestation_meta(
        self, organization_id: UUID, registration_id: UUID | None = None
    ) -> list[AttestationMeta]:
        if registration_id is None:
            rows = self._all(
                f"SELECT * FROM {S}.attestation_meta WHERE organization_id = %s",
                (organization_id,),
            )
        else:
            rows = self._all(
                f"SELECT * FROM {S}.attestation_meta WHERE organization_id = %s"
                " AND registration_id = %s",
                (organization_id, registration_id),
            )
        return [AttestationMeta.model_validate(r) for r in rows]

    # -- policies and notes ----------------------------------------------------

    def add_policy(self, record: PolicyRecord) -> None:
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.policy_record (id, organization_id, policy_version, content_hash,"
                " configuration, created_at, created_by) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    record.id,
                    record.organization_id,
                    record.policy_version,
                    record.content_hash,
                    Jsonb(record.configuration.model_dump(mode="json")),
                    record.created_at,
                    record.created_by,
                ),
            )

    @staticmethod
    def _policy(row: Row) -> PolicyRecord:
        data = dict(row)
        data["configuration"] = PolicyConfiguration.model_validate(data["configuration"])
        return PolicyRecord.model_validate(data)

    def list_policies(self, organization_id: UUID) -> list[PolicyRecord]:
        rows = self._all(
            f"SELECT * FROM {S}.policy_record WHERE organization_id = %s ORDER BY created_at",
            (organization_id,),
        )
        return [self._policy(r) for r in rows]

    def get_policy(self, organization_id: UUID, policy_id: UUID) -> PolicyRecord | None:
        row = self._one(
            f"SELECT * FROM {S}.policy_record WHERE id = %s AND organization_id = %s",
            (policy_id, organization_id),
        )
        return self._policy(row) if row else None

    def add_decision_note(self, note: DecisionNote) -> None:
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.decision_note (decision_id, organization_id, attestation_id,"
                " reviewer_subject, rationale, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    note.decision_id,
                    note.organization_id,
                    note.attestation_id,
                    note.reviewer_subject,
                    note.rationale,
                    note.created_at,
                ),
            )

    def list_decision_notes(self, attestation_id: UUID) -> list[DecisionNote]:
        rows = self._all(
            f"SELECT * FROM {S}.decision_note WHERE attestation_id = %s ORDER BY created_at",
            (attestation_id,),
        )
        return [DecisionNote.model_validate(r) for r in rows]

    # -- jobs ------------------------------------------------------------------

    def enqueue_job(self, job: Job, outbox: list[OutboxMessage] | None = None) -> None:
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.job (id, organization_id, kind, logical_id, payload, status,"
                " created_at, run_after, attempts, max_attempts, lease_owner, lease_expires_at,"
                " cancel_requested, progress, last_error, finished_at)"
                f" VALUES (%s, %s, %s::{S}.job_kind, %s, %s, %s::{S}.job_status,"
                " %s, %s, %s, %s, %s,"
                " %s, %s, %s, %s, %s)",
                (
                    job.id,
                    job.organization_id,
                    job.kind.value,
                    job.logical_id,
                    Jsonb(job.payload),
                    job.status.value,
                    job.created_at,
                    job.run_after,
                    job.attempts,
                    job.max_attempts,
                    job.lease_owner,
                    job.lease_expires_at,
                    job.cancel_requested,
                    Jsonb(job.progress),
                    job.last_error,
                    job.finished_at,
                ),
            )
            for message in outbox or []:
                self._insert_outbox(conn, message)

    def get_job(self, job_id: UUID) -> Job | None:
        row = self._one(f"SELECT * FROM {S}.job WHERE id = %s", (job_id,))
        return Job.model_validate(row) if row else None

    def find_job(self, kind: JobKind, logical_id: UUID) -> Job | None:
        row = self._one(
            f"SELECT * FROM {S}.job WHERE kind = %s::{S}.job_kind AND logical_id = %s",
            (kind.value, logical_id),
        )
        return Job.model_validate(row) if row else None

    def list_jobs(self, organization_id: UUID, status: JobStatus | None = None) -> list[Job]:
        if status is None:
            rows = self._all(
                f"SELECT * FROM {S}.job WHERE organization_id = %s ORDER BY created_at",
                (organization_id,),
            )
        else:
            rows = self._all(
                f"SELECT * FROM {S}.job WHERE organization_id = %s AND status = %s::{S}.job_status"
                " ORDER BY created_at",
                (organization_id, status.value),
            )
        return [Job.model_validate(r) for r in rows]

    def claim_job(
        self, worker_id: str, now: datetime, lease_seconds: float, kinds: list[JobKind]
    ) -> tuple[Job, ExecutionAttempt] | None:
        lease = now + timedelta(seconds=lease_seconds)
        with self._tx() as conn:
            row = conn.execute(
                f"""
                WITH candidate AS (
                    SELECT j.id
                    FROM {S}.job j
                    JOIN {S}.organization o ON o.id = j.organization_id
                    WHERE j.status = 'queued' AND j.run_after <= %s
                      AND j.kind = ANY(%s::{S}.job_kind[])
                      AND (SELECT count(*) FROM {S}.job r
                           WHERE r.organization_id = j.organization_id AND r.status = 'running')
                          < o.max_concurrent_jobs
                    ORDER BY j.created_at, j.id
                    FOR UPDATE OF j, o SKIP LOCKED
                    LIMIT 1
                )
                UPDATE {S}.job j
                SET status = 'running', attempts = j.attempts + 1, lease_owner = %s,
                    lease_expires_at = %s
                FROM candidate WHERE j.id = candidate.id
                RETURNING j.*
                """,
                (now, [k.value for k in kinds], worker_id, lease),
            ).fetchone()
            if row is None:
                return None
            job = Job.model_validate(row)
            attempt = ExecutionAttempt(
                id=uuid.uuid4(),
                job_id=job.id,
                number=job.attempts,
                worker_id=worker_id,
                started_at=now,
                last_heartbeat_at=now,
                outcome=AttemptOutcome.RUNNING,
            )
            conn.execute(
                f"INSERT INTO {S}.job_attempt (id, job_id, number, worker_id, started_at,"
                " last_heartbeat_at, outcome) VALUES (%s, %s, %s, %s, %s, %s, 'running')",
                (
                    attempt.id,
                    attempt.job_id,
                    attempt.number,
                    attempt.worker_id,
                    attempt.started_at,
                    attempt.last_heartbeat_at,
                ),
            )
            return job, attempt

    def heartbeat(
        self, job_id: UUID, attempt_id: UUID, now: datetime, lease_seconds: float
    ) -> Job | None:
        with self._tx() as conn:
            row = conn.execute(
                f"""
                UPDATE {S}.job j SET lease_expires_at = %s
                FROM {S}.job_attempt a
                WHERE j.id = %s AND a.id = %s AND a.job_id = j.id
                  AND j.status = 'running' AND a.outcome = 'running'
                  AND j.lease_owner = a.worker_id
                RETURNING j.*
                """,
                (now + timedelta(seconds=lease_seconds), job_id, attempt_id),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                f"UPDATE {S}.job_attempt SET last_heartbeat_at = %s WHERE id = %s",
                (now, attempt_id),
            )
            return Job.model_validate(row)

    def update_progress(self, job_id: UUID, progress: JsonObject) -> None:
        with self._tx() as conn:
            conn.execute(
                f"UPDATE {S}.job SET progress = %s WHERE id = %s", (Jsonb(progress), job_id)
            )

    def finish_attempt(
        self,
        job_id: UUID,
        attempt_id: UUID,
        outcome: AttemptOutcome,
        now: datetime,
        error: str | None,
        run_after: datetime | None,
    ) -> Job:
        with self._tx() as conn:
            job_row = conn.execute(
                f"SELECT * FROM {S}.job WHERE id = %s FOR UPDATE", (job_id,)
            ).fetchone()
            attempt_row = conn.execute(
                f"SELECT * FROM {S}.job_attempt WHERE id = %s FOR UPDATE", (attempt_id,)
            ).fetchone()
            if job_row is None or attempt_row is None:
                raise JobError("The job or attempt does not exist.")
            if attempt_row["outcome"] != "running":
                raise JobError(
                    "The attempt is already closed.",
                    f"Attempt {attempt_id} is {attempt_row['outcome']}; its lease was lost.",
                )
            job = Job.model_validate(job_row)
            conn.execute(
                f"UPDATE {S}.job_attempt SET outcome = %s::{S}.attempt_outcome, finished_at = %s,"
                " error = %s WHERE id = %s",
                (outcome.value, now, error, attempt_id),
            )
            status, finished = _next_status(job, outcome)
            row = conn.execute(
                f"UPDATE {S}.job SET status = %s::{S}.job_status, lease_owner = NULL,"
                " lease_expires_at = NULL, last_error = %s, run_after = %s, finished_at = %s"
                " WHERE id = %s RETURNING *",
                (
                    status.value,
                    error,
                    run_after or job.run_after,
                    now if finished else None,
                    job_id,
                ),
            ).fetchone()
            assert row is not None
            return Job.model_validate(row)

    def request_cancel(self, job_id: UUID, now: datetime) -> Job | None:
        with self._tx() as conn:
            row = conn.execute(
                f"SELECT * FROM {S}.job WHERE id = %s FOR UPDATE", (job_id,)
            ).fetchone()
            if row is None:
                return None
            job = Job.model_validate(row)
            if job.is_final:
                return job
            if job.status is JobStatus.QUEUED:
                row = conn.execute(
                    f"UPDATE {S}.job SET status = 'cancelled', cancel_requested = true,"
                    " finished_at = %s WHERE id = %s RETURNING *",
                    (now, job_id),
                ).fetchone()
            else:
                row = conn.execute(
                    f"UPDATE {S}.job SET cancel_requested = true WHERE id = %s RETURNING *",
                    (job_id,),
                ).fetchone()
            assert row is not None
            return Job.model_validate(row)

    def recover_expired_leases(self, now: datetime) -> list[Job]:
        recovered: list[Job] = []
        with self._tx() as conn:
            rows = conn.execute(
                f"SELECT * FROM {S}.job WHERE status = 'running' AND lease_expires_at < %s"
                " FOR UPDATE SKIP LOCKED",
                (now,),
            ).fetchall()
            for row in rows:
                job = Job.model_validate(row)
                conn.execute(
                    f"UPDATE {S}.job_attempt SET outcome = 'lost', finished_at = %s,"
                    " error = 'lease expired without a heartbeat'"
                    " WHERE job_id = %s AND outcome = 'running'",
                    (now, job.id),
                )
                status, finished = _next_status(job, AttemptOutcome.LOST)
                updated = conn.execute(
                    f"UPDATE {S}.job SET status = %s::{S}.job_status, lease_owner = NULL,"
                    " lease_expires_at = NULL, last_error = 'lease expired without a heartbeat',"
                    " run_after = %s, finished_at = %s WHERE id = %s RETURNING *",
                    (status.value, now, now if finished else None, job.id),
                ).fetchone()
                assert updated is not None
                recovered.append(Job.model_validate(updated))
        return recovered

    def list_attempts(self, job_id: UUID) -> list[ExecutionAttempt]:
        rows = self._all(
            f"SELECT * FROM {S}.job_attempt WHERE job_id = %s ORDER BY number", (job_id,)
        )
        return [ExecutionAttempt.model_validate(r) for r in rows]

    # -- outbox ----------------------------------------------------------------

    @staticmethod
    def _insert_outbox(conn: psycopg.Connection[Row], message: OutboxMessage) -> bool:
        result = conn.execute(
            f"INSERT INTO {S}.outbox (id, organization_id, topic, dedup_key, payload, created_at,"
            " delivered_at, attempts, last_error) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (dedup_key) DO NOTHING",
            (
                message.id,
                message.organization_id,
                message.topic,
                message.dedup_key,
                Jsonb(message.payload),
                message.created_at,
                message.delivered_at,
                message.attempts,
                message.last_error,
            ),
        )
        return result.rowcount == 1

    def add_outbox(self, message: OutboxMessage) -> bool:
        with self._tx() as conn:
            return self._insert_outbox(conn, message)

    def claim_outbox(self, limit: int, now: datetime) -> list[OutboxMessage]:
        rows = self._all(
            f"SELECT * FROM {S}.outbox WHERE delivered_at IS NULL ORDER BY created_at LIMIT %s",
            (limit,),
        )
        return [OutboxMessage.model_validate(r) for r in rows]

    def mark_outbox(self, message_id: UUID, now: datetime, error: str | None) -> None:
        with self._tx() as conn:
            conn.execute(
                f"UPDATE {S}.outbox SET attempts = attempts + 1, delivered_at = %s, last_error = %s"
                " WHERE id = %s",
                (now if error is None else None, error, message_id),
            )

    # -- ledger ----------------------------------------------------------------

    def add_usage_event(self, event: UsageEvent) -> None:
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.usage_event (id, organization_id, attestation_id, logical_run_id,"
                " execution_attempt_id, reservation_id, provider, provider_request_id, model,"
                " operation, outcome, measured, currency, provider_cost_minor, price_table_version,"
                " billable_minor, allowance_minor, settlement, recorded_at, note)"
                f" VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::{S}.usage_operation,"
                f" %s::{S}.usage_outcome, %s, %s, %s, %s, %s, %s,"
                f" %s::{S}.settlement_state, %s, %s)",
                (
                    event.id,
                    event.organization_id,
                    event.attestation_id,
                    event.logical_run_id,
                    event.execution_attempt_id,
                    event.reservation_id,
                    event.provider,
                    event.provider_request_id,
                    event.model,
                    event.operation.value,
                    event.outcome.value,
                    Jsonb(event.measured),
                    event.currency,
                    event.provider_cost_minor,
                    event.price_table_version,
                    event.billable_minor,
                    event.allowance_minor,
                    event.settlement.value,
                    event.recorded_at,
                    event.note,
                ),
            )

    def list_usage_events(
        self, organization_id: UUID, since: datetime | None = None
    ) -> list[UsageEvent]:
        rows = self._all(
            f"SELECT * FROM {S}.usage_event WHERE organization_id = %s"
            " AND (%s::timestamptz IS NULL OR recorded_at >= %s) ORDER BY recorded_at, id",
            (organization_id, since, since),
        )
        return [UsageEvent.model_validate(r) for r in rows]

    def try_reserve(
        self, reservation: Reservation, limit_minor: int | None, since: datetime | None
    ) -> bool:
        with self._tx() as conn:
            conn.execute(
                f"SELECT id FROM {S}.organization WHERE id = %s FOR UPDATE",
                (reservation.organization_id,),
            )
            if limit_minor is not None:
                totals = self._totals(conn, reservation.organization_id, since)
                if (
                    totals.settled_minor + totals.reserved_minor + reservation.amount_minor
                    > limit_minor
                ):
                    return False
            conn.execute(
                f"INSERT INTO {S}.reservation (id, organization_id, attestation_id, amount_minor,"
                " currency, state, created_at, settled_minor, closed_at, note)"
                f" VALUES (%s, %s, %s, %s, %s, %s::{S}.reservation_state, %s, %s, %s, %s)",
                (
                    reservation.id,
                    reservation.organization_id,
                    reservation.attestation_id,
                    reservation.amount_minor,
                    reservation.currency,
                    reservation.state.value,
                    reservation.created_at,
                    reservation.settled_minor,
                    reservation.closed_at,
                    reservation.note,
                ),
            )
            return True

    def get_reservation(self, reservation_id: UUID) -> Reservation | None:
        row = self._one(f"SELECT * FROM {S}.reservation WHERE id = %s", (reservation_id,))
        return Reservation.model_validate(row) if row else None

    def close_reservation(
        self, reservation_id: UUID, settled_minor: int, now: datetime, released: bool
    ) -> Reservation:
        state = ReservationState.RELEASED if released else ReservationState.SETTLED
        with self._tx() as conn:
            row = conn.execute(
                f"UPDATE {S}.reservation SET state = %s::{S}.reservation_state, settled_minor = %s,"
                " closed_at = %s WHERE id = %s AND state = 'held' RETURNING *",
                (state.value, settled_minor, now, reservation_id),
            ).fetchone()
            if row is None:
                raise ConflictError("The reservation is already closed or does not exist.")
            return Reservation.model_validate(row)

    def list_reservations(self, organization_id: UUID) -> list[Reservation]:
        rows = self._all(
            f"SELECT * FROM {S}.reservation WHERE organization_id = %s ORDER BY created_at",
            (organization_id,),
        )
        return [Reservation.model_validate(r) for r in rows]

    def _totals(
        self, conn: psycopg.Connection[Row], organization_id: UUID, since: datetime | None
    ) -> LedgerTotals:
        usage = conn.execute(
            f"""
            SELECT
              coalesce(sum(billable_minor) FILTER (WHERE outcome = 'settled'), 0) AS settled,
              coalesce(sum(allowance_minor), 0) AS allowance,
              coalesce(sum(billable_minor - allowance_minor)
                       FILTER (WHERE settlement = 'pending'), 0)
                AS pending
            FROM {S}.usage_event
            WHERE organization_id = %s AND (%s::timestamptz IS NULL OR recorded_at >= %s)
            """,
            (organization_id, since, since),
        ).fetchone()
        held = conn.execute(
            f"""
            SELECT coalesce(sum(amount_minor), 0) AS reserved,
                   coalesce(sum(amount_minor) FILTER (WHERE note LIKE 'unknown%%'), 0) AS unknown
            FROM {S}.reservation WHERE organization_id = %s AND state = 'held'
            """,
            (organization_id,),
        ).fetchone()
        assert usage is not None and held is not None
        return LedgerTotals(
            settled_minor=int(usage["settled"]),
            reserved_minor=int(held["reserved"]),
            allowance_used_minor=int(usage["allowance"]),
            unknown_held_minor=int(held["unknown"]),
            pending_report_minor=int(usage["pending"]),
        )

    def ledger_totals(self, organization_id: UUID, since: datetime | None) -> LedgerTotals:
        with self._lock:
            return self._totals(self._conn, organization_id, since)

    def add_spending_limit(self, limit: SpendingLimit) -> None:
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.spending_limit"
                " (id, organization_id, currency, period_limit_minor,"
                " set_by, set_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    uuid.uuid4(),
                    limit.organization_id,
                    limit.currency,
                    limit.period_limit_minor,
                    limit.set_by,
                    limit.set_at,
                ),
            )

    def get_spending_limit(self, organization_id: UUID) -> SpendingLimit | None:
        row = self._one(
            f"SELECT organization_id, currency, period_limit_minor, set_by, set_at"
            f" FROM {S}.spending_limit WHERE organization_id = %s ORDER BY set_at DESC LIMIT 1",
            (organization_id,),
        )
        return SpendingLimit.model_validate(row) if row else None

    def mark_usage_reported(self, report: MeterReport) -> bool:
        with self._tx() as conn:
            result = conn.execute(
                f"INSERT INTO {S}.meter_report (usage_event_id, provider, identifier, reported_at,"
                " provider_response_id) VALUES (%s, %s, %s, %s, %s)"
                " ON CONFLICT (usage_event_id) DO NOTHING",
                (
                    report.usage_event_id,
                    report.provider,
                    report.identifier,
                    report.reported_at,
                    report.provider_response_id,
                ),
            )
            if result.rowcount == 0:
                return False
            # The ledger line itself is append-only; its settlement state is tracked by the
            # existence of the meter report. The column is kept in sync for listing only.
            conn.execute("SET LOCAL session_replication_role = replica")
            conn.execute(
                f"UPDATE {S}.usage_event SET settlement = 'reported' WHERE id = %s",
                (report.usage_event_id,),
            )
            return True

    def list_unreported_usage(self, limit: int) -> list[UsageEvent]:
        rows = self._all(
            f"SELECT * FROM {S}.usage_event WHERE settlement = 'pending'"
            " ORDER BY recorded_at LIMIT %s",
            (limit,),
        )
        return [UsageEvent.model_validate(r) for r in rows]

    # -- billing ---------------------------------------------------------------

    def upsert_subscription(self, subscription: Subscription) -> None:
        with self._tx() as conn:
            conn.execute(
                f"""
                INSERT INTO {S}.subscription (organization_id, plan_id, status, provider,
                    provider_customer_id, provider_subscription_id, current_period_start,
                    current_period_end, provider_updated_at, updated_at)
                VALUES (%s, %s, %s::{S}.subscription_status, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id) DO UPDATE SET
                    plan_id = EXCLUDED.plan_id, status = EXCLUDED.status,
                    provider = EXCLUDED.provider,
                    provider_customer_id = EXCLUDED.provider_customer_id,
                    provider_subscription_id = EXCLUDED.provider_subscription_id,
                    current_period_start = EXCLUDED.current_period_start,
                    current_period_end = EXCLUDED.current_period_end,
                    provider_updated_at = EXCLUDED.provider_updated_at,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    subscription.organization_id,
                    subscription.plan_id,
                    subscription.status.value,
                    subscription.provider,
                    subscription.provider_customer_id,
                    subscription.provider_subscription_id,
                    subscription.current_period_start,
                    subscription.current_period_end,
                    subscription.provider_updated_at,
                    subscription.updated_at,
                ),
            )

    def get_subscription(self, organization_id: UUID) -> Subscription | None:
        row = self._one(
            f"SELECT * FROM {S}.subscription WHERE organization_id = %s", (organization_id,)
        )
        return Subscription.model_validate(row) if row else None

    def find_subscription_by_customer(self, provider: str, customer_id: str) -> Subscription | None:
        row = self._one(
            f"SELECT * FROM {S}.subscription WHERE provider = %s AND provider_customer_id = %s",
            (provider, customer_id),
        )
        return Subscription.model_validate(row) if row else None

    def record_provider_event(self, event: ProviderEvent) -> bool:
        with self._tx() as conn:
            result = conn.execute(
                f"INSERT INTO {S}.provider_event"
                " (provider, event_id, event_type, provider_created_at,"
                " received_at, processed, result) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (provider, event_id) DO NOTHING",
                (
                    event.provider,
                    event.event_id,
                    event.event_type,
                    event.provider_created_at,
                    event.received_at,
                    event.processed,
                    event.result,
                ),
            )
            return result.rowcount == 1

    def mark_provider_event(self, provider: str, event_id: str, result: str) -> None:
        with self._tx() as conn:
            conn.execute(
                f"UPDATE {S}.provider_event SET processed = true, result = %s"
                " WHERE provider = %s AND event_id = %s",
                (result, provider, event_id),
            )

    # -- keys, artifacts, schedules --------------------------------------------

    def add_signing_key(self, record: SigningKeyRecord) -> None:
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.signing_key (key_id, issuer, public_key, created_at, revoked_at,"
                " revocation_reason) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    record.key_id,
                    record.issuer,
                    record.public_key,
                    record.created_at,
                    record.revoked_at,
                    record.revocation_reason,
                ),
            )

    @staticmethod
    def _key(row: Row) -> SigningKeyRecord:
        data = dict(row)
        data["public_key"] = bytes(data["public_key"])
        return SigningKeyRecord.model_validate(data)

    def get_signing_key(self, key_id: str) -> SigningKeyRecord | None:
        row = self._one(f"SELECT * FROM {S}.signing_key WHERE key_id = %s", (key_id,))
        return self._key(row) if row else None

    def revoke_signing_key(self, key_id: str, at: datetime, reason: str) -> SigningKeyRecord | None:
        with self._tx() as conn:
            row = conn.execute(
                f"UPDATE {S}.signing_key SET revoked_at = coalesce(revoked_at, %s),"
                " revocation_reason = coalesce(revocation_reason, %s)"
                " WHERE key_id = %s RETURNING *",
                (at, reason, key_id),
            ).fetchone()
            return self._key(row) if row else None

    def list_signing_keys(self) -> list[SigningKeyRecord]:
        rows = self._all(f"SELECT * FROM {S}.signing_key ORDER BY created_at")
        return [self._key(r) for r in rows]

    def add_external_artifact(self, artifact: ExternalArtifact) -> None:
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.external_artifact (id, organization_id, attestation_id, tool,"
                " tool_version, kind, storage_ref, sha256, created_at)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    artifact.id,
                    artifact.organization_id,
                    artifact.attestation_id,
                    artifact.tool,
                    artifact.tool_version,
                    artifact.kind,
                    artifact.storage_ref,
                    artifact.sha256,
                    artifact.created_at,
                ),
            )

    def list_external_artifacts(self, attestation_id: UUID) -> list[ExternalArtifact]:
        rows = self._all(
            f"SELECT * FROM {S}.external_artifact WHERE attestation_id = %s ORDER BY created_at",
            (attestation_id,),
        )
        return [ExternalArtifact.model_validate(r) for r in rows]

    def add_schedule(self, schedule: ReevaluationSchedule) -> None:
        with self._tx() as conn:
            conn.execute(
                f"INSERT INTO {S}.reevaluation_schedule (id, organization_id, registration_id,"
                " interval_hours, runs_per_test_case, budget_limit, next_run_at, enabled,"
                " created_by, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    schedule.id,
                    schedule.organization_id,
                    schedule.registration_id,
                    schedule.interval_hours,
                    schedule.runs_per_test_case,
                    schedule.budget_limit,
                    schedule.next_run_at,
                    schedule.enabled,
                    schedule.created_by,
                    schedule.created_at,
                ),
            )

    @staticmethod
    def _schedule(row: Row) -> ReevaluationSchedule:
        data = dict(row)
        data["budget_limit"] = str(data["budget_limit"])
        return ReevaluationSchedule.model_validate(data)

    def list_schedules(self, organization_id: UUID) -> list[ReevaluationSchedule]:
        rows = self._all(
            f"SELECT * FROM {S}.reevaluation_schedule WHERE organization_id = %s"
            " ORDER BY created_at",
            (organization_id,),
        )
        return [self._schedule(r) for r in rows]

    def due_schedules(self, now: datetime) -> list[ReevaluationSchedule]:
        rows = self._all(
            f"SELECT * FROM {S}.reevaluation_schedule WHERE enabled AND next_run_at <= %s"
            " ORDER BY next_run_at",
            (now,),
        )
        return [self._schedule(r) for r in rows]

    def update_schedule(self, schedule: ReevaluationSchedule) -> None:
        with self._tx() as conn:
            conn.execute(
                f"UPDATE {S}.reevaluation_schedule SET next_run_at = %s, enabled = %s,"
                " interval_hours = %s, runs_per_test_case = %s, budget_limit = %s WHERE id = %s",
                (
                    schedule.next_run_at,
                    schedule.enabled,
                    schedule.interval_hours,
                    schedule.runs_per_test_case,
                    schedule.budget_limit,
                    schedule.id,
                ),
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _next_status(job: Job, outcome: AttemptOutcome) -> tuple[JobStatus, bool]:
    if outcome is AttemptOutcome.SUCCEEDED:
        return JobStatus.SUCCEEDED, True
    if outcome is AttemptOutcome.CANCELLED or job.cancel_requested:
        return JobStatus.CANCELLED, True
    if job.attempts >= job.max_attempts:
        return JobStatus.FAILED, True
    return JobStatus.QUEUED, False
