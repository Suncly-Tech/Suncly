"""The configured Policy engine: the customer's numbers, never Suncly's (POLICY.md)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from suncly.domain.evidence import TestCaseResult
from suncly.domain.models import DecisionOutcome, RiskLevel, TestCaseKind
from suncly.domain.policy import (
    CategoryRequirement,
    FreshnessRule,
    InconclusiveHandling,
    PolicyConfiguration,
    RegressionRule,
    RiskThresholds,
    TestCaseVerdict,
    TestCategory,
    evaluate_policy,
    evaluate_test_case,
)

NOW = datetime(2026, 10, 5, tzinfo=UTC)


def result(p: int = 0, f: int = 0, i: int = 0, test_case_id: UUID | None = None) -> TestCaseResult:
    return TestCaseResult(
        test_case_id=test_case_id or uuid4(),
        skill_id="s",
        kind=TestCaseKind.SKILL,
        pass_count=p,
        fail_count=f,
        inconclusive_count=i,
    )


def policy(**overrides: object) -> PolicyConfiguration:
    base: dict[str, object] = {
        "policy_version": "v1",
        "thresholds": {
            RiskLevel.LOW: RiskThresholds(min_pass_ratio=0.9),
            RiskLevel.MEDIUM: RiskThresholds(min_pass_ratio=0.95),
            RiskLevel.HIGH: RiskThresholds(min_pass_ratio=1.0, require_human_signoff=True),
        },
    }
    base.update(overrides)
    return PolicyConfiguration.model_validate(base)


def evaluate(
    results: list[TestCaseResult],
    risk: RiskLevel = RiskLevel.LOW,
    config: PolicyConfiguration | None = None,
    baseline: dict[UUID, TestCaseResult] | None = None,
    categories: dict[UUID, TestCategory] | None = None,
    baseline_at: datetime | None = None,
) -> DecisionOutcome:
    return evaluate_policy(
        policy=config,
        risk_level=risk,
        results=results,
        categories=categories or {},
        baseline=baseline,
        baseline_at=baseline_at,
        now=NOW,
    ).outcome


def test_without_a_policy_the_outcome_is_always_flag() -> None:
    for results in ([], [result(p=100)], [result(f=100)]):
        evaluation = evaluate_policy(
            policy=None,
            risk_level=RiskLevel.LOW,
            results=results,
            categories={},
            baseline=None,
            baseline_at=None,
            now=NOW,
        )
        assert evaluation.outcome is DecisionOutcome.FLAG
        assert evaluation.policy_version == "unconfigured" and evaluation.requires_human


def test_low_risk_passing_results_are_approved_under_the_customers_threshold() -> None:
    assert evaluate([result(p=19, f=1)], config=policy()) is DecisionOutcome.APPROVE
    assert evaluate([result(p=10)], config=policy()) is DecisionOutcome.APPROVE


def test_failing_results_block_or_flag_as_the_policy_says() -> None:
    assert evaluate([result(p=5, f=5)], config=policy()) is DecisionOutcome.BLOCK
    lenient = policy(
        thresholds={RiskLevel.LOW: RiskThresholds(min_pass_ratio=0.9, block_on_fail=False)}
    )
    assert evaluate([result(p=5, f=5)], config=lenient) is DecisionOutcome.FLAG


def test_high_risk_never_approves_automatically() -> None:
    evaluation = evaluate_policy(
        policy=policy(),
        risk_level=RiskLevel.HIGH,
        results=[result(p=50)],
        categories={},
        baseline=None,
        baseline_at=None,
        now=NOW,
    )
    assert evaluation.outcome is DecisionOutcome.FLAG and evaluation.requires_human
    assert any("human sign-off" in reason for reason in evaluation.reasons)
    with pytest.raises(ValidationError, match="human sign-off"):
        policy(high_risk_requires_human=False)


def test_a_risk_level_without_thresholds_flags() -> None:
    config = policy(thresholds={RiskLevel.LOW: RiskThresholds(min_pass_ratio=0.5)})
    assert evaluate([result(p=10)], risk=RiskLevel.MEDIUM, config=config) is DecisionOutcome.FLAG


def test_borderline_results_flag() -> None:
    # 18/20 = 0.90: at the threshold but inside the 0.05 margin -> borderline.
    margin = policy(
        thresholds={RiskLevel.LOW: RiskThresholds(min_pass_ratio=0.9, borderline_margin=0.05)}
    )
    assert evaluate([result(p=18, f=2)], config=margin) is DecisionOutcome.FLAG
    # 19/20 = 0.95 sits exactly on the margin's ceiling: a pass, not a float rounding accident.
    assert evaluate([result(p=19, f=1)], config=margin) is DecisionOutcome.APPROVE
    thresholds = RiskThresholds(min_pass_ratio=0.5, max_inconclusive_ratio=0.1)
    evaluation = evaluate_test_case(
        result(p=8, i=2),
        TestCategory.SEMANTIC,
        thresholds,
        InconclusiveHandling.COUNT_AS_FAIL,
        None,
        None,
    )
    assert evaluation.verdict is TestCaseVerdict.BORDERLINE


def test_inconclusive_is_never_a_pass_under_any_handling() -> None:
    counted = policy(inconclusive=InconclusiveHandling.COUNT_AS_FAIL)
    assert evaluate([result(p=9, i=1)], config=counted) is DecisionOutcome.APPROVE
    assert evaluate([result(p=8, i=2)], config=counted) is DecisionOutcome.BLOCK
    flagging = policy(inconclusive=InconclusiveHandling.FLAG)
    assert evaluate([result(p=99, i=1)], config=flagging) is DecisionOutcome.FLAG
    excluded = policy(inconclusive=InconclusiveHandling.EXCLUDE)
    assert evaluate([result(p=9, i=50)], config=excluded) is DecisionOutcome.APPROVE
    only_inconclusive = evaluate_test_case(
        result(i=5),
        TestCategory.SEMANTIC,
        RiskThresholds(min_pass_ratio=0.5),
        InconclusiveHandling.EXCLUDE,
        None,
        None,
    )
    assert only_inconclusive.verdict is TestCaseVerdict.NO_RUNS
    assert evaluate([result(i=5)], config=excluded) is DecisionOutcome.FLAG


def test_a_drop_against_the_baseline_flags_even_when_passing() -> None:
    test_case_id = uuid4()
    config = policy(
        regression=RegressionRule(baseline="previous_completed", max_pass_ratio_drop=0.05)
    )
    current = [result(p=90, f=10, test_case_id=test_case_id)]
    baseline = {test_case_id: result(p=100, test_case_id=test_case_id)}
    evaluation = evaluate_policy(
        policy=config,
        risk_level=RiskLevel.LOW,
        results=current,
        categories={},
        baseline=baseline,
        baseline_at=NOW - timedelta(days=1),
        now=NOW,
    )
    assert evaluation.outcome is DecisionOutcome.FLAG
    assert evaluation.test_cases[0].dropped
    stable = {test_case_id: result(p=92, f=8, test_case_id=test_case_id)}
    assert evaluate(current, config=config, baseline=stable) is DecisionOutcome.APPROVE


def test_required_categories_and_freshness_are_enforced() -> None:
    semantic = uuid4()
    config = policy(
        required_categories=[
            CategoryRequirement(category=TestCategory.SECURITY, min_test_cases=1),
        ],
        freshness=FreshnessRule(max_evidence_age_days=7),
    )
    evaluation = evaluate_policy(
        policy=config,
        risk_level=RiskLevel.LOW,
        results=[result(p=10, test_case_id=semantic)],
        categories={semantic: TestCategory.SEMANTIC},
        baseline=None,
        baseline_at=NOW - timedelta(days=30),
        now=NOW,
    )
    assert evaluation.outcome is DecisionOutcome.FLAG
    assert any("security" in reason for reason in evaluation.reasons)
    assert any("day(s) old" in reason for reason in evaluation.reasons)
    security = uuid4()
    covered = evaluate_policy(
        policy=config,
        risk_level=RiskLevel.LOW,
        results=[result(p=10, test_case_id=semantic), result(p=10, test_case_id=security)],
        categories={semantic: TestCategory.SEMANTIC, security: TestCategory.SECURITY},
        baseline=None,
        baseline_at=None,
        now=NOW,
    )
    assert covered.outcome is DecisionOutcome.APPROVE


def test_the_policy_is_content_addressed_and_immutable_by_version() -> None:
    first, second = policy(), policy()
    assert first.content_hash() == second.content_hash()
    assert policy(policy_version="v2").content_hash() != first.content_hash()
    with pytest.raises(ValidationError):
        PolicyConfiguration.model_validate({"policy_version": "v1", "thresholds": {}, "extra": 1})
