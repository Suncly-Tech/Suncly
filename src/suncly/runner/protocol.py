"""The Runner's A2A client logic: send the message, follow the task, record everything.

Pure protocol logic over the ``A2ATransport`` port, so it is tested with a fake
transport. Facts used: A2A §3.1.1 (SendMessage returns a Task or a Message),
§3.2.2 (blocking by default; a non-terminal task is polled with GetTask,
§3.1.3), §8.3.2 (the selected interface's ``tenant`` goes into every request),
§9.4 (JSON-RPC shapes) and the TaskState values of a2a.proto v1.0.1.
The Runner never answers an interrupted state (OQ-A4, proposal).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from suncly.domain import a2a
from suncly.domain.criteria import parse_input
from suncly.domain.models import JsonObject
from suncly.domain.transcript import COST_PER_ATTEMPT, Exchange, RunOutcome, Transcript
from suncly.ports.a2a import A2ATransport, RpcResponse
from suncly.ports.clock import Clock
from suncly.ports.run_executor import RunJob


class _Recorder:
    def __init__(self, target_url: str) -> None:
        self.target_url = target_url
        self.exchanges: list[Exchange] = []

    def add(self, method: str, response: RpcResponse) -> None:
        self.exchanges.append(
            Exchange(
                direction="request",
                at=response.sent_at,
                method=method,
                url=self.target_url,
                headers=response.request_headers,
                body=response.request_body,
            )
        )
        self.exchanges.append(
            Exchange(
                direction="response",
                at=response.received_at,
                method=method,
                url=self.target_url,
                http_status=response.http_status,
                headers=response.response_headers,
                body=response.response_body
                if response.transport_error is None
                else {"transport_error": response.transport_error},
            )
        )


def _request_params(job: RunJob, params: JsonObject) -> JsonObject:
    """``params`` with the interface's ``tenant`` first when one is declared (A2A §8.3.2).

    The field is omitted when the interface declares none, as the same rule requires.
    """
    if job.tenant is None:
        return params
    return {"tenant": job.tenant, **params}


def _rpc_result(response: RpcResponse) -> tuple[JsonObject | None, str | None]:
    """``(result, problem)``: the JSON-RPC result object, or why there is none."""
    if response.transport_error is not None:
        return None, response.transport_error
    if response.http_status != 200:
        return None, f"HTTP {response.http_status} from the agent"
    body = response.response_body
    if not isinstance(body, dict):
        return None, "the response body is not a JSON object"
    error = body.get("error")
    if isinstance(error, dict):
        return None, f"JSON-RPC error {error.get('code')}: {error.get('message')}"
    result = body.get("result")
    if not isinstance(result, dict):
        return None, "the JSON-RPC response has no result object"
    return result, None


def execute_run(
    job: RunJob,
    transport: A2ATransport,
    clock: Clock,
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
) -> Transcript:
    """Run one test case input against the agent and return the unredacted transcript."""
    started_at = clock.now()
    deadline = monotonic() + job.timeout_s
    recorder = _Recorder(transport.target_url)
    message: JsonObject = {
        "messageId": job.message_id,
        "role": a2a.ROLE_USER,
        "parts": parse_input(job.input).to_parts(),
    }
    request_counter = 1

    def remaining() -> float:
        return deadline - monotonic()

    def finish(
        outcome: RunOutcome,
        *,
        latency_ms: int | None = None,
        task_id: str | None = None,
        final_task_state: str | None = None,
        final_response: JsonObject | None = None,
        failure: str | None = None,
    ) -> Transcript:
        return Transcript(
            attestation_id=job.attestation_id,
            test_case_id=job.test_case_id,
            attempt=job.attempt,
            target_url=transport.target_url,
            protocol_binding=job.protocol_binding,
            protocol_version=job.protocol_version,
            started_at=started_at,
            finished_at=clock.now(),
            latency_ms=latency_ms,
            cost=COST_PER_ATTEMPT,
            outcome=outcome,
            task_id=task_id,
            final_task_state=final_task_state,
            final_response=final_response,
            exchanges=recorder.exchanges,
            failure=failure,
        )

    first = transport.call(
        a2a.METHOD_SEND_MESSAGE,
        _request_params(job, {"message": message}),
        str(request_counter),
        max(remaining(), 0.001),
    )
    recorder.add(a2a.METHOD_SEND_MESSAGE, first)
    sent_at = first.sent_at
    result, problem = _rpc_result(first)
    if result is None:
        if first.transport_error is not None:
            outcome = RunOutcome.TIMEOUT if first.timed_out else RunOutcome.UNREACHABLE
            return finish(outcome, failure=problem)
        return finish(RunOutcome.PROTOCOL_ERROR, failure=problem)

    def elapsed_ms(response: RpcResponse) -> int:
        return max(int((response.received_at - sent_at).total_seconds() * 1000), 0)

    if "message" in result:
        reply = result["message"]
        if not isinstance(reply, dict):
            return finish(RunOutcome.PROTOCOL_ERROR, failure="result.message is not an object")
        return finish(
            RunOutcome.RESPONDED_MESSAGE, latency_ms=elapsed_ms(first), final_response=reply
        )
    if "task" not in result:
        return finish(
            RunOutcome.PROTOCOL_ERROR, failure="SendMessage result has neither task nor message"
        )

    task: Any = result["task"]
    last_response = first
    while True:
        if not isinstance(task, dict):
            return finish(RunOutcome.PROTOCOL_ERROR, failure="result.task is not an object")
        state = a2a.task_state(task)
        task_id = task.get("id") if isinstance(task.get("id"), str) else None
        if a2a.is_terminal(state) or a2a.is_interrupted(state):
            return finish(
                RunOutcome.RESPONDED_TASK,
                latency_ms=elapsed_ms(last_response),
                task_id=task_id,
                final_task_state=state,
                final_response=task,
            )
        if state not in a2a.ALL_TASK_STATES:
            return finish(
                RunOutcome.PROTOCOL_ERROR,
                task_id=task_id,
                final_task_state=state,
                final_response=task,
                failure=f"Task.status.state {state!r} is not a TaskState",
            )
        if task_id is None:
            return finish(
                RunOutcome.PROTOCOL_ERROR,
                final_task_state=state,
                final_response=task,
                failure="the task is not final and has no id to poll",
            )
        if remaining() <= 0:
            return finish(
                RunOutcome.TIMEOUT,
                task_id=task_id,
                final_task_state=state,
                final_response=task,
                failure=f"the task was still {state} when the timeout of {job.timeout_s}s expired",
            )
        sleep(min(job.poll_interval_s, max(remaining(), 0)))
        request_counter += 1
        poll = transport.call(
            a2a.METHOD_GET_TASK,
            _request_params(job, {"id": task_id}),
            str(request_counter),
            max(remaining(), 0.001),
        )
        recorder.add(a2a.METHOD_GET_TASK, poll)
        result, problem = _rpc_result(poll)
        if result is None:
            if poll.transport_error is not None:
                outcome = RunOutcome.TIMEOUT if poll.timed_out else RunOutcome.UNREACHABLE
            else:
                outcome = RunOutcome.PROTOCOL_ERROR
            return finish(
                outcome,
                task_id=task_id,
                final_task_state=state,
                final_response=task,
                failure=f"GetTask failed: {problem}",
            )
        task = result
        last_response = poll
