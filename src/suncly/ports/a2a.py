"""The transport the Runner's A2A client speaks through.

The protocol logic (which method to call, how to follow a task) lives in
``suncly.runner.protocol`` and is pure. The transport does the HTTP, enforces
that only the target host is ever contacted (schema §2), and reports each
exchange so the Runner can record every message it receives.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class RpcResponse(BaseModel):
    """What came back for one JSON-RPC call, before interpretation."""

    model_config = ConfigDict(frozen=True)

    sent_at: AwareDatetime
    received_at: AwareDatetime
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: Any
    http_status: int | None
    response_headers: dict[str, str] = Field(default_factory=dict)
    response_body: Any
    """Parsed JSON when the body was JSON, otherwise the text."""
    transport_error: str | None = None
    """Set when no HTTP response arrived (connection refused, timeout, TLS failure)."""
    timed_out: bool = False


class A2ATransport(Protocol):
    """Performs one JSON-RPC 2.0 call over HTTP(S) to the target (A2A §9)."""

    @property
    def target_url(self) -> str: ...

    def call(
        self, method: str, params: dict[str, Any], request_id: str, timeout_s: float
    ) -> RpcResponse: ...

    def get_json(self, url: str, timeout_s: float) -> RpcResponse:
        """``GET url`` on the target's origin, for independent sandbox-state verification."""
        ...
