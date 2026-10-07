"""What the judge subprocess receives on stdin: one question for one endpoint. No key."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class JudgeJob(BaseModel):
    """One prompt for the pinned model at the configured endpoint (DR-004)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    endpoint: str = Field(min_length=1)
    """The configured model endpoint; the only host the subprocess may talk to."""
    model: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    timeout_s: float = Field(gt=0)
