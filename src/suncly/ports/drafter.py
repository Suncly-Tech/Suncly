"""Drafting a contract from an Agent Card (schema §2: Contract builder).

The deterministic drafter of this version and the model-based Contract builder
of stage 2 both implement ``ContractDrafter``, so callers never change.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from suncly.domain.card import AgentCard
from suncly.domain.models import JsonObject, TestCaseKind


class DraftTestCase(BaseModel):
    """A test case before it has an id or a contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    skill_id: str | None
    input: JsonObject
    criteria: JsonObject
    kind: TestCaseKind


class NotTestableSkill(BaseModel):
    """A declared skill the drafter could not write a test case for, and why."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    skill_id: str
    reason: str


class Draft(BaseModel):
    """The drafter's output: test cases, and the skills it had to leave out."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    test_cases: list[DraftTestCase] = Field(default_factory=list)
    not_testable: list[NotTestableSkill] = Field(default_factory=list)


class DraftSettings(BaseModel):
    """What the drafter needs besides the card."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    latency_limit_ms: int = Field(ge=1)
    max_test_cases_per_skill: int = Field(ge=1)


class ContractDrafter(Protocol):
    """Builds a draft contract from a card. A human approves it afterwards."""

    name: str

    def draft(self, card: AgentCard, settings: DraftSettings) -> Draft: ...
