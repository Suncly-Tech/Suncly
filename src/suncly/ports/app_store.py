"""The application store port: tenancy, jobs, outbox, ledger, billing, keys.

The attestation core keeps its seven entities behind ``ports/store.py``. The
hosted application layer (SCHEMA.md §12) keeps everything else behind this
port. Two implementations exist, in memory and on Postgres, and both pass
``tests/stores/test_app_store_contract.py``. Every method that must be atomic
under concurrency (claiming a job, reserving money, recording a provider
event) is atomic in both.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from suncly.domain.billing import MeterReport, ProviderEvent, Subscription
from suncly.domain.jobs import (
    AttemptOutcome,
    ExecutionAttempt,
    Job,
    JobKind,
    JobStatus,
    OutboxMessage,
)
from suncly.domain.ledger import Reservation, SpendingLimit, UsageEvent
from suncly.domain.models import JsonObject
from suncly.domain.policy import PolicyRecord
from suncly.domain.tenancy import AgentRegistration, Membership, Organization


class AttestationMeta(BaseModel):
    """The application layer's record about one core attestation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attestation_id: UUID
    organization_id: UUID
    registration_id: UUID
    created_by: str
    runs_planned: int = Field(ge=0)
    runs_per_test_case: int = Field(ge=1)
    suite_version: str
    contract_content_hash: str
    judge_version: str
    rubric_versions: dict[str, str] = Field(default_factory=dict)
    policy_version: str | None = None
    policy_content_hash: str | None = None
    environment: JsonObject = Field(default_factory=dict)
    deployment_identity: JsonObject | None = None
    issued_at: AwareDatetime | None = None
    expires_at: AwareDatetime | None = None
    payload_version: int | None = None
    decided_by_reviewer: str | None = None


class DecisionNote(BaseModel):
    """The rationale behind a human decision record. Append-only, one per decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: UUID
    organization_id: UUID
    attestation_id: UUID
    reviewer_subject: str
    rationale: str = Field(min_length=1)
    created_at: AwareDatetime


class SigningKeyRecord(BaseModel):
    """A key the deployment trusts for verification, with its revocation state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key_id: str
    issuer: str
    public_key: bytes
    created_at: AwareDatetime
    revoked_at: AwareDatetime | None = None
    revocation_reason: str | None = None


class ExternalArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    organization_id: UUID
    attestation_id: UUID
    tool: str
    tool_version: str
    kind: str
    storage_ref: str
    sha256: str
    created_at: AwareDatetime


class ReevaluationSchedule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    organization_id: UUID
    registration_id: UUID
    interval_hours: int = Field(ge=1)
    runs_per_test_case: int = Field(ge=1)
    budget_limit: str
    next_run_at: AwareDatetime
    enabled: bool = True
    created_by: str
    created_at: AwareDatetime


class LedgerTotals(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    settled_minor: int = 0
    reserved_minor: int = 0
    allowance_used_minor: int = 0
    unknown_held_minor: int = 0
    pending_report_minor: int = 0


class ApplicationStore(Protocol):
    # -- organizations and memberships ------------------------------------------
    def add_organization(self, organization: Organization) -> None: ...

    def get_organization(self, organization_id: UUID) -> Organization | None: ...

    def get_organization_by_slug(self, slug: str) -> Organization | None: ...

    def add_membership(self, membership: Membership) -> None: ...

    def get_membership(self, organization_id: UUID, subject: str) -> Membership | None: ...

    def list_memberships(self, organization_id: UUID) -> list[Membership]: ...

    def list_organizations_for_subject(self, subject: str) -> list[Organization]: ...

    # -- agent registrations --------------------------------------------------
    def add_registration(self, registration: AgentRegistration) -> None: ...

    def get_registration(
        self, organization_id: UUID, registration_id: UUID
    ) -> AgentRegistration | None: ...

    def get_registration_by_agent(self, agent_id: UUID) -> AgentRegistration | None: ...

    def list_registrations(self, organization_id: UUID) -> list[AgentRegistration]: ...

    def archive_registration(
        self, organization_id: UUID, registration_id: UUID, at: datetime
    ) -> AgentRegistration | None: ...

    # -- attestation meta -----------------------------------------------------
    def add_attestation_meta(self, meta: AttestationMeta) -> None: ...

    def get_attestation_meta(self, attestation_id: UUID) -> AttestationMeta | None: ...

    def update_attestation_meta(self, meta: AttestationMeta) -> None: ...

    def list_attestation_meta(
        self, organization_id: UUID, registration_id: UUID | None = None
    ) -> list[AttestationMeta]: ...

    # -- policies and decision notes ------------------------------------------
    def add_policy(self, record: PolicyRecord) -> None: ...

    def list_policies(self, organization_id: UUID) -> list[PolicyRecord]: ...

    def get_policy(self, organization_id: UUID, policy_id: UUID) -> PolicyRecord | None: ...

    def add_decision_note(self, note: DecisionNote) -> None: ...

    def list_decision_notes(self, attestation_id: UUID) -> list[DecisionNote]: ...

    # -- jobs -----------------------------------------------------------------
    def enqueue_job(self, job: Job, outbox: list[OutboxMessage] = ...) -> None:
        """Insert the job (and outbox messages) atomically; a duplicate logical id is refused."""
        ...

    def get_job(self, job_id: UUID) -> Job | None: ...

    def find_job(self, kind: JobKind, logical_id: UUID) -> Job | None: ...

    def list_jobs(self, organization_id: UUID, status: JobStatus | None = None) -> list[Job]: ...

    def claim_job(
        self, worker_id: str, now: datetime, lease_seconds: float, kinds: list[JobKind]
    ) -> tuple[Job, ExecutionAttempt] | None:
        """Atomically claim one queued job whose tenant is under its concurrency limit."""
        ...

    def heartbeat(
        self, job_id: UUID, attempt_id: UUID, now: datetime, lease_seconds: float
    ) -> Job | None:
        """Extend the lease. Returns the job, or ``None`` when the lease was lost."""
        ...

    def update_progress(self, job_id: UUID, progress: JsonObject) -> None: ...

    def finish_attempt(
        self,
        job_id: UUID,
        attempt_id: UUID,
        outcome: AttemptOutcome,
        now: datetime,
        error: str | None,
        run_after: datetime | None,
    ) -> Job:
        """Close the attempt and set the job's next status (retry, failed, succeeded)."""
        ...

    def request_cancel(self, job_id: UUID, now: datetime) -> Job | None: ...

    def recover_expired_leases(self, now: datetime) -> list[Job]:
        """Mark attempts whose lease expired as lost and requeue or fail their jobs."""
        ...

    def list_attempts(self, job_id: UUID) -> list[ExecutionAttempt]: ...

    # -- outbox ---------------------------------------------------------------
    def add_outbox(self, message: OutboxMessage) -> bool:
        """Insert unless the dedup key exists. Returns whether it was inserted."""
        ...

    def claim_outbox(self, limit: int, now: datetime) -> list[OutboxMessage]: ...

    def mark_outbox(self, message_id: UUID, now: datetime, error: str | None) -> None: ...

    # -- ledger ---------------------------------------------------------------
    def add_usage_event(self, event: UsageEvent) -> None: ...

    def list_usage_events(
        self, organization_id: UUID, since: datetime | None = None
    ) -> list[UsageEvent]: ...

    def try_reserve(
        self, reservation: Reservation, limit_minor: int | None, since: datetime | None
    ) -> bool:
        """Insert the reservation unless settled + held usage since ``since`` would exceed
        ``limit_minor``. Atomic per organization."""
        ...

    def get_reservation(self, reservation_id: UUID) -> Reservation | None: ...

    def close_reservation(
        self, reservation_id: UUID, settled_minor: int, now: datetime, released: bool
    ) -> Reservation: ...

    def list_reservations(self, organization_id: UUID) -> list[Reservation]: ...

    def ledger_totals(self, organization_id: UUID, since: datetime | None) -> LedgerTotals: ...

    def add_spending_limit(self, limit: SpendingLimit) -> None: ...

    def get_spending_limit(self, organization_id: UUID) -> SpendingLimit | None: ...

    def mark_usage_reported(self, report: MeterReport) -> bool:
        """Record the meter report unless one exists for the event. Returns whether recorded."""
        ...

    def list_unreported_usage(self, limit: int) -> list[UsageEvent]: ...

    # -- billing --------------------------------------------------------------
    def upsert_subscription(self, subscription: Subscription) -> None: ...

    def get_subscription(self, organization_id: UUID) -> Subscription | None: ...

    def find_subscription_by_customer(
        self, provider: str, customer_id: str
    ) -> Subscription | None: ...

    def record_provider_event(self, event: ProviderEvent) -> bool:
        """Insert unless (provider, event_id) exists. Returns whether it was new."""
        ...

    def mark_provider_event(self, provider: str, event_id: str, result: str) -> None: ...

    # -- signing keys, artifacts, schedules ------------------------------------
    def add_signing_key(self, record: SigningKeyRecord) -> None: ...

    def get_signing_key(self, key_id: str) -> SigningKeyRecord | None: ...

    def revoke_signing_key(
        self, key_id: str, at: datetime, reason: str
    ) -> SigningKeyRecord | None: ...

    def list_signing_keys(self) -> list[SigningKeyRecord]: ...

    def add_external_artifact(self, artifact: ExternalArtifact) -> None: ...

    def list_external_artifacts(self, attestation_id: UUID) -> list[ExternalArtifact]: ...

    def add_schedule(self, schedule: ReevaluationSchedule) -> None: ...

    def list_schedules(self, organization_id: UUID) -> list[ReevaluationSchedule]: ...

    def due_schedules(self, now: datetime) -> list[ReevaluationSchedule]: ...

    def update_schedule(self, schedule: ReevaluationSchedule) -> None: ...

    def close(self) -> None: ...
