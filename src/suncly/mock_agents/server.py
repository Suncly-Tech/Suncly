"""A small local HTTP server speaking the A2A JSON-RPC binding (A2A §9).

Routes: ``GET /.well-known/agent-card.json`` (A2A §8.2) and ``POST /rpc``.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from suncly.mock_agents.behaviours import Behaviour, CallContext, RpcError

CARD_PATH = "/.well-known/agent-card.json"
RPC_PATH = "/rpc"


class MockAgentServer:
    def __init__(self, behaviour: Behaviour, host: str = "127.0.0.1", port: int = 0) -> None:
        self.behaviour = behaviour
        self._calls = 0
        self._card_fetches = 0
        self._lock = threading.Lock()
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args: Any) -> None:
                return None

            def _send(self, status: int, body: dict[str, Any]) -> None:
                data = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                if self.path != CARD_PATH:
                    self._send(404, {"error": "not found"})
                    return
                with server._lock:
                    server._card_fetches += 1
                    fetches = server._card_fetches
                context = CallContext(
                    call_number=0, headers=dict(self.headers.items()), card_fetches=fetches
                )
                self._send(200, server.behaviour.card(server.base_url, context))

            def do_POST(self) -> None:
                if self.path != RPC_PATH:
                    self._send(404, {"error": "not found"})
                    return
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                try:
                    request = json.loads(raw)
                except ValueError:
                    self._send(
                        200,
                        {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {"code": -32700, "message": "Invalid JSON payload"},
                        },
                    )
                    return
                request_id = request.get("id") if isinstance(request, dict) else None
                method = request.get("method") if isinstance(request, dict) else None
                params = request.get("params") if isinstance(request, dict) else None
                with server._lock:
                    server._calls += 1
                    call_number = server._calls
                    fetches = server._card_fetches
                headers = {k.lower(): v for k, v in self.headers.items()}
                context = CallContext(
                    call_number=call_number, headers=headers, card_fetches=fetches
                )
                try:
                    if not isinstance(method, str) or not isinstance(params, dict):
                        raise RpcError(-32600, "Request payload validation error")
                    result = server.behaviour.handle(method, params, context)
                except RpcError as error:
                    self._send(
                        200,
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": error.code, "message": error.message},
                        },
                    )
                    return
                self._send(200, {"jsonrpc": "2.0", "id": request_id, "result": result})

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever, name=f"mock-{behaviour.name}", daemon=True
        )

    @property
    def base_url(self) -> str:
        address = self._server.server_address
        host = address[0] if isinstance(address[0], str) else address[0].decode()
        return f"http://{host}:{address[1]}"

    @property
    def card_url(self) -> str:
        return self.base_url + CARD_PATH

    @property
    def calls(self) -> int:
        with self._lock:
            return self._calls

    def start(self) -> MockAgentServer:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self.behaviour.close()

    def __enter__(self) -> MockAgentServer:
        return self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
