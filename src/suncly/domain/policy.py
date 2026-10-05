"""Versioned customer policy configuration and its evaluation (SCHEMA.md §5, POLICY.md).

Nothing here invents a number. A policy carries the thresholds the customer
wrote; without a policy the only outcome is ``flag`` (OQ-PO5). The
configuration is content-addressed: ``policy_version`` is the customer's
label, ``content_hash`` is what the signature binds.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from suncly.domain.canonical import canonical_sha256
from suncly.domain.evidence import TestCaseResult
from suncly.domain.models import DecisionOutcome, RiskLevel

JsonObject = dict[str, Any]

POLICY_FORMAT = "suncly-policy/1"


class TestCategory(StrEnum):
    """The result categories every check and test case belongs to."""

    PROTOCOL = "protocol"
    """Protocol compatibility: well-formed A2A, task states, bindings, the TCK."""
    SEMANTIC = "semantic"
    """Task correctness: expected outputs, deterministic assertions, rubrics."""
    SECURITY = "security"
    """Security behaviour: injection, undeclared behaviour, data handling, Promptfoo packs."""
    OPERATIONAL = "operational"
    """Latency, reliability, availability."""


class InconclusiveHandling(StrEnum):
    COUNT_AS_FAIL = "count_as_fail"
    """Inconclusive runs count against the test case like failures (never as passes)."""
    FLAG = "flag"
    """Any inconclusive run flags the attestation for a human."""
    EXCLUDE = "exclude"
    """Inconclusive runs are left out of the ratio; they still never count as passes."""


class RiskThresholds(BaseModel):
    """Thresholds for one risk level. Every number is the customer's."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_pass_ratio: float = Field(ge=0.0, le=1.0)
    """Minimum share of runs per test case that passed; below it the test case fails."""
    borderline_margin: float = Field(default=0.0, ge=0.0, le=1.0)
    """A test case within this margin above ``min_pass_ratio`` is borderline: ``flag``."""
    max_inconclusive_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    """Above this share of inconclusive runs per test case the result is borderline."""
    require_human_signoff: bool = False
    """Never approve automatically at this risk level (SCHEMA.md §5: high)."""
    block_on_fail: bool = True
    """A failing test case without a drop blocks; otherwise it flags (OQ-PO4)."""


class CategoryRequirement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    category: TestCategory
    min_test_cases: int = Field(ge=1)
    """Minimum number of test cases of this category the contract must hold."""


class RegressionRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline: str = Field(pattern=r"^(previous_completed|last_approved)$")
    max_pass_ratio_drop: float = Field(ge=0.0, le=1.0)
    """A test case whose pass ratio dropped by more than this against the baseline is a drop."""


class FreshnessRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_evidence_age_days: int = Field(ge=1)
    """An attestation older than this is no longer acceptable under the policy."""


class PolicyConfiguration(BaseModel):
    """The customer's policy, one immutable version at a time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    format: str = Field(default=POLICY_FORMAT, pattern=r"^suncly-policy/1$")
    policy_version: str = Field(min_length=1, max_length=64)
    thresholds: dict[RiskLevel, RiskThresholds]
    required_categories: list[CategoryRequirement] = Field(default_factory=list)
    inconclusive: InconclusiveHandling = InconclusiveHandling.COUNT_AS_FAIL
    regression: RegressionRule | None = None
    freshness: FreshnessRule | None = None
    high_risk_requires_human: bool = True
    """SCHEMA.md §5: human sign-off every time for high risk. Cannot be turned off."""

    @model_validator(mode="after")
    def _high_risk_always_human(self) -> PolicyConfiguration:
        if not self.high_risk_requires_human:
            raise ValueError("high-risk agents always need human sign-off (SCHEMA.md §5)")
        return self

    def content_hash(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))


class PolicyRecord(BaseModel):
    """A stored policy version for one organization. Append-only."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    organization_id: UUID
    policy_version: str
    content_hash: str
    configuration: PolicyConfiguration
    created_at: AwareDatetime
    created_by: str


class TestCaseVerdict(StrEnum):
    PASS = "pass"  # noqa: S105 - a verdict, not a password
    BORDERLINE = "borderline"
    FAIL = "fail"
    NO_RUNS = "no_runs"


class TestCaseEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    test_case_id: UUID
    category: TestCategory
    verdict: TestCaseVerdict
    pass_ratio: float | None
    inconclusive_ratio: float
    dropped: bool = False
    detail: str = ""


class PolicyEvaluation(BaseModel):
    """What the Policy engine concluded, and every reason it gives."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: DecisionOutcome
    policy_version: str
    content_hash: str | None
    reasons: list[str]
    test_cases: list[TestCaseEvaluation] = Field(default_factory=list)
    requires_human: bool = False


_PRECISION = 9
"""Ratios are compared at nine decimals so 19/20 is not "below" 0.9 + 0.05."""


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, _PRECISION)


def evaluate_test_case(
    result: TestCaseResult,
    category: TestCategory,
    thresholds: RiskThresholds,
    handling: InconclusiveHandling,
    baseline: TestCaseResult | None,
    regression: RegressionRule | None,
) -> TestCaseEvaluation:
    """Pure evaluation of one test case under one risk level's thresholds."""
    total = result.total
    inconclusive_ratio = (result.inconclusive_count / total) if total else 0.0
    if handling is InconclusiveHandling.EXCLUDE:
        denominator = result.pass_count + result.fail_count
    else:
        denominator = total
    pass_ratio = _ratio(result.pass_count, denominator)
    dropped = False
    if baseline is not None and regression is not None and baseline.total:
        base_denominator = (
            baseline.pass_count + baseline.fail_count
            if handling is InconclusiveHandling.EXCLUDE
            else baseline.total
        )
        base_ratio = _ratio(baseline.pass_count, base_denominator)
        if base_ratio is not None and pass_ratio is not None:
            dropped = round(base_ratio - pass_ratio, _PRECISION) > regression.max_pass_ratio_drop
    if pass_ratio is None:
        return TestCaseEvaluation(
            test_case_id=result.test_case_id,
            category=category,
            verdict=TestCaseVerdict.NO_RUNS,
            pass_ratio=None,
            inconclusive_ratio=inconclusive_ratio,
            dropped=dropped,
            detail="no decidable run",
        )
    borderline_ceiling = round(thresholds.min_pass_ratio + thresholds.borderline_margin, _PRECISION)
    if pass_ratio < thresholds.min_pass_ratio:
        verdict = TestCaseVerdict.FAIL
        detail = f"pass ratio {pass_ratio:.3f} below min_pass_ratio {thresholds.min_pass_ratio}"
    elif pass_ratio < borderline_ceiling:
        verdict = TestCaseVerdict.BORDERLINE
        detail = f"pass ratio {pass_ratio:.3f} within the borderline margin"
    elif inconclusive_ratio > thresholds.max_inconclusive_ratio:
        verdict = TestCaseVerdict.BORDERLINE
        detail = f"inconclusive ratio {inconclusive_ratio:.3f} above max_inconclusive_ratio"
    elif handling is InconclusiveHandling.FLAG and result.inconclusive_count:
        verdict = TestCaseVerdict.BORDERLINE
        detail = f"{result.inconclusive_count} inconclusive run(s) under inconclusive=flag"
    else:
        verdict = TestCaseVerdict.PASS
        detail = f"pass ratio {pass_ratio:.3f}"
    if dropped:
        detail += "; dropped against the baseline"
    return TestCaseEvaluation(
        test_case_id=result.test_case_id,
        category=category,
        verdict=verdict,
        pass_ratio=pass_ratio,
        inconclusive_ratio=inconclusive_ratio,
        dropped=dropped,
        detail=detail,
    )


def evaluate_policy(
    *,
    policy: PolicyConfiguration | None,
    risk_level: RiskLevel,
    results: list[TestCaseResult],
    categories: dict[UUID, TestCategory],
    baseline: dict[UUID, TestCaseResult] | None,
    baseline_at: datetime | None,
    now: datetime,
) -> PolicyEvaluation:
    """The decision table of POLICY.md, with the customer's numbers. Pure.

    Without a policy the outcome is ``flag`` with ``policy_version``
    ``unconfigured`` (OQ-PO5). ``approve`` needs every test case to pass, every
    required category to be covered, no drop, no borderline, and a risk level
    that allows automatic approval.
    """
    if policy is None:
        return PolicyEvaluation(
            outcome=DecisionOutcome.FLAG,
            policy_version="unconfigured",
            content_hash=None,
            reasons=["no policy is configured for this organization; a human must review"],
            requires_human=True,
        )
    thresholds = policy.thresholds.get(risk_level)
    reasons: list[str] = []
    if thresholds is None:
        return PolicyEvaluation(
            outcome=DecisionOutcome.FLAG,
            policy_version=policy.policy_version,
            content_hash=policy.content_hash(),
            reasons=[f"the policy defines no thresholds for risk level {risk_level.value}"],
            requires_human=True,
        )
    evaluations = [
        evaluate_test_case(
            result,
            categories.get(result.test_case_id, TestCategory.SEMANTIC),
            thresholds,
            policy.inconclusive,
            (baseline or {}).get(result.test_case_id),
            policy.regression,
        )
        for result in results
    ]
    counts: dict[TestCategory, int] = {}
    for evaluation in evaluations:
        counts[evaluation.category] = counts.get(evaluation.category, 0) + 1
    coverage_missing = [
        requirement
        for requirement in policy.required_categories
        if counts.get(requirement.category, 0) < requirement.min_test_cases
    ]
    for requirement in coverage_missing:
        reasons.append(
            f"category {requirement.category.value} has {counts.get(requirement.category, 0)} "
            f"test case(s); the policy requires at least {requirement.min_test_cases}"
        )
    if policy.freshness is not None and baseline_at is not None:
        age = now - baseline_at
        if age > timedelta(days=policy.freshness.max_evidence_age_days):
            reasons.append(
                f"the baseline evidence is {age.days} day(s) old; the policy accepts at most "
                f"{policy.freshness.max_evidence_age_days}"
            )
    failed = [e for e in evaluations if e.verdict is TestCaseVerdict.FAIL]
    borderline = [
        e for e in evaluations if e.verdict in (TestCaseVerdict.BORDERLINE, TestCaseVerdict.NO_RUNS)
    ]
    dropped = [e for e in evaluations if e.dropped]
    for evaluation in failed:
        reasons.append(f"test case {evaluation.test_case_id}: {evaluation.detail}")
    for evaluation in borderline:
        reasons.append(f"test case {evaluation.test_case_id}: borderline, {evaluation.detail}")
    for evaluation in dropped:
        reasons.append(f"test case {evaluation.test_case_id}: dropping results")
    requires_human = (
        risk_level is RiskLevel.HIGH
        or thresholds.require_human_signoff
        or bool(dropped)
        or bool(borderline)
        or bool(coverage_missing)
    )
    if not results:
        reasons.append("no test case results to decide on")
        requires_human = True
    if dropped or borderline or coverage_missing or not results:
        outcome = DecisionOutcome.FLAG
    elif failed:
        outcome = DecisionOutcome.BLOCK if thresholds.block_on_fail else DecisionOutcome.FLAG
        if risk_level is RiskLevel.HIGH and not thresholds.block_on_fail:
            outcome = DecisionOutcome.FLAG
    elif requires_human:
        outcome = DecisionOutcome.FLAG
        reasons.append(
            "human sign-off is required at this risk level"
            if risk_level is RiskLevel.HIGH or thresholds.require_human_signoff
            else "human review is required"
        )
    else:
        outcome = DecisionOutcome.APPROVE
        reasons.append("every test case met the policy thresholds; no drop, nothing borderline")
    return PolicyEvaluation(
        outcome=outcome,
        policy_version=policy.policy_version,
        content_hash=policy.content_hash(),
        reasons=reasons,
        test_cases=evaluations,
        requires_human=requires_human and outcome is not DecisionOutcome.APPROVE,
    )
