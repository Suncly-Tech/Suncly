"""The hosted attestation workflow: create asynchronously, follow, cancel, read evidence.

``start`` reserves money, creates the core ``attestation`` record and a
durable job, and returns at once; the worker (``core/worker.py``) executes
the job. Evidence is assembled from the stores on request, so the API never
depends on the worker's memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from suncly.core.app import AppServices
from suncly.core.attestation import PROPOSALS_IN_EFFECT
from suncly.core.authz import AuthorizedContext
from suncly.core.config import DEFAULT_BUDGET_FACTOR
from suncly.core.contract_builder import contract_content_hash
from suncly.core.evidence import assemble_bundle
from suncly.core.judge import JUDGE_VERSION
from suncly.core.policy_engine import rubric_versions_of
from suncly.core.registry import AgentRegistry
from suncly.domain.criteria import parse_criteria
from suncly.domain.errors import ConflictError, NotFoundError, StoreError
from suncly.domain.evidence import CardRecheck, EvidenceBundle, NotExecutedRun
from suncly.domain.jobs import Job, JobKind, JobStatus, OutboxMessage
from suncly.domain.models import (
    Attestation,
    AttestationStatus,
    AttestationTrigger,
    Contract,
    ContractStatus,
    JsonObject,
)
from suncly.domain.tenancy import AgentRegistration
from suncly.ports.app_store import AttestationMeta


@dataclass(frozen=True)
class StartAttestationRequest:
    registration_id: UUID
    contract_id: UUID
    runs: int
    budget_limit: Decimal | None = None
    trigger: AttestationTrigger = AttestationTrigger.MANUAL


@dataclass(frozen=True)
class AttestationView:
    attestation: Attestation
    meta: AttestationMeta
    job: Job | None
    registration: AgentRegistration
    contract: Contract

    @property
    def progress(self) -> JsonObject:
        return dict(self.job.progress) if self.job else {}


class AttestationWorkflow:
    def __init__(self, services: AppServices) -> None:
        self._s = services
        self._registry = AgentRegistry(services)

    # -- start -------------------------------------------------------------------------

    def start(self, ctx: AuthorizedContext, request: StartAttestationRequest) -> AttestationView:
        s = self._s
        registration = self._registry.get(ctx, request.registration_id)
        if not registration.active:
            raise ConflictError("The registration is archived.", "Archived agents do not run.")
        if not registration.sandbox_declared:
            raise ConflictError(
                "Nothing runs: the endpoint is not declared a sandbox or dry-run endpoint.",
                "Suncly only tests sandboxes (DR-006).",
                "Register the agent with the sandbox declaration.",
            )
        contract = s.store.get_contract(request.contract_id)
        card_version = s.store.get_card_version(contract.card_version_id) if contract else None
        if (
            contract is None
            or card_version is None
            or card_version.agent_id != registration.agent_id
        ):
            raise NotFoundError(
                "The contract does not belong to this agent.", f"No contract {request.contract_id}."
            )
        if contract.status is not ContractStatus.APPROVED:
            raise ConflictError(
                "The contract is not approved.",
                f"Contract {contract.id} is {contract.status.value}; nothing runs before a human "
                "approves it (schema §2).",
            )
        test_cases = s.store.list_test_cases(contract.id)
        planned = request.runs * len(test_cases)
        budget_limit = (
            request.budget_limit
            if request.budget_limit is not None
            else Decimal(DEFAULT_BUDGET_FACTOR * planned)
        )
        model_judged = sum(1 for tc in test_cases if parse_criteria(tc.criteria).needs_model_judge)
        estimate = s.usage.estimate(
            planned_runs=int(min(Decimal(planned) * 2, budget_limit)) if planned else 0,
            model_judged_runs=model_judged * request.runs,
            model=s.app_config.model.identity if s.app_config.model else None,
            byok=registration.bring_your_own_model_key,
        )
        attestation = Attestation(
            id=s.ids.new_id(),
            contract_id=contract.id,
            card_version_id=card_version.id,
            trigger=request.trigger,
            status=AttestationStatus.QUEUED,
            started_at=s.clock.now(),
            budget_limit=budget_limit,
            cost_total=Decimal(0),
        )
        reservation = s.usage.reserve(
            ctx.organization_id,
            None,
            estimate.total_minor,
            note=f"attestation {attestation.id}",
        )
        s.store.add_attestation(attestation)
        meta = AttestationMeta(
            attestation_id=attestation.id,
            organization_id=ctx.organization_id,
            registration_id=registration.id,
            created_by=ctx.reviewer_id,
            runs_planned=planned,
            runs_per_test_case=request.runs,
            suite_version=self._suite_version(contract.id),
            contract_content_hash=contract_content_hash(test_cases),
            judge_version=JUDGE_VERSION,
            rubric_versions=rubric_versions_of(test_cases),
            environment={
                "deployment_mode": registration.deployment_mode.value,
                "sandbox_declared": registration.sandbox_declared,
            },
        )
        s.app_store.add_attestation_meta(meta)
        job = Job(
            id=s.ids.new_id(),
            organization_id=ctx.organization_id,
            kind=JobKind.ATTESTATION,
            logical_id=attestation.id,
            payload={
                "registration_id": str(registration.id),
                "contract_id": str(contract.id),
                "card_version_id": str(card_version.id),
                "runs": request.runs,
                "reservation_id": str(reservation.id),
                "created_by": ctx.reviewer_id,
            },
            status=JobStatus.QUEUED,
            created_at=s.clock.now(),
            run_after=s.clock.now(),
            max_attempts=s.app_config.worker.max_attempts,
            progress={"phase": "queued", "planned_runs": planned, "recorded_runs": 0},
        )
        try:
            s.app_store.enqueue_job(
                job,
                [
                    OutboxMessage(
                        id=s.ids.new_id(),
                        organization_id=ctx.organization_id,
                        topic="attestation.queued",
                        dedup_key=f"attestation.queued:{attestation.id}",
                        payload={"attestation_id": str(attestation.id)},
                        created_at=s.clock.now(),
                    )
                ],
            )
        except Exception:
            s.usage.release(reservation.id)
            cancelled = attestation.model_copy(
                update={"status": AttestationStatus.CANCELLED, "finished_at": s.clock.now()}
            )
            s.store.update_attestation(cancelled)
            raise
        return AttestationView(attestation, meta, job, registration, contract)

    def _suite_version(self, contract_id: UUID) -> str:
        key = f"contracts/{contract_id}/suite.json"
        if self._s.transcripts.exists(key):
            from suncly.domain.behavioral import parse_behavioral_suite

            suite = parse_behavioral_suite(self._s.transcripts.get(key).decode("utf-8"))
            return f"behavioral-suite/{suite.suite_version}"
        return "contract/1"

    # -- reading ---------------------------------------------------------------------------

    def owned(self, ctx: AuthorizedContext, attestation_id: UUID) -> AttestationView:
        s = self._s
        meta = s.app_store.get_attestation_meta(attestation_id)
        attestation = s.store.get_attestation(attestation_id)
        if meta is None or attestation is None or meta.organization_id != ctx.organization_id:
            raise NotFoundError(
                "The attestation does not exist in this organization.",
                f"No attestation {attestation_id}.",
            )
        registration = s.app_store.get_registration(ctx.organization_id, meta.registration_id)
        contract = s.store.get_contract(attestation.contract_id)
        if registration is None or contract is None:
            raise StoreError("The attestation references records that do not exist.")
        job = s.app_store.find_job(JobKind.ATTESTATION, attestation_id)
        return AttestationView(attestation, meta, job, registration, contract)

    def list(
        self, ctx: AuthorizedContext, registration_id: UUID | None = None
    ) -> list[AttestationView]:
        views: list[AttestationView] = []
        for meta in self._s.app_store.list_attestation_meta(ctx.organization_id, registration_id):
            try:
                views.append(self.owned(ctx, meta.attestation_id))
            except (NotFoundError, StoreError):
                continue
        return sorted(views, key=lambda v: v.attestation.started_at, reverse=True)

    def cancel(self, ctx: AuthorizedContext, attestation_id: UUID) -> AttestationView:
        s = self._s
        view = self.owned(ctx, attestation_id)
        if view.attestation.status.is_final:
            raise ConflictError(
                "The attestation is already final.",
                f"Attestation {attestation_id} is {view.attestation.status.value}.",
            )
        job = s.app_store.request_cancel(view.job.id, s.clock.now()) if view.job else None
        attestation = view.attestation
        if (
            job is not None
            and job.status is JobStatus.CANCELLED
            and not attestation.status.is_final
        ):
            attestation = attestation.model_copy(
                update={"status": AttestationStatus.CANCELLED, "finished_at": s.clock.now()}
            )
            s.store.update_attestation(attestation)
            reservation_id = (job.payload or {}).get("reservation_id")
            if reservation_id:
                s.usage.release(UUID(str(reservation_id)))
        return AttestationView(attestation, view.meta, job, view.registration, view.contract)

    def evidence(self, ctx: AuthorizedContext, attestation_id: UUID) -> EvidenceBundle:
        s = self._s
        view = self.owned(ctx, attestation_id)
        progress = view.progress
        not_executed = [
            NotExecutedRun.model_validate(item) for item in progress.get("not_executed") or []
        ]
        recheck = (
            CardRecheck.model_validate(progress["card_recheck"])
            if isinstance(progress.get("card_recheck"), dict)
            else CardRecheck(outcome="not_performed", detail="the attestation has not finished")
        )
        signer = s.keys.current()
        public_key = None
        if view.attestation.signing_key_id:
            record = s.app_store.get_signing_key(view.attestation.signing_key_id)
            public_key = record.public_key if record else None
        if public_key is None and signer is not None:
            public_key = signer.public_key
        notes = [
            {
                "decision_id": str(note.decision_id),
                "reviewer_subject": note.reviewer_subject,
                "rationale": note.rationale,
                "created_at": note.created_at.isoformat(),
            }
            for note in s.app_store.list_decision_notes(attestation_id)
        ]
        return assemble_bundle(
            store=s.store,
            transcripts=s.transcripts,
            attestation_id=attestation_id,
            clock=s.clock,
            card_url=view.registration.card_url,
            target_url=progress.get("target_url"),
            planned_runs=view.meta.runs_planned,
            not_executed=not_executed,
            card_recheck=recheck,
            sandbox_declared=view.registration.sandbox_declared,
            drafter_name=view.meta.suite_version,
            signer_public_key=public_key,
            proposals=PROPOSALS_IN_EFFECT,
            policy_evaluation=progress.get("policy_evaluation"),
            decision_notes=notes,
            external_results=list(progress.get("external_results") or []),
        )
