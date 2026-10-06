"""The Runner: protocol logic, redaction, credentials, host restriction and the process entry."""

from __future__ import annotations

import io
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import pytest

from suncly.domain import a2a
from suncly.domain.errors import TargetHostRefusedError
from suncly.domain.transcript import RunOutcome, Transcript
from suncly.mock_agents import behaviours
from suncly.mock_agents.server import MockAgentServer
from suncly.ports.a2a import RpcResponse
from suncly.ports.run_executor import RunJob, RunResult
from suncly.runner import process
from suncly.runner.credentials import CREDENTIAL_ENV_VAR, Credentials, read_credentials
from suncly.runner.http_transport import (
    HttpxJsonRpcTransport,
    is_loopback_host,
    require_https_or_loopback,
)
from suncly.runner.protocol import execute_run
from suncly.runner.redaction import REDACTED, Redactor, redact_transcript
from tests.fakes import (
    FakeClock,
    ScriptedTransport,
    make_transcript,
    rpc_error,
    rpc_http,
    rpc_ok,
    rpc_transport_failure,
    task_response,
)

TARGET = "https://agent.example.com/rpc"


def job(**overrides: object) -> RunJob:
    data: dict[str, object] = {
        "attestation_id": UUID(int=1),
        "test_case_id": UUID(int=2),
        "attempt": 1,
        "message_id": "msg-1",
        "input": {"text": "hello"},
        "target_url": TARGET,
        "protocol_binding": "JSONRPC",
        "protocol_version": "1.0",
        "timeout_s": 5.0,
        "poll_interval_s": 0.01,
        "sandbox_declared": True,
    }
    data.update(overrides)
    return RunJob.model_validate(data)


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


def run(transport: ScriptedTransport, j: RunJob | None = None) -> Transcript:
    clock = Clock()
    return execute_run(j or job(), transport, FakeClock(), clock.sleep, clock.monotonic)


# -- protocol -----------------------------------------------------------------------


def test_send_message_builds_a_1_0_message_and_records_both_exchanges() -> None:
    transport = ScriptedTransport(TARGET, [rpc_ok({"task": task_response()})])
    transcript = run(transport)
    method, params = transport.calls[0]
    assert method == a2a.METHOD_SEND_MESSAGE
    assert params == {
        "message": {"messageId": "msg-1", "role": "ROLE_USER", "parts": [{"text": "hello"}]}
    }
    assert transcript.outcome is RunOutcome.RESPONDED_TASK
    assert transcript.final_task_state == "TASK_STATE_COMPLETED"
    assert transcript.task_id == "task-1" and transcript.latency_ms is not None
    assert [e.direction for e in transcript.exchanges] == ["request", "response"]


def test_a_non_terminal_task_is_polled_with_get_task_until_final() -> None:
    working = task_response(state="TASK_STATE_WORKING")
    transport = ScriptedTransport(
        TARGET,
        [
            rpc_ok({"task": task_response(state="TASK_STATE_SUBMITTED")}),
            rpc_ok(working),
            rpc_ok(task_response()),
        ],
    )
    transcript = run(transport)
    assert [m for m, _ in transport.calls] == ["SendMessage", "GetTask", "GetTask"]
    assert transport.calls[1][1] == {"id": "task-1"}
    assert (
        transcript.outcome is RunOutcome.RESPONDED_TASK
        and transcript.final_task_state == "TASK_STATE_COMPLETED"
    )
    assert len(transcript.exchanges) == 6


def test_the_tenant_of_the_selected_interface_is_sent_in_every_request() -> None:
    """A2A v1.0.1 §8.3.2 rule 4: set ``tenant`` to the interface's value in every request.

    Found while attesting reference agents (docs/REAL_AGENT_REPORT.md): the Runner
    omitted the field even when the selected interface declared one.
    """
    transport = ScriptedTransport(
        TARGET,
        [rpc_ok({"task": task_response(state="TASK_STATE_SUBMITTED")}), rpc_ok(task_response())],
    )
    run(transport, job(tenant="acme"))
    assert [m for m, _ in transport.calls] == ["SendMessage", "GetTask"]
    assert transport.calls[0][1]["tenant"] == "acme"
    assert transport.calls[1][1] == {"tenant": "acme", "id": "task-1"}
    # Without a declared tenant the field is omitted, as the same rule requires.
    transport = ScriptedTransport(
        TARGET,
        [rpc_ok({"task": task_response(state="TASK_STATE_SUBMITTED")}), rpc_ok(task_response())],
    )
    run(transport)
    assert "tenant" not in transport.calls[0][1]
    assert transport.calls[1][1] == {"id": "task-1"}


def test_interrupted_states_stop_the_runner_without_answering() -> None:
    transport = ScriptedTransport(
        TARGET, [rpc_ok({"task": task_response(state="TASK_STATE_INPUT_REQUIRED")})]
    )
    transcript = run(transport)
    assert transcript.outcome is RunOutcome.RESPONDED_TASK
    assert transcript.final_task_state == "TASK_STATE_INPUT_REQUIRED"
    assert len(transport.calls) == 1


def test_a_task_still_working_at_the_deadline_is_a_timeout() -> None:
    transport = ScriptedTransport(
        TARGET,
        [rpc_ok({"task": task_response(state="TASK_STATE_WORKING")})]
        + [rpc_ok(task_response(state="TASK_STATE_WORKING"))] * 1000,
    )
    transcript = run(transport, job(timeout_s=0.05, poll_interval_s=0.02))
    assert transcript.outcome is RunOutcome.TIMEOUT
    assert transcript.final_task_state == "TASK_STATE_WORKING"
    assert "timeout" in (transcript.failure or "")


def test_direct_message_reply() -> None:
    message = {"messageId": "m", "role": "ROLE_AGENT", "parts": [{"text": "hi"}]}
    transcript = run(ScriptedTransport(TARGET, [rpc_ok({"message": message})]))
    assert (
        transcript.outcome is RunOutcome.RESPONDED_MESSAGE and transcript.final_response == message
    )


@pytest.mark.parametrize(
    ("response", "outcome", "fragment"),
    [
        (rpc_error(-32001, "Task not found"), RunOutcome.PROTOCOL_ERROR, "-32001"),
        (rpc_http(503, "unavailable"), RunOutcome.PROTOCOL_ERROR, "HTTP 503"),
        (rpc_http(200, "not json"), RunOutcome.PROTOCOL_ERROR, "not a JSON object"),
        (rpc_ok({}), RunOutcome.PROTOCOL_ERROR, "neither task nor message"),
        (
            rpc_ok({"task": {"status": {"state": "TASK_STATE_WORKING"}}}),
            RunOutcome.PROTOCOL_ERROR,
            "no id to poll",
        ),
        (
            rpc_ok({"task": {"id": "t", "status": {"state": "NOT_A_STATE"}}}),
            RunOutcome.PROTOCOL_ERROR,
            "not a TaskState",
        ),
        (rpc_transport_failure("ConnectError: refused"), RunOutcome.UNREACHABLE, "refused"),
        (rpc_transport_failure("timeout", timed_out=True), RunOutcome.TIMEOUT, "timeout"),
    ],
)
def test_failures_are_classified(
    response: Callable[[str, dict[str, Any]], RpcResponse], outcome: RunOutcome, fragment: str
) -> None:
    transcript = run(ScriptedTransport(TARGET, [response]))
    assert transcript.outcome is outcome
    assert fragment in (transcript.failure or "")
    if outcome is RunOutcome.UNREACHABLE:
        assert transcript.latency_ms is None


# -- redaction and credentials ---------------------------------------------------------


def test_redactor_removes_secrets_headers_and_known_patterns() -> None:
    redactor = Redactor(["Bearer abcdefgh12345678", "abcdefgh12345678"])
    value = {
        "Authorization": "Bearer abcdefgh12345678",
        "cookie": "a=b",
        "body": {
            "text": "token abcdefgh12345678 and sk-abcdefghijklmnopqrstuvwxyz and AKIAABCDEFGHIJKLMNOP",
            "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmnopqrstuvwx",
            "kv": "api_key=supersecretvalue; password: hunter22",
            "encoded": "Bearer%20abcdefgh12345678",
            "safe": "nothing here",
        },
        "list": ["ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123", "xoxb-1234567890-abcdefghij"],
    }
    redacted = redactor.redact(value)
    dumped = json.dumps(redacted)
    for secret in (
        "abcdefgh12345678",
        "a=b",
        "sk-abcdefghijklmnopqrstuvwxyz",
        "AKIAABCDEFGHIJKLMNOP",
        "eyJhbGciOiJIUzI1NiJ9",
        "supersecretvalue",
        "hunter22",
        "ghp_",
        "xoxb-",
    ):
        assert secret not in dumped, secret
    assert redacted["Authorization"] == REDACTED and redacted["cookie"] == REDACTED
    assert redacted["body"]["safe"] == "nothing here"
    assert "api_key=" in redacted["body"]["kv"] and "password: " in redacted["body"]["kv"]
    assert redactor.replacements >= 9
    assert "credential" in redactor.rules_used and "sensitive_key" in redactor.rules_used


def test_redact_transcript_fills_the_summary_and_handles_the_credential_in_urls() -> None:
    transcript = make_transcript().model_copy(
        update={"target_url": "https://x.example.com/rpc?token=abcdefgh12345678"}
    )
    redacted = redact_transcript(transcript, Redactor(["abcdefgh12345678"]))
    assert "abcdefgh12345678" not in redacted.model_dump_json()
    assert redacted.redaction.replacements >= 1 and "credential" in redacted.redaction.rules


def test_credentials_come_from_the_environment_and_never_print() -> None:
    assert read_credentials({}).authorization is None
    assert read_credentials({CREDENTIAL_ENV_VAR: "  "}).authorization is None
    credentials = read_credentials({CREDENTIAL_ENV_VAR: "Bearer tok-1234567"})
    assert credentials.headers() == {"Authorization": "Bearer tok-1234567"}
    assert credentials.secrets() == ["Bearer tok-1234567", "tok-1234567"]
    assert "tok-1234567" not in repr(credentials) and "tok-1234567" not in str(
        Credentials("Bearer tok-1234567")
    )
    assert read_credentials({CREDENTIAL_ENV_VAR: "Basic ab"}).secrets() == ["Basic ab"], (
        "short parts are not secrets on their own"
    )


# -- http transport -------------------------------------------------------------------


def test_https_is_required_except_for_loopback() -> None:
    require_https_or_loopback("https://agent.example.com/rpc", "x")
    require_https_or_loopback("http://127.0.0.1:1/rpc", "x")
    require_https_or_loopback("http://localhost:1/rpc", "x")
    require_https_or_loopback("http://[::1]:1/rpc", "x")
    for url in ("http://agent.example.com/rpc", "ftp://127.0.0.1/x", "agent.example.com"):
        with pytest.raises(TargetHostRefusedError, match="must use https"):
            require_https_or_loopback(url, "x")
    assert (
        is_loopback_host("127.0.0.5")
        and not is_loopback_host("10.0.0.1")
        and not is_loopback_host(None)
    )


def test_the_transport_refuses_any_host_other_than_the_target() -> None:
    with MockAgentServer(behaviours.Honest()) as server:
        transport = HttpxJsonRpcTransport(server.base_url + "/rpc", "1.0", {})
        try:
            # The hook is the single enforcement point; exercise it directly with a foreign request.
            with pytest.raises(TargetHostRefusedError, match="other than the target"):
                transport._refuse_other_hosts(httpx.Request("POST", "https://evil.example.com/rpc"))
            with pytest.raises(TargetHostRefusedError):
                transport._refuse_other_hosts(
                    httpx.Request("POST", server.base_url.replace("http://", "https://") + "/rpc")
                )
            response = transport.call(
                "SendMessage",
                {"message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "hello"}]}},
                "1",
                5.0,
            )
        finally:
            transport.close()
    assert response.http_status == 200
    assert response.request_headers[a2a.VERSION_HEADER] == "1.0"
    assert response.response_body["result"]["task"]["status"]["state"] == "TASK_STATE_COMPLETED"


def test_the_transport_reports_connection_failures_as_transport_errors() -> None:
    with behaviours.DeadPort() as dead:
        transport = HttpxJsonRpcTransport(dead.url, "1.0", {})
        try:
            response = transport.call("SendMessage", {}, "1", 2.0)
        finally:
            transport.close()
    assert response.http_status is None and response.transport_error
    assert not response.timed_out, "a refused or timed-out connection is unreachable, not slow"


# -- process entry point ---------------------------------------------------------------


def run_process(
    j: RunJob | str, env: dict[str, str] | None = None
) -> tuple[int, RunResult | None, str]:
    stdin = io.StringIO(j if isinstance(j, str) else j.model_dump_json())
    stdout = io.StringIO()
    code = process.main(stdin, stdout, env or {})
    text = stdout.getvalue()
    try:
        return code, RunResult.model_validate_json(text), text
    except ValueError:
        return code, None, text


def test_process_runs_a_job_against_a_local_sandbox_and_redacts_the_credential() -> None:
    with MockAgentServer(behaviours.Leaky()) as server:
        code, result, text = run_process(
            job(target_url=server.base_url + "/rpc"),
            {CREDENTIAL_ENV_VAR: "Bearer process-secret-9876543210"},
        )
    assert code == 0 and result is not None and result.transcript is not None
    assert result.transcript.outcome is RunOutcome.RESPONDED_TASK
    assert "process-secret-9876543210" not in text
    assert REDACTED in text
    assert result.transcript.redaction.replacements >= 2


def test_process_refuses_undeclared_sandboxes_and_bad_jobs() -> None:
    code, result, _ = run_process(job(sandbox_declared=False))
    assert code == 0 and result is not None and result.crashed and "DR-006" in (result.error or "")
    code, result, _ = run_process("{not json")
    assert (
        code == 0
        and result is not None
        and result.crashed
        and "invalid run job" in (result.error or "")
    )


def test_process_withholds_the_transcript_when_redaction_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(transcript: Transcript, redactor: Redactor) -> Transcript:
        raise RuntimeError("redaction exploded")

    monkeypatch.setattr(process, "redact_transcript", broken)
    with MockAgentServer(behaviours.Honest()) as server:
        code, result, text = run_process(job(target_url=server.base_url + "/rpc"))
    assert code == 0 and result is not None
    assert result.withheld and result.transcript is None
    assert "exploded" not in text, "the error text never carries transcript content"


def test_process_answers_with_a_crash_result_when_the_target_is_not_https() -> None:
    code, result, _ = run_process(job(target_url="http://agent.example.com/rpc"))
    assert code == 0 and result is not None and result.crashed
    assert "must use https" in (result.error or "")


def test_unreachable_target_gives_a_transcript_not_a_crash() -> None:
    with behaviours.DeadPort() as dead:
        code, result, _ = run_process(job(target_url=dead.url))
    assert code == 0 and result is not None and result.transcript is not None
    assert result.transcript.outcome is RunOutcome.UNREACHABLE


def test_the_credential_variable_is_not_inherited_by_accident_in_tests() -> None:
    assert CREDENTIAL_ENV_VAR not in os.environ or os.environ[CREDENTIAL_ENV_VAR] == ""


def test_timestamps_are_utc() -> None:
    assert datetime.now(UTC).tzinfo is UTC
