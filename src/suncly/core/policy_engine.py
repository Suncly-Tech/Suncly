"""The Policy engine (schema §2, §4 step 6, §11).

It aggregates run results per test case (the only place that does), applies
the customer's policy, writes the decision, and signs the attestation with
payload version 2. Without a policy configuration the only outcome is
``flag`` (POLICY.md, OQ-PO5). The engine contains no numeric threshold of
its own: every number comes from the policy the customer wrote.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from suncly.core import integrity, signing
from suncly.domain.evidence import TestCaseResult
from suncly.domain.models import (
    POLICY_DECIDED_BY,
    Attestation,
    AttestationStatus,
    Contract,
    Decision,
    JsonObject,
    RiskLevel,
    Run,
    RunVerdict,
    TestCase,
)
from suncly.domain.policy import (
    ExternalToolSummary,
    PolicyConfiguration,
    PolicyEvaluation,
    TestCategory,
    evaluate_policy,
)
from suncly.ports.clock import Clock, IdGenerator
from suncly.ports.signer import Signer
from suncly.ports.store import EvidenceStore

#: ``decision.policy_version`` while no policy configuration exists (OQ-PO5, placeholder).
POLICY_VERSION_UNCONFIGURED = "unconfigured"

#: The one sentence every surface prints with a flag decision made without a policy.
FLAG_EXPLANATION = "No policy is configured, so a human must review this result."


def aggregate(test_cases: Sequence[TestCase], runs: Iterable[Run]) -> list[TestCaseResult]:
    """Per-test-case counts of pass, fail and inconclusive. Inconclusive is never a pass."""
    counts: dict[tuple[object, RunVerdict], int] = Counter()
    for run in runs:
        counts[(run.test_case_id, run.verdict)] += 1
    return [
        TestCaseResult(
            test_case_id=tc.id,
            skill_id=tc.skill_id,
            kind=tc.kind,
            pass_count=counts[(tc.id, RunVerdict.PASS)],
            fail_count=counts[(tc.id, RunVerdict.FAIL)],
            inconclusive_count=counts[(tc.id, RunVerdict.INCONCLUSIVE)],
        )
        for tc in test_cases
    ]


def categories_of(test_cases: Sequence[TestCase]) -> dict[UUID, TestCategory]:
    """The category of every test case: format 2 says it; format 1 is semantic."""
    categories: dict[UUID, TestCategory] = {}
    for tc in test_cases:
        raw = tc.criteria.get("category")
        try:
            categories[tc.id] = TestCategory(str(raw)) if raw else TestCategory.SEMANTIC
        except ValueError:
            categories[tc.id] = TestCategory.SEMANTIC
    return categories


def rubric_versions_of(test_cases: Sequence[TestCase]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for tc in test_cases:
        rubric = tc.criteria.get("rubric")
        if isinstance(rubric, dict) and rubric.get("id"):
            versions[str(rubric["id"])] = str(rubric.get("version", ""))
    return versions


@dataclass(frozen=True)
class SigningBinding:
    """Everything payload version 2 binds besides the results (``core/integrity.py``)."""

    issuer: str
    contract_content_hash: str
    suite_version: str
    judge_version: str
    environment: integrity.EnvironmentBinding
    deployment_identity: integrity.DeploymentIdentity | None
    validity: timedelta
    policy: PolicyConfiguration | None = None
    risk_level: RiskLevel = RiskLevel.HIGH
    baseline: dict[UUID, TestCaseResult] | None = None
    baseline_at: datetime | None = None
    artifact_hashes: Mapping[str, str] = field(default_factory=dict)
    reviewer: str | None = None
    external: Sequence[ExternalToolSummary] = ()
    """External tool results that take part in the decision (never an approval)."""


def decide(results: Sequence[TestCaseResult]) -> PolicyEvaluation:
    """The fail-safe decision without a policy: ``flag``. Kept for the CLI path."""
    return evaluate_policy(
        policy=None,
        risk_level=RiskLevel.HIGH,
        results=list(results),
        categories={},
        baseline=None,
        baseline_at=None,
        now=datetime.min,
    )


class PolicyEngine:
    def __init__(
        self, store: EvidenceStore, clock: Clock, ids: IdGenerator, signer: Signer
    ) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids
        self._signer = signer

    def evaluate(
        self, test_cases: Sequence[TestCase], runs: Sequence[Run], binding: SigningBinding
    ) -> tuple[list[TestCaseResult], PolicyEvaluation]:
        results = aggregate(test_cases, runs)
        evaluation = evaluate_policy(
            policy=binding.policy,
            risk_level=binding.risk_level,
            results=results,
            categories=categories_of(test_cases),
            baseline=binding.baseline,
            baseline_at=binding.baseline_at,
            now=self._clock.now(),
            external=binding.external,
        )
        return results, evaluation

    def decide_and_sign(
        self,
        attestation: Attestation,
        contract: Contract,
        card_hash: str,
        test_cases: Sequence[TestCase],
        runs: Sequence[Run],
        transcript_hashes: Mapping[str, str],
        binding: SigningBinding,
    ) -> tuple[Decision, Attestation, list[TestCaseResult], PolicyEvaluation, JsonObject]:
        """Decision first, then signature, then ``completed`` (FLOW.md, step 6).

        If signing fails the decision stays recorded, the attestation is not
        marked completed, and the error propagates so nothing reports approval.
        Returns the decision, the completed attestation, the aggregated results,
        the policy evaluation and the exact payload that was signed.
        """
        if attestation.status is not AttestationStatus.RUNNING:
            raise ValueError(
                f"only a running attestation is decided; {attestation.id} is "
                f"{attestation.status.value}"
            )
        results, evaluation = self.evaluate(test_cases, runs, binding)
        decision = Decision(
            id=self._ids.new_id(),
            attestation_id=attestation.id,
            outcome=evaluation.outcome,
            policy_version=evaluation.policy_version,
            decided_by=POLICY_DECIDED_BY,
            decided_at=self._clock.now(),
        )
        self._store.add_decision(decision)
        issued_at = self._clock.now()
        payload = integrity.build_payload_v2(
            attestation=attestation,
            card_hash=card_hash,
            contract=contract,
            contract_content_hash=binding.contract_content_hash,
            suite_version=binding.suite_version,
            judge_version=binding.judge_version,
            rubric_versions=rubric_versions_of(test_cases),
            policy_version=binding.policy.policy_version if binding.policy else None,
            policy_content_hash=evaluation.content_hash,
            results=results,
            transcript_hashes=transcript_hashes,
            artifact_hashes=binding.artifact_hashes,
            environment=binding.environment,
            deployment_identity=binding.deployment_identity,
            issued_at=issued_at,
            expires_at=issued_at + binding.validity,
            decision=decision,
            reviewer=binding.reviewer,
            issuer=binding.issuer,
        )
        signature, key_id = signing.sign_payload(self._signer, payload)
        completed = signing.replace_fields(
            attestation,
            signature=signature,
            signing_key_id=key_id,
            status=AttestationStatus.COMPLETED,
            finished_at=self._clock.now(),
        )
        self._store.update_attestation(completed)
        return decision, completed, results, evaluation, payload

    def sign_without_decision(
        self,
        attestation: Attestation,
        contract: Contract,
        card_hash: str,
        test_cases: Sequence[TestCase],
        runs: Sequence[Run],
        transcript_hashes: Mapping[str, str],
        binding: SigningBinding,
    ) -> tuple[Attestation, JsonObject]:
        """Sign a failed, invalidated or cancelled attestation; the payload's decision is null."""
        issued_at = self._clock.now()
        payload = integrity.build_payload_v2(
            attestation=attestation,
            card_hash=card_hash,
            contract=contract,
            contract_content_hash=binding.contract_content_hash,
            suite_version=binding.suite_version,
            judge_version=binding.judge_version,
            rubric_versions=rubric_versions_of(test_cases),
            policy_version=binding.policy.policy_version if binding.policy else None,
            policy_content_hash=binding.policy.content_hash() if binding.policy else None,
            results=aggregate(test_cases, runs),
            transcript_hashes=transcript_hashes,
            artifact_hashes=binding.artifact_hashes,
            environment=binding.environment,
            deployment_identity=binding.deployment_identity,
            issued_at=issued_at,
            expires_at=issued_at + binding.validity,
            decision=None,
            reviewer=None,
            issuer=binding.issuer,
        )
        signature, key_id = signing.sign_payload(self._signer, payload)
        signed = signing.with_signature(attestation, signature, key_id)
        self._store.update_attestation(signed)
        return signed, payload
