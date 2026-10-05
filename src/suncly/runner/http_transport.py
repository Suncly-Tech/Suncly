"""The Runner's HTTP layer: JSON-RPC 2.0 over HTTP(S) to one host only (A2A §9).

Network access is limited to the target (schema §2), in three layers:

1. ``check_url`` refuses schemes, ports and literal hosts the deployment's
   ``NetworkPolicy`` forbids before any request is built;
2. a request hook refuses any request whose scheme, host or port differs
   from the target's, so a redirect or an absolute URL can never lead
   elsewhere (redirects are not followed at all);
3. ``GuardedBackend`` resolves the host itself, checks **every** address it
   resolved to against the policy at connection time, and connects to one of
   the checked addresses. A name that resolves to a private address later
   (DNS rebinding) is refused when the socket is opened. TLS still validates
   the certificate against the original hostname.

Response bodies are bounded, every request has a deadline, and plain http is
allowed only where the policy allows it (loopback in local mode).

This is application-level filtering, not network isolation; the hosted
deployment adds egress controls outside the process (deploy/README.md).
"""

from __future__ import annotations

import json
import socket
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

import httpcore
import httpx

from suncly.domain.a2a import VERSION_HEADER
from suncly.domain.errors import TargetHostRefusedError
from suncly.domain.network import NetworkPolicy, check_addresses, check_url, is_loopback_host

__all__ = [
    "GuardedBackend",
    "GuardedTransport",
    "HttpxJsonRpcTransport",
    "is_loopback_host",
    "require_https_or_loopback",
    "resolve_host",
]
from suncly.domain.tenancy import DeploymentMode
from suncly.ports.a2a import RpcResponse

Resolver = Callable[[str], list[str]]

#: Bytes of a response body the Runner reads at most.
DEFAULT_MAX_RESPONSE_BYTES = 4_000_000


def resolve_host(host: str) -> list[str]:
    """Every address ``host`` resolves to, IPv4 and IPv6, as strings."""
    literal = host.strip("[]")
    try:
        socket.inet_pton(socket.AF_INET, literal)
        return [literal]
    except OSError:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, literal)
        return [literal]
    except OSError:
        pass
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise TargetHostRefusedError(
            "The target host could not be resolved.", f"{host}: {exc}"
        ) from exc
    addresses: list[str] = []
    for info in infos:
        address = str(info[4][0])
        if address not in addresses:
            addresses.append(address)
    return addresses


class GuardedBackend(httpcore.SyncBackend):
    """A network backend that validates every resolved address before connecting."""

    def __init__(self, policy: NetworkPolicy, resolver: Resolver = resolve_host) -> None:
        super().__init__()
        self._policy = policy
        self._resolver = resolver

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.NetworkStream:
        addresses = self._resolver(host)
        check_addresses(host, addresses, self._policy)
        last_error: Exception | None = None
        for address in addresses:
            try:
                return super().connect_tcp(address, port, timeout, local_address, socket_options)
            except (httpcore.ConnectError, httpcore.ConnectTimeout, OSError) as exc:
                last_error = exc
        raise httpcore.ConnectError(
            f"no checked address of {host} accepted the connection: {last_error}"
        )


class GuardedTransport(httpx.HTTPTransport):
    """``httpx.HTTPTransport`` whose connection pool uses ``GuardedBackend``."""

    def __init__(
        self, policy: NetworkPolicy, resolver: Resolver = resolve_host, verify: bool = True
    ) -> None:
        super().__init__(verify=verify, retries=0)
        ssl_context = httpx.create_ssl_context(verify=verify)
        self._pool = httpcore.ConnectionPool(
            ssl_context=ssl_context,
            max_connections=4,
            max_keepalive_connections=2,
            keepalive_expiry=5.0,
            http1=True,
            http2=False,
            retries=0,
            network_backend=GuardedBackend(policy, resolver),
        )


def default_policy() -> NetworkPolicy:
    """Local-mode policy for the CLI and tests; hosted processes pass theirs explicitly."""
    return NetworkPolicy.for_mode(DeploymentMode.LOCAL)


def require_https_or_loopback(url: str, what: str) -> None:
    """Refuse plain http anywhere but loopback (A2A §7.1 requires TLS in production).

    Kept for the local CLI path; hosted modes use ``check_url`` with their policy.
    """
    check_url(url, default_policy(), what)


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
        policy: NetworkPolicy | None = None,
        resolver: Resolver = resolve_host,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        self._policy = policy or default_policy()
        check_url(target_url, self._policy, "agent endpoint")
        self._target_url = target_url
        self._target = _origin(httpx.URL(target_url))
        self._max_bytes = max_response_bytes
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            VERSION_HEADER: protocol_version,
            **extra_headers,
        }
        verify = not (self._policy.allows_loopback and is_loopback_host(httpx.URL(target_url).host))
        self._client = httpx.Client(
            follow_redirects=False,
            timeout=httpx.Timeout(connect_timeout_s),
            event_hooks={"request": [self._refuse_other_hosts]},
            transport=GuardedTransport(self._policy, resolver, verify=verify),
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

    def _send(
        self, method: str, url: str, body: Any, timeout_s: float, headers: Mapping[str, str]
    ) -> RpcResponse:
        sent_at = datetime.now(UTC)
        request_headers = dict(headers)
        try:
            with self._client.stream(
                method,
                url,
                content=json.dumps(body).encode("utf-8") if body is not None else None,
                headers=headers,
                timeout=httpx.Timeout(timeout_s, connect=min(timeout_s, 10.0)),
            ) as response:
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > self._max_bytes:
                        return RpcResponse(
                            sent_at=sent_at,
                            received_at=datetime.now(UTC),
                            request_headers=request_headers,
                            request_body=body,
                            http_status=response.status_code,
                            response_headers=dict(response.headers),
                            response_body=None,
                            transport_error=f"response larger than {self._max_bytes} bytes",
                        )
                status = response.status_code
                response_headers = dict(response.headers)
        except httpx.ConnectTimeout as exc:
            return self._failure(
                sent_at,
                request_headers,
                body,
                f"unreachable: {exc.__class__.__name__} (no connection)",
            )
        except httpx.TimeoutException as exc:
            return self._failure(
                sent_at, request_headers, body, f"timeout: {exc.__class__.__name__}", timed_out=True
            )
        except TargetHostRefusedError as exc:
            return self._failure(
                sent_at, request_headers, body, f"refused: {exc.what} {exc.why}".strip()
            )
        except (httpx.HTTPError, OSError) as exc:
            return self._failure(sent_at, request_headers, body, f"{exc.__class__.__name__}: {exc}")
        received_at = datetime.now(UTC)
        response_body: Any
        try:
            response_body = json.loads(bytes(raw).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            response_body = bytes(raw).decode("utf-8", errors="replace")
        return RpcResponse(
            sent_at=sent_at,
            received_at=received_at,
            request_headers=request_headers,
            request_body=body,
            http_status=status,
            response_headers=response_headers,
            response_body=response_body,
        )

    @staticmethod
    def _failure(
        sent_at: datetime,
        headers: dict[str, str],
        body: Any,
        error: str,
        timed_out: bool = False,
    ) -> RpcResponse:
        return RpcResponse(
            sent_at=sent_at,
            received_at=datetime.now(UTC),
            request_headers=headers,
            request_body=body,
            http_status=None,
            response_body=None,
            transport_error=error,
            timed_out=timed_out,
        )

    def call(
        self, method: str, params: dict[str, Any], request_id: str, timeout_s: float
    ) -> RpcResponse:
        body = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        return self._send("POST", self._target_url, body, timeout_s, self._headers)

    def get_json(self, url: str, timeout_s: float) -> RpcResponse:
        """A plain GET on the target's origin (sandbox-state verification). Same guards."""
        try:
            check_url(url, self._policy, "sandbox verification URL")
        except TargetHostRefusedError as exc:
            return self._failure(datetime.now(UTC), {}, None, f"refused: {exc.what} {exc.why}")
        headers = {k: v for k, v in self._headers.items() if k.lower() != "content-type"}
        return self._send("GET", url, None, timeout_s, headers)

    def close(self) -> None:
        self._client.close()
