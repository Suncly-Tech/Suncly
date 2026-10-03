"""The format of ``test_case.input`` and ``test_case.criteria``.

Both formats are open (OQ-D7). This module is the stage 1 proposal: ``input``
is the message to send, and ``criteria`` holds the Layer 1 checks of schema §2
(valid schema, final task state, required fields, latency limit) plus the
declared output modes. Unknown keys are rejected so a typo can never silently
weaken a check.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from suncly.domain.a2a import TASK_STATE_COMPLETED, TERMINAL_TASK_STATES
from suncly.domain.models import JsonObject


class TestInput(BaseModel):
    """``test_case.input``: the Message to send. Either ``text`` or explicit A2A ``parts``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str | None = None
    parts: list[JsonObject] | None = None

    @model_validator(mode="after")
    def _exactly_one_form(self) -> TestInput:
        if (self.text is None) == (self.parts is None):
            raise ValueError("input needs exactly one of text or parts")
        if self.text is not None and not self.text.strip():
            raise ValueError("input text must not be blank")
        if self.parts is not None and not self.parts:
            raise ValueError("input parts must not be empty")
        return self

    def to_parts(self) -> list[JsonObject]:
        """The A2A Part objects to send (a2a.proto v1.0.1, message Part)."""
        if self.parts is not None:
            return [dict(part) for part in self.parts]
        return [{"text": self.text}]


class Criteria(BaseModel):
    """``test_case.criteria``: the Layer 1 checks for one test case.

    - ``final_state``: the terminal state the task must reach (schema §2: final task state).
    - ``latency_limit_ms``: the latency limit (schema §2).
    - ``response_present``: the response carries content: at least one artifact part for a
      Task, or one message part for a direct Message.
    - ``output_modes``: every output part's media type is in this list (the card's declared
      output modes). ``None`` disables the check.
    - ``required_fields``: JSON pointer paths (RFC 6901) that must exist and be non-empty in
      the final response (schema §2: required fields).
    - ``response_schema``: a JSON Schema the final response must satisfy (schema §2: valid
      schema). The A2A structure itself is always checked.
    - ``model_checks``: criteria Layer 1 cannot decide. They need Layer 2 (stage 4), so in
      this version every run with a model check is ``inconclusive``.
    - ``accept_direct_message``: a direct Message reply counts as a completed task. Off by
      default; the drafter never sets it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    final_state: str = TASK_STATE_COMPLETED
    latency_limit_ms: int = Field(ge=1)
    response_present: bool = True
    output_modes: list[str] | None = None
    required_fields: list[str] = Field(default_factory=list)
    response_schema: JsonObject | None = None
    model_checks: list[str] = Field(default_factory=list)
    accept_direct_message: bool = False
    """When true, a direct Message reply (A2A §3.1.1) satisfies the final-state check."""

    @model_validator(mode="after")
    def _final_state_is_terminal(self) -> Criteria:
        if self.final_state not in TERMINAL_TASK_STATES:
            raise ValueError(
                f"final_state must be a terminal task state, one of "
                f"{sorted(TERMINAL_TASK_STATES)}; got {self.final_state!r}"
            )
        for pointer in self.required_fields:
            if not pointer.startswith("/"):
                raise ValueError(
                    f"required_fields entries are JSON pointers starting with '/': {pointer!r}"
                )
        return self


def parse_input(value: Any) -> TestInput:
    return TestInput.model_validate(value)


def parse_criteria(value: Any) -> Criteria:
    return Criteria.model_validate(value)
