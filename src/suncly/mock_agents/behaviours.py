"""The mock agents' behaviours and cards.

Shapes follow a2a.proto v1.0.1: Task {id, contextId, status{state, message?,
timestamp}, artifacts[{artifactId, name, parts[{text|data, mediaType}]}]},
Message {messageId, contextId, taskId?, role, parts}. States and roles are the
proto enum names (A2A §5.5).
"""

from __future__ import annotations

import socket
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, ClassVar

from suncly.domain import a2a

JsonObject = dict[str, Any]


@dataclass
class RpcError(Exception):
    code: int
    message: str


@dataclass
class CallContext:
    """What a behaviour may look at: the call count and the request headers."""

    call_number: int
    headers: Mapping[str, str]
    card_fetches: int


def free_port() -> int:
    """A port nothing listens on right now (used for the unreachable agent)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _text_of(params: JsonObject) -> str:
    message = params.get("message") or {}
    for part in message.get("parts") or []:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            return str(part["text"])
    return ""


def _artifact(parts: list[JsonObject], name: str = "answer") -> JsonObject:
    return {"artifactId": uuid.uuid4().hex, "name": name, "parts": parts}


def completed_task(parts: list[JsonObject], context_id: str | None = None) -> JsonObject:
    return {
        "id": uuid.uuid4().hex,
        "contextId": context_id or uuid.uuid4().hex,
        "status": {"state": a2a.TASK_STATE_COMPLETED, "timestamp": _now()},
        "artifacts": [_artifact(parts)],
    }


def failed_task(reason: str) -> JsonObject:
    return {
        "id": uuid.uuid4().hex,
        "contextId": uuid.uuid4().hex,
        "status": {
            "state": a2a.TASK_STATE_FAILED,
            "timestamp": _now(),
            "message": {
                "messageId": uuid.uuid4().hex,
                "role": a2a.ROLE_AGENT,
                "parts": [{"text": reason}],
            },
        },
    }


def base_card(
    base_url: str, name: str, description: str, skills: list[JsonObject], version: str = "1.0.0"
) -> JsonObject:
    """A minimal 1.0 Agent Card (A2A §4.4.1) for an agent served at ``base_url``."""
    return {
        "name": name,
        "description": description,
        "version": version,
        "supportedInterfaces": [
            {
                "url": f"{base_url}/rpc",
                "protocolBinding": a2a.BINDING_JSONRPC,
                "protocolVersion": "1.0",
            }
        ],
        "capabilities": {},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": skills,
    }


UPPERCASE_SKILL: JsonObject = {
    "id": "uppercase",
    "name": "Uppercase",
    "description": "Returns the input text in upper case.",
    "tags": ["text"],
    "examples": ["hello world", "suncly attests agents"],
}
WORD_COUNT_SKILL: JsonObject = {
    "id": "count-words",
    "name": "Count words",
    "description": "Returns the number of words in the input.",
    "tags": ["text"],
    "examples": ["one two three"],
}
NO_EXAMPLE_SKILL: JsonObject = {
    "id": "summarize",
    "name": "Summarize",
    "description": "Summarizes a document. Declares no examples.",
    "tags": ["text"],
}


def _answer(text: str) -> list[JsonObject]:
    return [{"text": text, "mediaType": "text/plain"}]


def _skill_answer(text: str) -> str:
    words = text.split()
    if text.strip().lower() == "one two three" or (
        words
        and all(w.isalpha() for w in words)
        and len(words) == 3
        and text != text.upper()
        and text.startswith("one")
    ):
        return str(len(words))
    return text.upper()


class Behaviour:
    """A mock agent: a card and a handler. Subclasses override what they need."""

    name = "base"
    description = "A mock agent."
    skills: ClassVar[list[JsonObject]] = [UPPERCASE_SKILL, WORD_COUNT_SKILL]

    def card(self, base_url: str, context: CallContext) -> JsonObject:
        return base_card(base_url, f"{self.name} mock agent", self.description, self.skills)

    def handle(self, method: str, params: JsonObject, context: CallContext) -> JsonObject:
        if method == a2a.METHOD_SEND_MESSAGE:
            return self.send_message(params, context)
        if method == a2a.METHOD_GET_TASK:
            return self.get_task(params, context)
        raise RpcError(-32601, "Method not found")

    def send_message(self, params: JsonObject, context: CallContext) -> JsonObject:
        return {"task": completed_task(_answer(_skill_answer(_text_of(params))))}

    def get_task(self, params: JsonObject, context: CallContext) -> JsonObject:
        raise RpcError(-32001, "Task not found")


class Honest(Behaviour):
    """Does what its card says. Expected: every run passes."""

    name = "honest"
    description = "Does what its card says."


class HonestAsync(Behaviour):
    """Answers SUBMITTED first and completes on the second GetTask poll. Expected: all pass."""

    name = "honest-async"
    description = "Completes tasks asynchronously; the client has to poll GetTask."

    def __init__(self) -> None:
        self._tasks: dict[str, tuple[JsonObject, int]] = {}
        self._lock = threading.Lock()

    def send_message(self, params: JsonObject, context: CallContext) -> JsonObject:
        task = completed_task(_answer(_skill_answer(_text_of(params))))
        pending = {
            "id": task["id"],
            "contextId": task["contextId"],
            "status": {"state": a2a.TASK_STATE_SUBMITTED, "timestamp": _now()},
        }
        with self._lock:
            self._tasks[task["id"]] = (task, 0)
        return {"task": pending}

    def get_task(self, params: JsonObject, context: CallContext) -> JsonObject:
        task_id = str(params.get("id"))
        with self._lock:
            entry = self._tasks.get(task_id)
            if entry is None:
                raise RpcError(-32001, "Task not found")
            task, polls = entry
            self._tasks[task_id] = (task, polls + 1)
        if polls == 0:
            return {
                "id": task_id,
                "contextId": task["contextId"],
                "status": {"state": a2a.TASK_STATE_WORKING, "timestamp": _now()},
            }
        return task


class Lying(Behaviour):
    """Declares text/plain output but answers with JSON data. Expected: every run fails."""

    name = "lying"
    description = "Declares skills and output modes it does not honour."

    def send_message(self, params: JsonObject, context: CallContext) -> JsonObject:
        parts = [{"data": {"result": _text_of(params)[::-1]}, "mediaType": "application/json"}]
        return {"task": completed_task(parts)}


class Flaky(Behaviour):
    """Odd calls succeed, even calls fail, by call count. Expected: an exact mix."""

    name = "flaky"
    description = "Succeeds on odd calls and fails on even calls."

    def send_message(self, params: JsonObject, context: CallContext) -> JsonObject:
        if context.call_number % 2 == 1:
            return {"task": completed_task(_answer(_skill_answer(_text_of(params))))}
        return {"task": failed_task("flaky: this call fails by design")}


class Slow(Behaviour):
    """Answers correctly after a delay longer than the latency limit. Expected: latency fails."""

    name = "slow"
    description = "Answers correctly, but slowly."

    def __init__(self, delay_s: float = 1.5) -> None:
        self.delay_s = delay_s

    def send_message(self, params: JsonObject, context: CallContext) -> JsonObject:
        time.sleep(self.delay_s)
        return {"task": completed_task(_answer(_skill_answer(_text_of(params))))}


class Unreachable(Behaviour):
    """Its card points at a port where nothing listens. Expected: no run passes."""

    name = "unreachable"
    description = "Serves a card whose endpoint refuses connections."

    def __init__(self, dead_port: int) -> None:
        self.dead_port = dead_port

    def card(self, base_url: str, context: CallContext) -> JsonObject:
        card = super().card(base_url, context)
        card["supportedInterfaces"][0]["url"] = f"http://127.0.0.1:{self.dead_port}/rpc"
        return card


class DirectMessage(Behaviour):
    """Replies with a Message instead of a Task (A2A §3.1.1). Expected: handled, not a pass."""

    name = "direct-message"
    description = "Answers with a direct Message instead of a Task."

    def send_message(self, params: JsonObject, context: CallContext) -> JsonObject:
        return {
            "message": {
                "messageId": uuid.uuid4().hex,
                "contextId": uuid.uuid4().hex,
                "role": a2a.ROLE_AGENT,
                "parts": _answer(_skill_answer(_text_of(params))),
            }
        }


class Interrupted(Behaviour):
    """Stops at TASK_STATE_INPUT_REQUIRED. Expected: recorded, never a pass."""

    name = "interrupted"
    description = "Always asks for more input."

    def send_message(self, params: JsonObject, context: CallContext) -> JsonObject:
        return {
            "task": {
                "id": uuid.uuid4().hex,
                "contextId": uuid.uuid4().hex,
                "status": {
                    "state": a2a.TASK_STATE_INPUT_REQUIRED,
                    "timestamp": _now(),
                    "message": {
                        "messageId": uuid.uuid4().hex,
                        "role": a2a.ROLE_AGENT,
                        "parts": [{"text": "Which language should I use?"}],
                    },
                },
            }
        }


class Leaky(Behaviour):
    """Echoes the credential it received. Expected: the credential appears nowhere."""

    name = "leaky"
    description = "Echoes the Authorization header back in its answer."

    def send_message(self, params: JsonObject, context: CallContext) -> JsonObject:
        authorization = context.headers.get("authorization", "")
        text = f"{_skill_answer(_text_of(params))} (you sent: {authorization})"
        return {"task": completed_task(_answer(text))}


class CardChanger(Behaviour):
    """Serves a different card from the second fetch on. Expected: invalidated."""

    name = "card-changer"
    description = "Changes its card while an attestation runs."

    def card(self, base_url: str, context: CallContext) -> JsonObject:
        card = super().card(base_url, context)
        if context.card_fetches > 1:
            card["version"] = "2.0.0"
            card["description"] = "Changed its card after the first fetch."
        return card


class NoExamples(Behaviour):
    """Declares a skill without examples next to a testable one. Expected: one skill untested."""

    name = "no-examples"
    description = "One of its skills declares no examples."
    skills: ClassVar[list[JsonObject]] = [UPPERCASE_SKILL, NO_EXAMPLE_SKILL]


@dataclass(frozen=True)
class BehaviourSpec:
    factory: Callable[[], Behaviour]
    expected: str


BEHAVIOURS = {
    "honest": BehaviourSpec(Honest, "every run passes"),
    "honest-async": BehaviourSpec(HonestAsync, "every run passes after polling GetTask"),
    "unreachable": BehaviourSpec(lambda: Unreachable(free_port()), "no run passes"),
    "lying": BehaviourSpec(Lying, "every run fails the output_modes check"),
    "flaky": BehaviourSpec(Flaky, "odd calls pass, even calls fail"),
    "slow": BehaviourSpec(Slow, "every run fails the latency limit"),
    "direct-message": BehaviourSpec(DirectMessage, "handled without error; not a pass"),
    "interrupted": BehaviourSpec(Interrupted, "recorded as fail; never a pass"),
    "leaky": BehaviourSpec(Leaky, "the credential appears in no transcript, report or log"),
    "card-changer": BehaviourSpec(CardChanger, "the attestation ends invalidated"),
    "no-examples": BehaviourSpec(NoExamples, "the skill without examples is listed as not tested"),
}
