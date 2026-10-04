"""Executing one run in the isolated Runner (schema §2: Runner).

The Orchestrator hands over exactly what one run needs and gets back the
redacted transcript. The production adapter starts the Runner as a separate
process; tests use an in-process fake.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from suncly.domain.models import JsonObject
from suncly.domain.transcript import Transcript


class RunJob(BaseModel):
    """What one run needs, and nothing else. Credentials are not part of it (DR-003)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attestation_id: UUID
    test_case_id: UUID
    attempt: int = Field(ge=1)
    message_id: str
    input: JsonObject
    target_url: str
    protocol_binding: str
    protocol_version: str
    timeout_s: float = Field(gt=0)
    poll_interval_s: float = Field(gt=0)
    sandbox_declared: bool
    """DR-006: the Runner refuses to run unless the caller declared the target a sandbox."""


class RunResult(BaseModel):
    """The Runner's answer: a transcript, or the reason there is none."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    transcript: Transcript | None = None
    withheld: bool = False
    """Redaction failed: the transcript is withheld and the run is not recorded (OQ-A11)."""
    crashed: bool = False
    """True when the Runner process died or produced no result; the Orchestrator may retry."""
    error: str | None = None


class RunExecutor(Protocol):
    def execute(self, job: RunJob) -> RunResult: ...
