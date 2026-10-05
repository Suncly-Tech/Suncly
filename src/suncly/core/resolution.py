"""Human resolution of flagged attestations (SCHEMA.md §11, POLICY.md).

A reviewer records a second ``decision`` with ``approve`` or ``block``
(OQ-D11) and the rationale behind it. The first decision is never edited;
the note is append-only; the reviewer's identity comes from the verified
principal, never from the body. Only a ``completed`` attestation whose latest
decision is ``flag`` can be resolved.
"""

from __future__ import annotations

from uuid import UUID

from suncly.core.app import AppServices
from suncly.core.attestations_app import AttestationWorkflow
from suncly.core.authz import AuthorizedContext
from suncly.domain.errors import ConflictError, ValidationFailedError
from suncly.domain.models import AttestationStatus, Decision, DecisionOutcome
from suncly.ports.app_store import DecisionNote

#: The outcomes a human may choose (OQ-D11, proposal).
HUMAN_OUTCOMES = frozenset({DecisionOutcome.APPROVE, DecisionOutcome.BLOCK})


class FlagResolutionService:
    def __init__(self, services: AppServices) -> None:
        self._s = services
        self._attestations = AttestationWorkflow(services)

    def resolve(
        self, ctx: AuthorizedContext, attestation_id: UUID, outcome: DecisionOutcome, rationale: str
    ) -> tuple[Decision, DecisionNote]:
        s = self._s
        if outcome not in HUMAN_OUTCOMES:
            raise ValidationFailedError(
                "A human decision is approve or block.", f"{outcome.value} is not allowed."
            )
        if len(rationale.strip()) < 20:
            raise ValidationFailedError(
                "A rationale is required.",
                "Write at least 20 characters a colleague could act on.",
            )
        view = self._attestations.owned(ctx, attestation_id)
        if view.attestation.status is not AttestationStatus.COMPLETED:
            raise ConflictError(
                "Only a completed attestation can be resolved.",
                f"Attestation {attestation_id} is {view.attestation.status.value}; a failed, "
                "invalidated or cancelled attestation carries no decision (schema §11).",
            )
        decisions = s.store.list_decisions(attestation_id)
        latest = decisions[-1] if decisions else None
        if latest is None or latest.outcome is not DecisionOutcome.FLAG:
            raise ConflictError(
                "The attestation is not waiting for a human decision.",
                f"Its latest decision is {latest.outcome.value if latest else 'absent'}.",
                "A resolved attestation is not re-decided; run a new attestation instead.",
            )
        decision = Decision(
            id=s.ids.new_id(),
            attestation_id=attestation_id,
            outcome=outcome,
            policy_version=decisions[0].policy_version,
            decided_by=ctx.reviewer_id,
            decided_at=s.clock.now(),
        )
        s.store.add_decision(decision)
        note = DecisionNote(
            decision_id=decision.id,
            organization_id=ctx.organization_id,
            attestation_id=attestation_id,
            reviewer_subject=ctx.principal.subject,
            rationale=rationale.strip(),
            created_at=s.clock.now(),
        )
        s.app_store.add_decision_note(note)
        s.app_store.update_attestation_meta(
            view.meta.model_copy(update={"decided_by_reviewer": ctx.reviewer_id})
        )
        return decision, note
