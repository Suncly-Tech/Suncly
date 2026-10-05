"""Durable jobs: the Postgres-backed queue of SCHEMA.md §7, with leases and attempts.

A job is the durable intent to do something (run an attestation, re-evaluate
an agent, relay an outbox message). ``logical_id`` is the stable identity of
the work (for an attestation job it is the attestation id); every execution of
that work is a separate ``ExecutionAttempt``. The pair keeps "run once" and
"try again" apart (DR-001): retries never create a second attestation, and
evidence written under the attestation's run keys is reused, never duplicated.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

JsonObject = dict[str, Any]


class JobKind(StrEnum):
    ATTESTATION = "attestation"
    """Execute one attestation end to end; the payload names the attestation."""
    REEVALUATION = "reevaluation"
    """Scheduled re-evaluation: start a new attestation for a registration and compare."""
    OUTBOX_RELAY = "outbox_relay"
    """Deliver pending outbox messages (meter reports, notifications)."""


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    """Every allowed attempt failed, or the work itself reported a permanent failure."""
    CANCELLED = "cancelled"


#: Statuses in which nothing more will happen to the job.
FINAL_JOB_STATUSES = frozenset({JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED})


class Job(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    organization_id: UUID
    kind: JobKind
    logical_id: UUID
    """The stable identity of the work; for attestation jobs, the attestation id."""
    payload: JsonObject = Field(default_factory=dict)
    status: JobStatus
    created_at: AwareDatetime
    run_after: AwareDatetime
    """Not claimable before this time (backoff between retries)."""
    attempts: int = Field(default=0, ge=0)
    """Execution attempts started so far."""
    max_attempts: int = Field(default=3, ge=1, le=20)
    lease_owner: str | None = None
    lease_expires_at: AwareDatetime | None = None
    cancel_requested: bool = False
    progress: JsonObject = Field(default_factory=dict)
    """The latest persisted progress (planned runs, recorded runs, phase)."""
    last_error: str | None = None
    finished_at: AwareDatetime | None = None

    @property
    def is_final(self) -> bool:
        return self.status in FINAL_JOB_STATUSES


class AttemptOutcome(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    """The attempt reported an error; the job may be retried."""
    LOST = "lost"
    """The lease expired without a heartbeat: the worker died or hung."""
    CANCELLED = "cancelled"


class ExecutionAttempt(BaseModel):
    """One execution of a job by one worker, with its lease history."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    job_id: UUID
    number: int = Field(ge=1)
    worker_id: str = Field(min_length=1)
    started_at: AwareDatetime
    last_heartbeat_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    outcome: AttemptOutcome
    error: str | None = None


class OutboxMessage(BaseModel):
    """A message written in the same transaction as the state change it announces.

    A relay delivers it at least once; consumers deduplicate on ``id`` (or on
    the ``dedup_key`` when the destination offers one, as Stripe meter events do).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    organization_id: UUID
    topic: str = Field(min_length=1, max_length=120)
    dedup_key: str = Field(min_length=1, max_length=200)
    payload: JsonObject
    created_at: AwareDatetime
    delivered_at: AwareDatetime | None = None
    attempts: int = Field(default=0, ge=0)
    last_error: str | None = None


def backoff_seconds(attempt_number: int, base_s: float = 5.0, cap_s: float = 300.0) -> float:
    """Exponential backoff for retry ``attempt_number`` (1 = first retry), bounded by ``cap_s``."""
    return float(min(cap_s, base_s * (2 ** max(attempt_number - 1, 0))))
