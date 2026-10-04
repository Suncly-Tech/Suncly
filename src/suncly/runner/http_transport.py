"""The Runner's HTTP layer: JSON-RPC 2.0 over HTTP(S) to one host only (A2A §9).

Network access is limited to the target (schema §2). The restriction is
enforced in one place: a request hook that refuses any request whose scheme,
host or port differs from the target's. Redirects are not followed, so a
redirect can never lead elsewhere. HTTPS is required except for loopback
addresses, which is where local sandboxes run.
"""

from __future__ import annotations

import ipaddress
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from suncly.domain.a2a import VERSION_HEADER
from suncly.domain.errors import TargetHostRefusedError
from suncly.ports.a2a import RpcResponse

LOOPBACK_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def require_https_or_loopback(url: str, what: str) -> None:
    """Refuse plain http anywhere but loopback (A2A §7.1 requires TLS in production)."""
    parts = urlsplit(url)
    if parts.scheme == "https":
        return
    if parts.scheme == "http" and is_loopback_host(parts.hostname):
        return
    raise TargetHostRefusedError(
        f"The {what} must use https.",
        f"{url} uses {parts.scheme or 'no scheme'}; plain http is allowed only for loopback "
        "addresses such as 127.0.0.1.",
        "Use an https URL, or run the sandbox on this machine.",
    )


def _origin(url: httpx.URL) -> tuple[str, str, int | None]:
    return url.scheme, (url.host or "").lower(), url.port


class HttpxJsonRpcTransport:
    """One target, one client, every request checked against the target."""

    def __init__(
        self,
        target_url: str,
        protocol_version: str,
        extra_headers: Mapping[str, str],
        connect_timeout_s: float = 10.0,
    ) -> None:
        require_https_or_loopback(target_url, "agent endpoint")
        self._target_url = target_url
        self._target = _origin(httpx.URL(target_url))
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            VERSION_HEADER: protocol_version,
            **extra_headers,
        }
        self._client = httpx.Client(
            follow_redirects=False,
            timeout=httpx.Timeout(connect_timeout_s),
            event_hooks={"request": [self._refuse_other_hosts]},
        )

    @property
    def target_url(self) -> str:
        return self._target_url

    def _refuse_other_hosts(self, request: httpx.Request) -> None:
        if _origin(request.url) != self._target:
            raise TargetHostRefusedError(
                "The Runner refused a request to a host other than the target.",
                f"The request was for {request.url.scheme}://{request.url.host}, the target is "
                f"{self._target[0]}://{self._target[1]}.",
            )

    def call(
        self, method: str, params: dict[str, Any], request_id: str, timeout_s: float
    ) -> RpcResponse:
        body = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        sent_at = datetime.now(UTC)
        try:
            response = self._client.post(
                self._target_url,
                content=json.dumps(body).encode("utf-8"),
                headers=self._headers,
                timeout=httpx.Timeout(timeout_s, connect=min(timeout_s, 10.0)),
            )
        except httpx.ConnectTimeout as exc:
            return RpcResponse(
                sent_at=sent_at,
                received_at=datetime.now(UTC),
                request_headers=dict(self._headers),
                request_body=body,
                http_status=None,
                response_body=None,
                transport_error=f"unreachable: {exc.__class__.__name__} (no connection)",
            )
        except httpx.TimeoutException as exc:
            return RpcResponse(
                sent_at=sent_at,
                received_at=datetime.now(UTC),
                request_headers=dict(self._headers),
                request_body=body,
                http_status=None,
                response_body=None,
                transport_error=f"timeout: {exc.__class__.__name__}",
                timed_out=True,
            )
        except (httpx.HTTPError, OSError) as exc:
            return RpcResponse(
                sent_at=sent_at,
                received_at=datetime.now(UTC),
                request_headers=dict(self._headers),
                request_body=body,
                http_status=None,
                response_body=None,
                transport_error=f"{exc.__class__.__name__}: {exc}",
            )
        received_at = datetime.now(UTC)
        response_body: Any
        try:
            response_body = response.json()
        except ValueError:
            response_body = response.text
        return RpcResponse(
            sent_at=sent_at,
            received_at=received_at,
            request_headers=dict(self._headers),
            request_body=body,
            http_status=response.status_code,
            response_headers=dict(response.headers),
            response_body=response_body,
        )

    def close(self) -> None:
        self._client.close()
