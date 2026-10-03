"""A2A protocol facts and structural checks shared by the Runner and the Judge.

Every constant here comes from the A2A specification v1.0.1 as recorded in
docs/ARCHITECTURE.md (A2A protocol dependencies) and from ``a2a.proto`` at tag
v1.0.1. Nothing is inferred beyond what those sources state.
"""

from __future__ import annotations

from typing import Any

from suncly.domain.models import JsonObject

#: The protocol version Suncly speaks (A2A §3.6: Major.Minor only).
PROTOCOL_VERSION = "1.0"
#: Service parameter carrying the protocol version (A2A §3.2.6, §9.2).
VERSION_HEADER = "A2A-Version"

#: Core protocol binding identifiers (AgentInterface.protocolBinding, a2a.proto v1.0.1).
BINDING_JSONRPC = "JSONRPC"
BINDING_GRPC = "GRPC"
BINDING_HTTP_JSON = "HTTP+JSON"

#: JSON-RPC method names (A2A §5.3, §9.1: PascalCase).
METHOD_SEND_MESSAGE = "SendMessage"
METHOD_GET_TASK = "GetTask"

#: Message roles (a2a.proto v1.0.1, enum Role).
ROLE_USER = "ROLE_USER"
ROLE_AGENT = "ROLE_AGENT"
ROLES = frozenset({ROLE_USER, ROLE_AGENT})

#: Task states (a2a.proto v1.0.1, enum TaskState), as JSON strings (A2A §5.5).
TASK_STATE_UNSPECIFIED = "TASK_STATE_UNSPECIFIED"
TASK_STATE_SUBMITTED = "TASK_STATE_SUBMITTED"
TASK_STATE_WORKING = "TASK_STATE_WORKING"
TASK_STATE_COMPLETED = "TASK_STATE_COMPLETED"
TASK_STATE_FAILED = "TASK_STATE_FAILED"
TASK_STATE_CANCELED = "TASK_STATE_CANCELED"
TASK_STATE_INPUT_REQUIRED = "TASK_STATE_INPUT_REQUIRED"
TASK_STATE_REJECTED = "TASK_STATE_REJECTED"
TASK_STATE_AUTH_REQUIRED = "TASK_STATE_AUTH_REQUIRED"

#: Terminal states (A2A §3.1.1). A "final task state" (schema §2) is one of these.
TERMINAL_TASK_STATES = frozenset(
    {TASK_STATE_COMPLETED, TASK_STATE_FAILED, TASK_STATE_CANCELED, TASK_STATE_REJECTED}
)
#: Interrupted states (A2A §3.2.2). Not final; the Runner stops and records them.
INTERRUPTED_TASK_STATES = frozenset({TASK_STATE_INPUT_REQUIRED, TASK_STATE_AUTH_REQUIRED})
ALL_TASK_STATES = frozenset(
    {TASK_STATE_UNSPECIFIED, TASK_STATE_SUBMITTED, TASK_STATE_WORKING}
    | TERMINAL_TASK_STATES
    | INTERRUPTED_TASK_STATES
)

#: The ``oneof content`` members of Part (a2a.proto v1.0.1). Exactly one is set.
PART_CONTENT_KEYS = ("text", "raw", "url", "data")

#: Media type Suncly assumes for a ``text`` part that declares none. This is a judging
#: rule of Suncly's, not a statement of the spec (docs/IMPLEMENTATION_NOTES.md).
TEXT_PART_DEFAULT_MEDIA_TYPE = "text/plain"


def is_terminal(state: str | None) -> bool:
    return state in TERMINAL_TASK_STATES


def is_interrupted(state: str | None) -> bool:
    return state in INTERRUPTED_TASK_STATES


def part_content_key(part: Any) -> str | None:
    """The one content key a Part sets, or ``None`` when it sets none or several."""
    if not isinstance(part, dict):
        return None
    present = [key for key in PART_CONTENT_KEYS if key in part]
    return present[0] if len(present) == 1 else None


def part_has_content(part: Any) -> bool:
    """True when the part carries non-empty content."""
    key = part_content_key(part)
    if key is None:
        return False
    value = part[key]
    if key in ("text", "raw", "url"):
        return isinstance(value, str) and value.strip() != ""
    return value is not None


def part_media_type(part: JsonObject) -> str | None:
    """The media type of a part: ``mediaType`` if declared, else text/plain for text parts."""
    declared = part.get("mediaType")
    if isinstance(declared, str) and declared:
        return declared
    if part_content_key(part) == "text":
        return TEXT_PART_DEFAULT_MEDIA_TYPE
    return None


def structural_problems_of_parts(parts: Any, where: str) -> list[str]:
    problems: list[str] = []
    if not isinstance(parts, list) or not parts:
        return [f"{where}.parts must be a non-empty list (REQUIRED in a2a.proto)"]
    for index, part in enumerate(parts):
        if part_content_key(part) is None:
            problems.append(
                f"{where}.parts[{index}] must set exactly one of {', '.join(PART_CONTENT_KEYS)}"
            )
    return problems


def structural_problems_of_message(message: Any) -> list[str]:
    """Why ``message`` is not a valid A2A Message (a2a.proto v1.0.1, REQUIRED fields)."""
    if not isinstance(message, dict):
        return ["Message must be a JSON object"]
    problems: list[str] = []
    if not isinstance(message.get("messageId"), str) or not message["messageId"]:
        problems.append("Message.messageId is REQUIRED")
    if message.get("role") not in ROLES:
        problems.append(f"Message.role must be one of {sorted(ROLES)}")
    problems.extend(structural_problems_of_parts(message.get("parts"), "Message"))
    return problems


def structural_problems_of_task(task: Any) -> list[str]:
    """Why ``task`` is not a valid A2A Task (a2a.proto v1.0.1, REQUIRED fields)."""
    if not isinstance(task, dict):
        return ["Task must be a JSON object"]
    problems: list[str] = []
    if not isinstance(task.get("id"), str) or not task["id"]:
        problems.append("Task.id is REQUIRED")
    status = task.get("status")
    if not isinstance(status, dict):
        problems.append("Task.status is REQUIRED")
    elif status.get("state") not in ALL_TASK_STATES:
        problems.append(f"Task.status.state must be a TaskState, got {status.get('state')!r}")
    artifacts = task.get("artifacts")
    if artifacts is not None:
        if not isinstance(artifacts, list):
            problems.append("Task.artifacts must be a list")
        else:
            for index, artifact in enumerate(artifacts):
                if not isinstance(artifact, dict):
                    problems.append(f"Task.artifacts[{index}] must be an object")
                    continue
                if not isinstance(artifact.get("artifactId"), str) or not artifact["artifactId"]:
                    problems.append(f"Task.artifacts[{index}].artifactId is REQUIRED")
                problems.extend(
                    structural_problems_of_parts(artifact.get("parts"), f"Task.artifacts[{index}]")
                )
    return problems


def task_state(task: JsonObject) -> str | None:
    status = task.get("status")
    if isinstance(status, dict):
        state = status.get("state")
        return state if isinstance(state, str) else None
    return None


def output_parts(response: JsonObject, is_task: bool) -> list[JsonObject]:
    """The parts that carry the agent's output: artifact parts of a Task, or Message parts."""
    if is_task:
        parts: list[JsonObject] = []
        for artifact in response.get("artifacts") or []:
            if isinstance(artifact, dict):
                parts.extend(p for p in artifact.get("parts") or [] if isinstance(p, dict))
        return parts
    return [p for p in response.get("parts") or [] if isinstance(p, dict)]
