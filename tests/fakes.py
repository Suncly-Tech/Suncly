"""Deterministic fakes for the ports, so core components are tested without I/O."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from suncly.core.signing import key_id_for
from suncly.domain import a2a
from suncly.domain.errors import CardFetchError
from suncly.domain.evidence import EvidenceBundle
from suncly.domain.models import JsonObject
from suncly.domain.transcript import COST_PER_ATTEMPT, Exchange, RunOutcome, Transcript
from suncly.ports.a2a import RpcResponse
from suncly.ports.card_fetcher import FetchedCard
from suncly.ports.run_executor import RunJob, RunResult

EPOCH = datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)


class FakeClock:
    """Advances one second per call, so timestamps are distinct and ordered."""

    def __init__(self, start: datetime = EPOCH) -> None:
        self._now = start

    def now(self) -> datetime:
        current = self._now
        self._now = current + timedelta(seconds=1)
        return current

    def advance(self, **delta: float) -> None:
        """Jump forward (``seconds=``, ``minutes=``, ``hours=``, ``days=``)."""
        self._now = self._now + timedelta(**delta)


class SeqIds:
    def __init__(self) -> None:
        self._n = 0

    def new_id(self) -> UUID:
        self._n += 1
        return UUID(int=self._n)


class StaticFetcher:
    """Serves card texts per URL; a list of texts is served in order, the last one repeating."""

    def __init__(self, cards: dict[str, str | list[str]], clock: FakeClock | None = None) -> None:
        self._cards = {url: ([v] if isinstance(v, str) else list(v)) for url, v in cards.items()}
        self._served: dict[str, int] = {}
        self._clock = clock or FakeClock()
        self.fetches = 0

    def fetch(self, url: str) -> FetchedCard:
        self.fetches += 1
        texts = self._cards.get(url)
        if texts is None:
            raise CardFetchError("The card could not be fetched.", f"No card at {url}.")
        index = min(self._served.get(url, 0), len(texts) - 1)
        self._served[url] = index + 1
        return FetchedCard(url=url, raw_json=texts[index], fetched_at=self._clock.now())


def card_json(
    *,
    name: str = "Test Agent",
    url: str = "https://agent.example.com/rpc",
    skills: list[JsonObject] | None = None,
    output_modes: list[str] | None = None,
    extra: JsonObject | None = None,
    binding: str = "JSONRPC",
    version: str = "1.0",
) -> JsonObject:
    card: JsonObject = {
        "name": name,
        "description": "An agent for tests.",
        "version": "1.0.0",
        "supportedInterfaces": [
            {"url": url, "protocolBinding": binding, "protocolVersion": version}
        ],
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": output_modes or ["text/plain"],
        "skills": skills
        if skills is not None
        else [
            {
                "id": "echo",
                "name": "Echo",
                "description": "Echoes.",
                "tags": ["text"],
                "examples": ["hello"],
            }
        ],
    }
    if extra:
        card.update(extra)
    return card


def card_text(**kwargs: Any) -> str:
    return json.dumps(card_json(**kwargs))


def task_response(
    text: str = "HELLO", state: str = "TASK_STATE_COMPLETED", media_type: str | None = "text/plain"
) -> JsonObject:
    part: JsonObject = {"text": text}
    if media_type:
        part["mediaType"] = media_type
    return {
        "id": "task-1",
        "contextId": "ctx-1",
        "status": {"state": state, "timestamp": "2026-10-04T12:00:00.000Z"},
        "artifacts": [{"artifactId": "a-1", "parts": [part]}],
    }


def make_transcript(
    job: RunJob | None = None,
    *,
    outcome: RunOutcome = RunOutcome.RESPONDED_TASK,
    final_response: JsonObject | None = None,
    latency_ms: int | None = 50,
    failure: str | None = None,
    clock: FakeClock | None = None,
) -> Transcript:
    clock = clock or FakeClock()
    attestation_id = job.attestation_id if job else UUID(int=1)
    test_case_id = job.test_case_id if job else UUID(int=2)
    attempt = job.attempt if job else 1
    if final_response is None and outcome in (RunOutcome.RESPONDED_TASK,):
        final_response = task_response()
    state = None
    if final_response is not None and outcome is RunOutcome.RESPONDED_TASK:
        state = a2a.task_state(final_response)
    started = clock.now()
    return Transcript(
        attestation_id=attestation_id,
        test_case_id=test_case_id,
        attempt=attempt,
        target_url=job.target_url if job else "https://agent.example.com/rpc",
        protocol_binding="JSONRPC",
        protocol_version="1.0",
        started_at=started,
        finished_at=clock.now(),
        latency_ms=latency_ms if outcome is not RunOutcome.UNREACHABLE else None,
        cost=COST_PER_ATTEMPT,
        outcome=outcome,
        task_id="task-1" if outcome is RunOutcome.RESPONDED_TASK else None,
        final_task_state=state,
        final_response=final_response,
        exchanges=[
            Exchange(direction="request", at=started, method="SendMessage", url="x", body={}),
        ],
        failure=failure,
    )


@dataclass
class FakeExecutor:
    """Scripted Runner: ``behaviour(job, attempt_number) -> RunResult``."""

    behaviour: Callable[[RunJob, int], RunResult]
    jobs: list[RunJob] = field(default_factory=list)
    attempts: dict[tuple[UUID, UUID, int], int] = field(default_factory=dict)

    def execute(self, job: RunJob) -> RunResult:
        key = (job.attestation_id, job.test_case_id, job.attempt)
        self.attempts[key] = self.attempts.get(key, 0) + 1
        self.jobs.append(job)
        return self.behaviour(job, self.attempts[key])


def passing_executor(clock: FakeClock | None = None) -> FakeExecutor:
    return FakeExecutor(lambda job, n: RunResult(transcript=make_transcript(job, clock=clock)))


class MemorySigner:
    def __init__(self) -> None:
        self._key = ed25519.Ed25519PrivateKey.generate()
        self._public = self._key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )

    @property
    def key_id(self) -> str:
        return key_id_for(self._public)

    @property
    def public_key(self) -> bytes:
        return self._public

    def sign(self, payload: bytes) -> bytes:
        return self._key.sign(payload)


class MemorySigningKeys:
    def __init__(self, signer: MemorySigner | None = None) -> None:
        self._signer = signer
        self.created = 0

    def current(self) -> MemorySigner | None:
        return self._signer

    def create(self) -> MemorySigner:
        self._signer = MemorySigner()
        self.created += 1
        return self._signer

    def public_key_for(self, key_id: str) -> bytes | None:
        if self._signer and self._signer.key_id == key_id:
            return self._signer.public_key
        return None


class FailingSigner(MemorySigner):
    def sign(self, payload: bytes) -> bytes:
        raise OSError("the key device is gone")


class MemoryReportWriter:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.bundles: list[EvidenceBundle] = []

    def write(self, bundle: EvidenceBundle) -> Path:
        self.bundles.append(bundle)
        return self.folder / str(bundle.attestation.id)


class ScriptedTransport:
    """An ``A2ATransport`` answering from a list of ``RpcResponse``-building callables."""

    def __init__(
        self, target_url: str, responses: list[Callable[[str, dict[str, Any]], RpcResponse]]
    ) -> None:
        self._target_url = target_url
        self._responses = iter(responses)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    @property
    def target_url(self) -> str:
        return self._target_url

    def call(
        self, method: str, params: dict[str, Any], request_id: str, timeout_s: float
    ) -> RpcResponse:
        self.calls.append((method, params))
        try:
            build = next(self._responses)
        except StopIteration as exc:
            raise AssertionError(f"unexpected call {method}") from exc
        return build(method, params)

    def get_json(self, url: str, timeout_s: float) -> RpcResponse:
        self.calls.append(("GET", {"url": url}))
        try:
            build = next(self._responses)
        except StopIteration as exc:
            raise AssertionError(f"unexpected GET {url}") from exc
        return build("GET", {"url": url})


def rpc_ok(
    result: JsonObject, clock: FakeClock | None = None
) -> Callable[[str, dict[str, Any]], RpcResponse]:
    clock = clock or FakeClock()

    def build(method: str, params: dict[str, Any]) -> RpcResponse:
        sent = clock.now()
        return RpcResponse(
            sent_at=sent,
            received_at=clock.now(),
            request_headers={"Authorization": "Bearer secret-token-value-123456"},
            request_body={"jsonrpc": "2.0", "id": "1", "method": method, "params": params},
            http_status=200,
            response_headers={"content-type": "application/json"},
            response_body={"jsonrpc": "2.0", "id": "1", "result": result},
        )

    return build


def rpc_error(code: int, message: str) -> Callable[[str, dict[str, Any]], RpcResponse]:
    def build(method: str, params: dict[str, Any]) -> RpcResponse:
        return RpcResponse(
            sent_at=EPOCH,
            received_at=EPOCH + timedelta(milliseconds=5),
            request_body={},
            http_status=200,
            response_body={
                "jsonrpc": "2.0",
                "id": "1",
                "error": {"code": code, "message": message},
            },
        )

    return build


def rpc_transport_failure(
    error: str, timed_out: bool = False
) -> Callable[[str, dict[str, Any]], RpcResponse]:
    def build(method: str, params: dict[str, Any]) -> RpcResponse:
        return RpcResponse(
            sent_at=EPOCH,
            received_at=EPOCH + timedelta(seconds=1),
            request_body={},
            http_status=None,
            response_body=None,
            transport_error=error,
            timed_out=timed_out,
        )

    return build


def rpc_http(status: int, body: Any) -> Callable[[str, dict[str, Any]], RpcResponse]:
    def build(method: str, params: dict[str, Any]) -> RpcResponse:
        return RpcResponse(
            sent_at=EPOCH,
            received_at=EPOCH + timedelta(milliseconds=5),
            request_body={},
            http_status=status,
            response_body=body,
        )

    return build


def decimal(value: int | str) -> Decimal:
    return Decimal(value)


def iter_files(folder: Path) -> Iterator[Path]:
    yield from (p for p in folder.rglob("*") if p.is_file())
