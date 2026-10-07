"""The format of ``test_case.input`` and ``test_case.criteria``.

Both formats were open (OQ-D7) and are decided for the model checks (founders,
2026-10-07; docs/IMPLEMENTATION_NOTES.md section 3): ``input`` is the message
to send, and ``criteria`` holds the Layer 1 checks of schema §2 (valid schema,
final task state, required fields, latency limit), the declared output modes,
and the model checks for Layer 2, each an object with a name, the criterion
text, the expected answer shape and the pass rule. Unknown keys are rejected
so a typo can never silently weaken a check.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from suncly.domain.a2a import TASK_STATE_COMPLETED, TERMINAL_TASK_STATES
from suncly.domain.models import JsonObject

#: The answer shapes Layer 2 can ask a model for (OQ-D7, decided).
ExpectedAnswer = Literal["yes_no", "score_0_to_10"]

#: Pass rule of a ``score_0_to_10`` check: ``at_least <n>`` with ``n`` from 0 to 10.
SCORE_PASS_RULE = re.compile(r"^at_least (10|[0-9])$")


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


class ModelCheck(BaseModel):
    """One criterion Layer 1 cannot decide, judged by Layer 2 (OQ-D7, decided 2026-10-07).

    - ``name``: identifies the check within its test case.
    - ``criterion``: the criterion text, placed verbatim in the rubric frame.
    - ``expected``: the answer shape the model is asked for: ``yes_no`` or ``score_0_to_10``.
    - ``pass_rule``: which answers pass: ``yes`` or ``no`` for ``yes_no``; ``at_least <n>``
      for ``score_0_to_10``.

    Every field is required and unknown keys are refused, so a check is always fully
    specified.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    criterion: str = Field(min_length=1)
    expected: ExpectedAnswer
    pass_rule: str = Field(min_length=1)

    @model_validator(mode="after")
    def _pass_rule_matches_the_shape(self) -> ModelCheck:
        if not self.name.strip() or not self.criterion.strip():
            raise ValueError("a model check's name and criterion must not be blank")
        if self.expected == "yes_no" and self.pass_rule not in ("yes", "no"):
            raise ValueError(
                f"the pass_rule of a yes_no check is 'yes' or 'no'; got {self.pass_rule!r}"
            )
        if self.expected == "score_0_to_10" and not SCORE_PASS_RULE.match(self.pass_rule):
            raise ValueError(
                "the pass_rule of a score_0_to_10 check is 'at_least <n>' with n from 0 to 10; "
                f"got {self.pass_rule!r}"
            )
        return self

    def passes(self, answer: str | int) -> bool:
        """Apply the pass rule to a parsed answer of the expected shape."""
        if self.expected == "yes_no":
            return answer == self.pass_rule
        match = SCORE_PASS_RULE.match(self.pass_rule)
        assert match is not None  # guaranteed by validation
        return isinstance(answer, int) and answer >= int(match.group(1))


class Criteria(BaseModel):
    """``test_case.criteria``: the checks for one test case.

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
    - ``model_checks``: criteria Layer 1 cannot decide, each a ``ModelCheck``. Layer 2 judges
      them when a judge model is configured; without one, every run with a model check is
      ``inconclusive``.
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
    model_checks: list[ModelCheck] = Field(default_factory=list)
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
        names = [check.name for check in self.model_checks]
        if len(set(names)) != len(names):
            raise ValueError(f"model_checks names must be unique within a test case: {names}")
        return self


def parse_input(value: Any) -> TestInput:
    return TestInput.model_validate(value)


def parse_criteria(value: Any) -> Criteria:
    return Criteria.model_validate(value)
