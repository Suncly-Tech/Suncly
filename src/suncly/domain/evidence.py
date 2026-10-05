"""Aggregates of evidence shared by the Policy engine, the Report adapter and the verifier.

None of these is an entity. They combine the seven entities with facts that
only exist while an attestation runs (how many runs were planned, which were
never executed, what the card re-fetch found) and with the derived
"what was NOT tested" list (schema §8, DR-007).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from suncly.domain.card import ParsedCard
from suncly.domain.models import (
    Agent,
    Attestation,
    CardVersion,
    Contract,
    Decision,
    JsonObject,
    Run,
    TestCase,
    TestCaseKind,
)


class TestCaseResult(BaseModel):
    """Per-test-case aggregated results (schema §11). ``inconclusive`` is never a pass."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    test_case_id: UUID
    skill_id: str | None
    kind: TestCaseKind
    pass_count: int = Field(ge=0)
    fail_count: int = Field(ge=0)
    inconclusive_count: int = Field(ge=0)

    @property
    def total(self) -> int:
        return self.pass_count + self.fail_count + self.inconclusive_count

    def to_payload(self) -> JsonObject:
        """The form that enters the signature payload: the schema's verdict names as keys."""
        return {
            "test_case_id": str(self.test_case_id),
            "skill_id": self.skill_id,
            "kind": self.kind.value,
            "pass": self.pass_count,
            "fail": self.fail_count,
            "inconclusive": self.inconclusive_count,
        }


class NotExecutedReason(StrEnum):
    BUDGET = "budget"
    """The budget cap stopped the run before it started (schema §11, DR-005)."""
    RUNNER_CRASHED = "runner_crashed"
    """The Runner produced no result even after retries."""
    WITHHELD = "withheld"
    """Redaction failed inside the Runner; the transcript was withheld (OQ-A11)."""
    UNKNOWN_OUTCOME = "unknown_outcome"
    """The request may have reached the sandbox but no result was persisted (the Runner or the
    worker died in between). The sandbox was not declared idempotent, so it was not repeated."""
    CANCELLED = "cancelled"
    """Cancellation was requested before this run started."""


class NotExecutedRun(BaseModel):
    """A planned run that was never recorded, and why."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    test_case_id: UUID
    attempt: int = Field(ge=1)
    reason: NotExecutedReason
    detail: str = ""


class CardRecheck(BaseModel):
    """What the Orchestrator found when it re-fetched the card at the end (schema §11)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: Literal["unchanged", "changed", "unavailable", "not_performed"]
    card_hash: str | None = None
    detail: str = ""


class NotTestedItem(BaseModel):
    """One line of the report's "What was NOT tested" section (DR-007)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: str
    detail: str


class RunEvidence(BaseModel):
    """A run with its stored evidence document (transcript plus judgement) and its hash."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run: Run
    document: JsonObject
    document_hash: str


class EvidenceBundle(BaseModel):
    """Everything known about one attestation, assembled once and rendered many ways."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    generated_at: AwareDatetime
    agent: Agent
    card_version: CardVersion
    parsed_card: ParsedCard
    card_url: str | None
    contract: Contract
    test_cases: list[TestCase]
    attestation: Attestation
    runs: list[RunEvidence]
    decisions: list[Decision]
    results: list[TestCaseResult]
    planned_runs: int | None
    not_executed: list[NotExecutedRun]
    card_recheck: CardRecheck
    not_tested: list[NotTestedItem]
    sandbox_declared: bool
    drafter_name: str | None
    signer_public_key: str | None
    """Base64url, no padding; lets a reader verify without access to the deployment's keys."""
    signature_payload: JsonObject | None
    proposals: list[str]
    """Open-question proposals in effect for this attestation (docs/IMPLEMENTATION_NOTES.md)."""
    policy_evaluation: JsonObject | None = None
    """What the Policy engine concluded and why (``domain/policy.py``), when a policy applied."""
    decision_notes: list[JsonObject] = Field(default_factory=list)
    """Rationales of human decisions, in decision order."""
    external_results: list[JsonObject] = Field(default_factory=list)
    """Normalized results of external tools (the A2A TCK, Promptfoo), with their versions."""

    @property
    def transcript_hashes(self) -> dict[str, str]:
        return {str(r.run.id): r.document_hash for r in self.runs}

    def test_case(self, test_case_id: UUID) -> TestCase | None:
        return next((tc for tc in self.test_cases if tc.id == test_case_id), None)

    @property
    def policy_decision(self) -> Decision | None:
        """The first decision, made by the policy (invariant 11)."""
        return self.decisions[0] if self.decisions else None
