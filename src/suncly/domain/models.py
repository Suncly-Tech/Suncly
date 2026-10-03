"""The seven entities of docs/DATA_MODEL.md and their enumerations.

Entity, field and enum names are exactly the schema's (SCHEMA.md §3, §11). The
invariants that need no database are enforced by the models themselves:
invariant 3 (approval fields), invariant 7 (a model verdict has a rationale),
the attestation status rules of schema §11, and the rule that a test case of
kind ``skill`` names its skill. Invariant 6, the unique run key, is enforced by
the evidence store, because one record cannot check it.

Enum members are written in upper case; their values are the schema's exact
lowercase strings.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any, NamedTuple
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

JsonObject = dict[str, Any]

#: ``decision.decided_by`` for automatic decisions (schema §11).
POLICY_DECIDED_BY = "policy"


class RiskLevel(StrEnum):
    """``agent.risk_level`` (schema §3)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ContractStatus(StrEnum):
    """``contract.status`` (schema §11)."""

    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class TestCaseKind(StrEnum):
    """``test_case.kind`` (schema §3)."""

    SKILL = "skill"
    PROBE_UNDECLARED = "probe_undeclared"
    PROBE_INJECTION = "probe_injection"
    PROBE_FAILURE = "probe_failure"


class AttestationTrigger(StrEnum):
    """``attestation.trigger`` (schema §11)."""

    CI = "ci"
    SCHEDULE = "schedule"
    CARD_CHANGE = "card_change"
    MANUAL = "manual"


class AttestationStatus(StrEnum):
    """``attestation.status`` (schema §11)."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INVALIDATED = "invalidated"

    @property
    def is_final(self) -> bool:
        """True for the statuses that set ``finished_at`` (schema §11)."""
        return self in FINAL_ATTESTATION_STATUSES


FINAL_ATTESTATION_STATUSES = frozenset(
    {
        AttestationStatus.COMPLETED,
        AttestationStatus.FAILED,
        AttestationStatus.CANCELLED,
        AttestationStatus.INVALIDATED,
    }
)

#: Statuses that never get a decision: schema §11 for failed and invalidated,
#: proposed for cancelled (OQ-D6).
UNDECIDED_ATTESTATION_STATUSES = frozenset(
    {AttestationStatus.FAILED, AttestationStatus.INVALIDATED, AttestationStatus.CANCELLED}
)


class RunVerdict(StrEnum):
    """``run.verdict`` (schema §2, §3). ``inconclusive`` is never counted as a pass."""

    PASS = "pass"  # noqa: S105 - a verdict, not a password
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class JudgeLayer(StrEnum):
    """``run.judge_layer`` (schema §11): the layer that decided the verdict."""

    DETERMINISTIC = "deterministic"
    MODEL = "model"


class DecisionOutcome(StrEnum):
    """``decision.outcome`` (schema §3). ``flag`` is "flag for human review" (schema §2)."""

    APPROVE = "approve"
    FLAG = "flag"
    BLOCK = "block"


class Entity(BaseModel):
    """Base for the seven entities: immutable records with no extra fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Agent(Entity):
    """An agent under attestation, its owner and its risk level (schema §3)."""

    id: UUID
    name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    risk_level: RiskLevel


class CardVersion(Entity):
    """One fetched Agent Card, identified by its hash (schema §3)."""

    id: UUID
    agent_id: UUID
    card_hash: str = Field(min_length=1)
    raw_json: str
    fetched_at: AwareDatetime


class Contract(Entity):
    """A versioned set of test cases for one card version (schema §3, §11)."""

    id: UUID
    card_version_id: UUID
    version: int = Field(ge=1)
    status: ContractStatus
    created_at: AwareDatetime
    approved_by: str | None = None
    approved_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def _approval_fields_match_status(self) -> Contract:
        """Invariant 3 (schema §11): approval fields are null until approved, then both set."""
        has_both = self.approved_by is not None and self.approved_at is not None
        has_none = self.approved_by is None and self.approved_at is None
        if self.status in (ContractStatus.DRAFT, ContractStatus.REJECTED) and not has_none:
            raise ValueError(
                "approved_by and approved_at are null until the contract is approved (invariant 3)"
            )
        if self.status in (ContractStatus.APPROVED, ContractStatus.SUPERSEDED) and not has_both:
            raise ValueError("an approved contract has approved_by and approved_at (schema §11)")
        if self.approved_by is not None and not self.approved_by.strip():
            raise ValueError("approved_by must not be blank")
        return self

    @property
    def is_approved(self) -> bool:
        return self.status is ContractStatus.APPROVED


class TestCase(Entity):
    """One test in a contract, for a declared skill or a probe (schema §3)."""

    id: UUID
    contract_id: UUID
    skill_id: str | None
    input: JsonObject
    criteria: JsonObject
    kind: TestCaseKind

    @model_validator(mode="after")
    def _skill_test_case_names_its_skill(self) -> TestCase:
        """A test case of kind ``skill`` exercises a declared skill (db/README.md, derived)."""
        if self.kind is TestCaseKind.SKILL and not (self.skill_id or "").strip():
            raise ValueError("a test case of kind skill must have a skill_id")
        return self


class Attestation(Entity):
    """One execution of a contract against the agent (schema §3, §11)."""

    id: UUID
    contract_id: UUID
    card_version_id: UUID
    trigger: AttestationTrigger
    status: AttestationStatus
    started_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    budget_limit: Decimal = Field(ge=0)
    cost_total: Decimal = Field(ge=0)
    signature: str | None = None
    signing_key_id: str | None = None

    @model_validator(mode="after")
    def _status_rules(self) -> Attestation:
        """Schema §11: finished_at marks a final status; signature fields travel together."""
        if (self.finished_at is not None) != self.status.is_final:
            raise ValueError(
                "finished_at is set exactly when the attestation is completed, failed, "
                "cancelled or invalidated (schema §11)"
            )
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        if (self.signature is None) != (self.signing_key_id is None):
            raise ValueError("signature and signing_key_id are set together (schema §11)")
        if self.status is AttestationStatus.COMPLETED and self.signature is None:
            raise ValueError("a completed attestation is signed (invariant 13)")
        return self

    @property
    def is_signed(self) -> bool:
        return self.signature is not None


class RunKey(NamedTuple):
    """The deterministic run key (DR-001, invariant 6, OQ-D3)."""

    attestation_id: UUID
    test_case_id: UUID
    attempt: int


class Run(Entity):
    """One execution of one test case (schema §3, §11). Append-only (schema §8)."""

    id: UUID
    attestation_id: UUID
    test_case_id: UUID
    attempt: int = Field(ge=1)
    verdict: RunVerdict
    judge_layer: JudgeLayer
    rationale: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    cost: Decimal = Field(ge=0)
    transcript_ref: str = Field(min_length=1)
    started_at: AwareDatetime
    finished_at: AwareDatetime

    @model_validator(mode="after")
    def _model_verdict_has_rationale(self) -> Run:
        """Invariant 7 (schema §2): a model verdict is never stored without its rationale."""
        if self.judge_layer is JudgeLayer.MODEL and not (self.rationale or "").strip():
            raise ValueError("rationale is required when judge_layer is model (invariant 7)")
        if self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        return self

    @property
    def key(self) -> RunKey:
        return RunKey(self.attestation_id, self.test_case_id, self.attempt)


class Decision(Entity):
    """A policy outcome for an attestation (schema §3, §11). Append-only."""

    id: UUID
    attestation_id: UUID
    outcome: DecisionOutcome
    policy_version: str = Field(min_length=1)
    decided_by: str = Field(min_length=1)
    decided_at: AwareDatetime

    @model_validator(mode="after")
    def _decided_by_not_blank(self) -> Decision:
        if not self.decided_by.strip():
            raise ValueError("decided_by must not be blank")
        return self

    @property
    def is_automatic(self) -> bool:
        return self.decided_by == POLICY_DECIDED_BY
