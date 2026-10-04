"""The Policy engine (schema §2, §4 step 6, §11).

It aggregates run results per test case (the only place that does), applies
the policy, writes the decision, and signs the attestation. There is no policy
configuration in this version, so the engine implements only the documented
fail-safe path: every attestation whose runs all finished and whose card is
unchanged gets exactly one decision with outcome ``flag`` (POLICY.md,
ARCHITECTURE.md: Policy engine, "Fails safely"). It contains no numeric
threshold and never writes ``approve`` or ``block``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime

from suncly.core import signing
from suncly.domain.evidence import TestCaseResult
from suncly.domain.models import (
    POLICY_DECIDED_BY,
    Attestation,
    AttestationStatus,
    Contract,
    Decision,
    DecisionOutcome,
    Run,
    RunVerdict,
    TestCase,
)
from suncly.ports.clock import Clock, IdGenerator
from suncly.ports.signer import Signer
from suncly.ports.store import EvidenceStore

#: ``decision.policy_version`` while no policy configuration exists (OQ-PO5, placeholder).
POLICY_VERSION_UNCONFIGURED = "unconfigured"

#: The one sentence every surface prints with the decision.
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


def decide(results: Sequence[TestCaseResult]) -> DecisionOutcome:
    """The fail-safe decision: ``flag``, for any results, until a policy is configured.

    ``results`` is accepted so the signature matches the configured engine of
    stage 5; nothing in it can change the outcome here.
    """
    del results
    return DecisionOutcome.FLAG


class PolicyEngine:
    def __init__(
        self, store: EvidenceStore, clock: Clock, ids: IdGenerator, signer: Signer
    ) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids
        self._signer = signer

    def decide_and_sign(
        self,
        attestation: Attestation,
        contract: Contract,
        card_hash: str,
        test_cases: Sequence[TestCase],
        runs: Sequence[Run],
        transcript_hashes: Mapping[str, str],
    ) -> tuple[Decision, Attestation, list[TestCaseResult]]:
        """Decision first, then signature, then ``completed`` (FLOW.md, step 6).

        If signing fails the decision stays recorded, the attestation is not
        marked completed, and the error propagates so nothing reports approval.
        """
        if attestation.status is not AttestationStatus.RUNNING:
            raise ValueError(
                f"only a running attestation is decided; {attestation.id} is "
                f"{attestation.status.value}"
            )
        results = aggregate(test_cases, runs)
        decision = Decision(
            id=self._ids.new_id(),
            attestation_id=attestation.id,
            outcome=decide(results),
            policy_version=POLICY_VERSION_UNCONFIGURED,
            decided_by=POLICY_DECIDED_BY,
            decided_at=self._clock.now(),
        )
        self._store.add_decision(decision)
        payload = signing.build_payload(
            attestation=attestation,
            card_hash=card_hash,
            contract=contract,
            results=results,
            transcript_hashes=transcript_hashes,
            decision=decision,
        )
        signature, key_id = signing.sign_payload(self._signer, payload)
        finished_at: datetime = self._clock.now()
        completed = signing.replace_fields(
            attestation,
            signature=signature,
            signing_key_id=key_id,
            status=AttestationStatus.COMPLETED,
            finished_at=finished_at,
        )
        self._store.update_attestation(completed)
        return decision, completed, results
