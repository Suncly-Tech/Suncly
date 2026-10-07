"""Asking the pinned judge model one question (schema §2, Layer 2; DR-004).

The core builds the prompt from the rubric and the criterion, hands it to the
``ModelJudge`` port and interprets the raw answer itself. The production
adapter starts the judge subprocess, which is the only place that holds the
customer's model key (OQ-A1, decided 2026-10-07); tests use an in-process
fake. The port carries no key and no endpoint.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class ModelRequest(BaseModel):
    """One question for the pinned model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model: str = Field(min_length=1)
    """The pinned model id from the configuration (DR-004)."""
    prompt: str = Field(min_length=1)
    timeout_s: float = Field(gt=0)


class ModelResponse(BaseModel):
    """The raw answer, or the reason there is none. Never carries the key."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model: str | None = None
    """The model id the endpoint reported as having answered; checked against the pin."""
    text: str | None = None
    """The raw answer text, interpreted by the core. ``None`` when there is no answer."""
    error: str | None = None
    timed_out: bool = False


class ModelJudge(Protocol):
    def ask(self, request: ModelRequest) -> ModelResponse: ...
