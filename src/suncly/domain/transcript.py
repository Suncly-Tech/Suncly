"""What the Runner returns for one run: the redacted transcript and its measurements.

A transcript is evidence, not an entity. The evidence store keeps it in
transcript storage and ``run.transcript_ref`` points at it (schema §7).
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from suncly.domain.models import JsonObject

#: Cost of one attempt in the unit of ``budget_limit`` (OQ-D1: NEEDS DECISION). Every attempt
#: costs one unit, retried or not, so ``cost_total`` counts calls made to the agent.
COST_PER_ATTEMPT = Decimal(1)


class RunOutcome(StrEnum):
    """How the exchange with the agent ended, before any judging."""

    RESPONDED_TASK = "responded_task"
    """The agent answered with a Task that reached a terminal or interrupted state."""
    RESPONDED_MESSAGE = "responded_message"
    """The agent answered with a direct Message instead of a Task (A2A §3.1.1)."""
    UNREACHABLE = "unreachable"
    """No connection could be made; there is no response (FLOW.md: Agent unreachable)."""
    TIMEOUT = "timeout"
    """The agent accepted the request but did not finish within the timeout."""
    PROTOCOL_ERROR = "protocol_error"
    """The agent answered, but not with a usable A2A response (error or malformed)."""


class Exchange(BaseModel):
    """One HTTP request or response, after redaction."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    direction: str = Field(pattern="^(request|response)$")
    at: AwareDatetime
    method: str | None = None
    url: str
    http_status: int | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = None


class RedactionSummary(BaseModel):
    """How much the Runner removed before the transcript left it (DR-003)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    replacements: int = 0
    rules: list[str] = Field(default_factory=list)


class Transcript(BaseModel):
    """The complete, redacted record of one run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attestation_id: UUID
    test_case_id: UUID
    attempt: int = Field(ge=1)
    target_url: str
    protocol_binding: str
    protocol_version: str
    started_at: AwareDatetime
    finished_at: AwareDatetime
    latency_ms: int | None = Field(default=None, ge=0)
    cost: Decimal = Field(ge=0)
    outcome: RunOutcome
    task_id: str | None = None
    final_task_state: str | None = None
    final_response: JsonObject | None = None
    exchanges: list[Exchange] = Field(default_factory=list)
    failure: str | None = None
    redaction: RedactionSummary = Field(default_factory=RedactionSummary)

    @property
    def responded(self) -> bool:
        return self.outcome in (RunOutcome.RESPONDED_TASK, RunOutcome.RESPONDED_MESSAGE)
