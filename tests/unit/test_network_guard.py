"""SSRF defences: URL policy, address classification, connection-time checks, bounds."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from suncly.adapters.httpx_card_fetcher import HttpxCardFetcher
from suncly.domain.errors import CardFetchError, TargetHostRefusedError
from suncly.domain.network import (
    NetworkPolicy,
    address_block_reason,
    check_addresses,
    check_url,
)
from suncly.domain.tenancy import DeploymentMode
from suncly.runner.http_transport import HttpxJsonRpcTransport, resolve_host

PUBLIC = NetworkPolicy.for_mode(DeploymentMode.PUBLIC)
LOCAL = NetworkPolicy.for_mode(DeploymentMode.LOCAL)
PRIVATE = NetworkPolicy.for_mode(DeploymentMode.PRIVATE_NETWORK)


@pytest.mark.parametrize(
    ("url", "ok_public", "ok_local"),
    [
        ("https://agent.example.com/rpc", True, True),
        ("https://agent.example.com:8443/rpc", True, True),
        ("https://agent.example.com:9999/rpc", False, True),
        ("http://agent.example.com/rpc", False, False),
        ("http://127.0.0.1:1/rpc", False, True),
        ("http://localhost:1/rpc", False, True),
        ("http://[::1]:1/rpc", False, True),
        ("https://localhost/rpc", False, True),
        ("https://metadata.google.internal/computeMetadata/v1/", False, False),
        ("https://169.254.169.254/latest/meta-data/", False, False),
        ("https://10.0.0.8/rpc", False, False),
        ("https://192.168.1.1/rpc", False, False),
        ("https://[fd00::1]/rpc", False, False),
        ("https://[::ffff:10.0.0.1]/rpc", False, False),
        ("https://user:pass@agent.example.com/rpc", False, False),
        ("ftp://agent.example.com/rpc", False, False),
        ("agent.example.com", False, False),
    ],
)
def test_url_policy_per_mode(url: str, ok_public: bool, ok_local: bool) -> None:
    for policy, ok in ((PUBLIC, ok_public), (LOCAL, ok_local)):
        if ok:
            check_url(url, policy)
        else:
            with pytest.raises(TargetHostRefusedError):
                check_url(url, policy)


def test_private_network_mode_is_a_separate_deployment_choice() -> None:
    check_url("https://10.0.0.8/rpc", PRIVATE)
    check_url("http://10.0.0.8:8080/rpc", PRIVATE)
    with pytest.raises(TargetHostRefusedError):
        check_url("https://169.254.169.254/latest/meta-data/", PRIVATE)
    with pytest.raises(TargetHostRefusedError):
        check_url("http://127.0.0.1/rpc", PUBLIC)


@pytest.mark.parametrize(
    ("address", "reason"),
    [
        ("93.184.216.34", None),
        ("2606:2800:220:1:248:1893:25c8:1946", None),
        ("127.0.0.1", "loopback"),
        ("::1", "loopback"),
        ("10.1.2.3", "private"),
        ("172.16.5.5", "private"),
        ("192.168.0.1", "private"),
        ("169.254.169.254", "link-local (cloud metadata range)"),
        ("fe80::1", "link-local (cloud metadata range)"),
        ("::ffff:127.0.0.1", "loopback"),
        ("::ffff:192.168.1.2", "private"),
        ("224.0.0.1", "multicast"),
        ("0.0.0.0", "reserved"),
        ("100.64.0.1", "in blocked range 100.64.0.0/10"),
        ("fd00:ec2::254", "private"),
        ("not-an-ip", "not an IP address"),
    ],
)
def test_address_classification(address: str, reason: str | None) -> None:
    assert address_block_reason(address) == reason


def test_every_resolved_address_must_be_allowed() -> None:
    check_addresses("agent.example.com", ["93.184.216.34"], PUBLIC)
    with pytest.raises(TargetHostRefusedError, match=r"rebinding|not a public endpoint"):
        check_addresses("agent.example.com", ["93.184.216.34", "10.0.0.1"], PUBLIC)
    with pytest.raises(TargetHostRefusedError, match="did not resolve"):
        check_addresses("agent.example.com", [], PUBLIC)
    check_addresses("sandbox.internal", ["10.0.0.1"], PRIVATE)
    check_addresses("localhost", ["127.0.0.1"], LOCAL)


class _Server:
    """A loopback HTTP server answering JSON-RPC and serving a card plus redirects."""

    def __init__(self) -> None:
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: Any) -> None:
                return None

            def _send(
                self, status: int, body: bytes, headers: dict[str, str] | None = None
            ) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                if self.path == "/card":
                    self._send(
                        200,
                        json.dumps(
                            {
                                "name": "x",
                                "supportedInterfaces": [
                                    {
                                        "url": server.url + "/rpc",
                                        "protocolBinding": "JSONRPC",
                                        "protocolVersion": "1.0",
                                    }
                                ],
                                "skills": [],
                            }
                        ).encode(),
                    )
                elif self.path == "/to-metadata":
                    self._send(302, b"", {"Location": "http://169.254.169.254/latest/meta-data/"})
                elif self.path == "/to-private":
                    self._send(302, b"", {"Location": "https://10.0.0.5/card"})
                elif self.path == "/big":
                    self._send(200, b"x" * 5000)
                elif self.path == "/state":
                    self._send(200, json.dumps({"orders": {"1": {"status": "cancelled"}}}).encode())
                else:
                    self._send(404, b"{}")

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                self.rfile.read(length)
                self._send(
                    200,
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": "1",
                            "result": {
                                "message": {
                                    "messageId": "m",
                                    "role": "ROLE_AGENT",
                                    "parts": [{"text": "hi"}],
                                }
                            },
                        }
                    ).encode(),
                )

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> _Server:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._server.shutdown()
        self._server.server_close()


def test_the_runner_transport_checks_resolved_addresses_at_connection_time() -> None:
    """A public-looking name that resolves to loopback (rebinding) is refused when connecting."""
    with _Server() as server:
        port = server.url.rsplit(":", 1)[1]
        local = HttpxJsonRpcTransport(server.url + "/rpc", "1.0", {}, policy=LOCAL)
        assert local.call("SendMessage", {}, "1", 5.0).http_status == 200
        local.close()

        def rebinding(host: str) -> list[str]:
            return ["127.0.0.1"] if host == "agent.example.com" else resolve_host(host)

        public = HttpxJsonRpcTransport(
            f"https://agent.example.com:{port}/rpc",
            "1.0",
            {},
            policy=NetworkPolicy.for_mode(DeploymentMode.PUBLIC, extra_ports=[int(port)]),
            resolver=rebinding,
        )
        response = public.call("SendMessage", {}, "1", 5.0)
        assert response.transport_error is not None
        assert (
            "loopback" in response.transport_error
            or "not a public endpoint" in response.transport_error
        )
        public.close()


def test_the_transport_bounds_response_sizes_and_only_gets_its_own_origin() -> None:
    with _Server() as server:
        transport = HttpxJsonRpcTransport(
            server.url + "/rpc", "1.0", {}, policy=LOCAL, max_response_bytes=1000
        )
        big = transport.get_json(server.url + "/big", 5.0)
        assert big.transport_error is not None and "larger than" in big.transport_error
        state = transport.get_json(server.url + "/state", 5.0)
        assert (
            state.http_status == 200 and state.response_body["orders"]["1"]["status"] == "cancelled"
        )
        elsewhere = transport.get_json("http://127.0.0.1:1/state", 5.0)
        assert (
            elsewhere.transport_error is not None
            and "other than the target" in elsewhere.transport_error
        )
        transport.close()


def test_the_card_fetcher_refuses_redirects_to_metadata_and_private_hosts() -> None:
    with _Server() as server:
        fetcher = HttpxCardFetcher(5.0, 100_000, policy=LOCAL)
        assert "supportedInterfaces" in fetcher.fetch(server.url + "/card").raw_json
        with pytest.raises(CardFetchError, match="not https or not allowed"):
            fetcher.fetch(server.url + "/to-metadata")
        with pytest.raises(CardFetchError, match="not https or not allowed"):
            fetcher.fetch(server.url + "/to-private")
        public = HttpxCardFetcher(5.0, 100_000, policy=PUBLIC)
        with pytest.raises(CardFetchError, match="must use https"):
            public.fetch(server.url + "/card")


def test_resolve_host_passes_literals_through() -> None:
    assert resolve_host("127.0.0.1") == ["127.0.0.1"]
    assert resolve_host("[::1]") == ["::1"]
    assert resolve_host("localhost")
    with pytest.raises(TargetHostRefusedError, match="could not be resolved"):
        resolve_host("no-such-host.invalid")
