"""The model port: structured completions for drafting and judging (DR-004).

One narrow interface serves both the model drafter (Contract builder) and
Layer 2 of the Judge. The caller sends a fixed system prompt, untrusted data
as the user message, and a JSON Schema; the adapter returns either a parsed
object that validated against the schema or an explicit failure. A failure
never becomes a pass anywhere.

The model never gets tools, and the adapters are wired without any customer
credential: a judge cannot call the agent.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

JsonObject = dict[str, Any]


class ModelConfig(BaseModel):
    """Pinned model configuration. Changing it is a deliberate configuration change."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    max_output_tokens: int = Field(default=4096, ge=256, le=128_000)
    effort: str | None = None
    timeout_s: float = Field(default=60.0, gt=0)
    temperature: float | None = None

    @property
    def identity(self) -> str:
        return f"{self.provider}:{self.model}"

    def parameters(self) -> JsonObject:
        return self.model_dump(mode="json", exclude={"provider", "model"}, exclude_none=True)


class ModelFailureKind(StrEnum):
    UNAVAILABLE = "unavailable"
    """The provider could not be reached or answered with an error."""
    TIMEOUT = "timeout"
    REFUSAL = "refusal"
    """The model declined to answer."""
    MALFORMED = "malformed"
    """The answer did not validate against the schema."""
    TRUNCATED = "truncated"
    """The answer hit the output limit."""
    MISCONFIGURED = "misconfigured"
    """No provider is configured, or the configuration is unusable."""


class ModelUsage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cache_read_tokens: int = Field(default=0, ge=0)
    provider_request_id: str | None = None


class StructuredRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    purpose: str = Field(pattern=r"^(draft|judge)$")
    system: str = Field(min_length=1)
    user: str = Field(min_length=1)
    schema_: JsonObject = Field(alias="schema")
    """The JSON Schema the answer must satisfy."""
    config: ModelConfig


class StructuredResponse(BaseModel):
    """Either ``parsed`` (validated) or ``failure``; never both, never neither."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    parsed: JsonObject | None = None
    raw_text: str | None = None
    failure: ModelFailureKind | None = None
    failure_detail: str = ""
    model: str = ""
    """The model identity the provider reports, for the evidence."""
    usage: ModelUsage = Field(default_factory=ModelUsage)
    latency_ms: int | None = None

    @property
    def ok(self) -> bool:
        return self.parsed is not None and self.failure is None


class StructuredModelClient(Protocol):
    """One provider adapter. Offline fakes implement it for CI."""

    name: str

    def complete(self, request: StructuredRequest) -> StructuredResponse: ...
