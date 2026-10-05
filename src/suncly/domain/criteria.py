"""The format of ``test_case.input`` and ``test_case.criteria``.

Both formats were open (OQ-D7). Format 1 holds the Layer 1 checks of schema
§2 (valid schema, final task state, required fields, latency limit) plus the
declared output modes. Format 2 (``format_version: 2``) adds what the
behavioural suite compiles to: the result category, deterministic assertions,
a versioned rubric for the model judge, negative cases and the optional
sandbox-state verification. Unknown keys are rejected so a typo can never
silently weaken a check.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from suncly.domain.a2a import TASK_STATE_COMPLETED, TERMINAL_TASK_STATES
from suncly.domain.models import JsonObject


#: Keys that exist only in criteria format 2.
FORMAT_2_KEYS = (
    "suite_case_id",
    "category",
    "assertions",
    "expected_output",
    "rubric",
    "reference_examples",
    "negative",
    "sandbox_verification",
)


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
    """``test_case.criteria``: the checks for one test case.

    Format 1 fields:

    - ``final_state``: the terminal state the task must reach (schema §2: final task state).
    - ``latency_limit_ms``: the latency limit (schema §2).
    - ``response_present``: the response carries content.
    - ``output_modes``: every output part's media type is in this list; ``None`` disables it.
    - ``required_fields``: JSON pointers that must exist and be non-empty in the final response.
    - ``response_schema``: a JSON Schema the final response must satisfy.
    - ``model_checks``: free-text criteria Layer 1 cannot decide. With a configured model
      judge they become rubric statements; without one every such run is ``inconclusive``.
    - ``accept_direct_message``: a direct Message reply counts as a completed task.

    Format 2 adds ``category``, ``assertions``, ``expected_output``, ``rubric``,
    ``reference_examples``, ``negative``, ``sandbox_verification`` and ``suite_case_id``
    (``domain/behavioral.py``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    format_version: int = Field(default=1, ge=1, le=2)
    final_state: str = TASK_STATE_COMPLETED
    latency_limit_ms: int = Field(ge=1)
    response_present: bool = True
    output_modes: list[str] | None = None
    required_fields: list[str] = Field(default_factory=list)
    response_schema: JsonObject | None = None
    model_checks: list[str] = Field(default_factory=list)
    accept_direct_message: bool = False
    """When true, a direct Message reply (A2A §3.1.1) satisfies the final-state check."""
    # -- format 2 ------------------------------------------------------------------
    suite_case_id: str | None = None
    category: str | None = Field(
        default=None, pattern=r"^(protocol|semantic|security|operational)$"
    )
    assertions: list[JsonObject] = Field(default_factory=list)
    expected_output: str | None = None
    rubric: JsonObject | None = None
    reference_examples: list[JsonObject] = Field(default_factory=list)
    negative: bool = False
    sandbox_verification: JsonObject | None = None

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
        if self.format_version == 1 and (
            self.assertions
            or self.rubric is not None
            or self.expected_output is not None
            or self.negative
            or self.sandbox_verification is not None
            or self.category is not None
        ):
            raise ValueError("format 2 fields need format_version 2")
        return self

    def to_document(self) -> JsonObject:
        """The stored form: format 1 keys only for format 1, so older contracts stay identical."""
        document = self.model_dump(mode="json", exclude_none=True)
        if self.format_version == 1:
            for key in FORMAT_2_KEYS:
                document.pop(key, None)
            document.pop("format_version", None)
        return document

    @property
    def needs_model_judge(self) -> bool:
        """True when a criterion exists that Layer 1 cannot decide."""
        return bool(self.model_checks) or self.rubric is not None


def parse_input(value: Any) -> TestInput:
    return TestInput.model_validate(value)


def parse_criteria(value: Any) -> Criteria:
    return Criteria.model_validate(value)
