"""The versioned behavioural test format (``suncly-behavioral-suite/2``).

A suite is what a customer reviews and approves: one case per behaviour,
each with the category it evidences, deterministic assertions, an optional
rubric for criteria only a model can judge, negative cases, and the coverage
gaps the author acknowledges. Compiling a suite produces ordinary
``test_case`` records (``domain/criteria.py``, format 2), so the Runner, the
Judge and the signature treat them like any other test case.

Everything in a suite is untrusted data: inputs are sent to the agent as text
and never interpreted by Suncly; rubric text reaches the judge model as data
inside a fixed prompt, never as instructions to Suncly.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from suncly.domain.a2a import TASK_STATE_COMPLETED, TERMINAL_TASK_STATES
from suncly.domain.canonical import canonical_sha256
from suncly.domain.criteria import parse_input
from suncly.domain.errors import ContractError
from suncly.domain.models import JsonObject, TestCaseKind
from suncly.domain.policy import TestCategory

BEHAVIORAL_SUITE_FORMAT = "suncly-behavioral-suite/2"
CRITERIA_FORMAT_VERSION = 2

AssertionKind = Literal[
    "text_equals",
    "text_contains",
    "text_not_contains",
    "text_regex",
    "json_pointer_equals",
    "json_pointer_present",
    "response_schema",
    "final_state",
    "output_mode",
]


class Assertion(BaseModel):
    """A deterministic check on the final response. Decided by Layer 1, never by a model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: AssertionKind
    value: Any = None
    pointer: str | None = None
    case_sensitive: bool = False
    description: str = ""

    @model_validator(mode="after")
    def _shape(self) -> Assertion:
        needs_pointer = self.kind in ("json_pointer_equals", "json_pointer_present")
        if needs_pointer and not (self.pointer or "").startswith("/"):
            raise ValueError(f"{self.kind} needs a JSON pointer starting with '/'")
        if self.kind in ("text_equals", "text_contains", "text_not_contains", "text_regex") and (
            not isinstance(self.value, str) or not self.value
        ):
            raise ValueError(f"{self.kind} needs a non-empty string value")
        if self.kind == "final_state" and self.value not in TERMINAL_TASK_STATES:
            raise ValueError("final_state must be a terminal task state")
        if self.kind == "response_schema" and not isinstance(self.value, dict):
            raise ValueError("response_schema needs a JSON Schema object")
        if self.kind == "output_mode" and not (isinstance(self.value, str) and self.value):
            raise ValueError("output_mode needs a media type")
        return self


class RubricStatement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    text: str = Field(min_length=1, max_length=2000)


class Rubric(BaseModel):
    """What a model judge decides, as fixed statements. Versioned: a change is a new version."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    version: str = Field(min_length=1, max_length=32)
    statements: list[RubricStatement] = Field(min_length=1, max_length=20)
    pass_requires: Literal["all", "majority"] = "all"  # noqa: S105 - a rule, not a password

    def content_hash(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))


class ReferenceExample(BaseModel):
    """A customer-provided example of a good answer. Context for the judge, never a pass."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    input: str = Field(min_length=1, max_length=8000)
    expected_output: str = Field(min_length=1, max_length=8000)
    note: str = ""


class SandboxVerification(BaseModel):
    """Independent check of sandbox state after an action, for action agents.

    The Runner performs ``GET url`` after the run, on the same origin as the
    agent endpoint, and compares the JSON at ``pointer`` with ``expected``. The
    agent's own claim that it acted is never evidence of the action.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str = Field(min_length=1, max_length=2048)
    pointer: str = Field(pattern=r"^/")
    expected: Any
    description: str = ""


class BehavioralCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    title: str = Field(min_length=1, max_length=200)
    skill_id: str | None = None
    kind: TestCaseKind = TestCaseKind.SKILL
    category: TestCategory
    input: JsonObject
    expected_output: str | None = Field(default=None, max_length=8000)
    assertions: list[Assertion] = Field(default_factory=list, max_length=50)
    rubric: Rubric | None = None
    reference_examples: list[ReferenceExample] = Field(default_factory=list, max_length=20)
    negative: bool = False
    """A negative or failure case: the agent is expected to refuse, fail or reject."""
    latency_limit_ms: int = Field(ge=1)
    final_state: str = TASK_STATE_COMPLETED
    sandbox_verification: SandboxVerification | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _valid(self) -> BehavioralCase:
        if self.kind is TestCaseKind.SKILL and not (self.skill_id or "").strip():
            raise ValueError("a case of kind skill names its skill_id")
        if self.final_state not in TERMINAL_TASK_STATES:
            raise ValueError("final_state must be a terminal task state")
        if not self.assertions and self.rubric is None and self.expected_output is None:
            raise ValueError(
                "a case needs at least one assertion, a rubric or an expected_output; "
                "a valid response alone proves nothing about correctness"
            )
        try:
            parse_input(self.input)
        except ValidationError as exc:
            raise ValueError(f"input: {exc.errors()[0]['msg']}") from exc
        return self


class CoverageGap(BaseModel):
    """What the suite knowingly does not cover. Listed in every report."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: TestCategory
    skill_id: str | None = None
    reason: str = Field(min_length=1, max_length=1000)


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    drafter: str = Field(min_length=1)
    model: str | None = None
    model_parameters: JsonObject = Field(default_factory=dict)
    generated_at: str | None = None
    usage: JsonObject = Field(default_factory=dict)


class BehavioralSuite(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    format: str = Field(default=BEHAVIORAL_SUITE_FORMAT, pattern=r"^suncly-behavioral-suite/2$")
    suite_version: str = Field(min_length=1, max_length=32)
    card_hash: str = Field(min_length=1)
    agent_name: str = ""
    cases: list[BehavioralCase] = Field(min_length=1, max_length=500)
    coverage_gaps: list[CoverageGap] = Field(default_factory=list)
    provenance: Provenance | None = None
    notes: str = ""

    @model_validator(mode="after")
    def _unique_ids(self) -> BehavioralSuite:
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("case ids must be unique within a suite")
        return self

    def content_hash(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))

    def categories(self) -> dict[TestCategory, int]:
        counts: dict[TestCategory, int] = {}
        for case in self.cases:
            counts[case.category] = counts.get(case.category, 0) + 1
        return counts


def parse_behavioral_suite(text: str) -> BehavioralSuite:
    try:
        loaded: Any = json.loads(text)
    except ValueError as exc:
        raise ContractError(
            "The behavioural suite is not valid JSON.", f"The parser reported: {exc}."
        ) from exc
    try:
        return BehavioralSuite.model_validate(loaded)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in error['loc']) or '<root>'}: {error['msg']}"
            for error in exc.errors()[:8]
        )
        raise ContractError(
            "The behavioural suite does not match format suncly-behavioral-suite/2.",
            f"Validation reported: {problems}.",
            "See docs/API.md, section 'Behavioural suite'.",
        ) from exc


def render_behavioral_suite(suite: BehavioralSuite) -> str:
    return json.dumps(suite.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"


def criteria_for_case(case: BehavioralCase, output_modes: list[str] | None) -> JsonObject:
    """The ``test_case.criteria`` document (format 2) that carries this case to the Judge."""
    criteria: JsonObject = {
        "format_version": CRITERIA_FORMAT_VERSION,
        "suite_case_id": case.id,
        "category": case.category.value,
        "final_state": case.final_state,
        "latency_limit_ms": case.latency_limit_ms,
        "response_present": not case.negative,
        "output_modes": output_modes,
        "required_fields": [],
        "model_checks": [],
        "accept_direct_message": False,
        "assertions": [a.model_dump(mode="json", exclude_none=True) for a in case.assertions],
        "negative": case.negative,
    }
    if case.expected_output is not None:
        criteria["expected_output"] = case.expected_output
    if case.rubric is not None:
        criteria["rubric"] = case.rubric.model_dump(mode="json")
    if case.reference_examples:
        criteria["reference_examples"] = [
            e.model_dump(mode="json", exclude_none=True) for e in case.reference_examples
        ]
    if case.sandbox_verification is not None:
        criteria["sandbox_verification"] = case.sandbox_verification.model_dump(mode="json")
    return criteria
