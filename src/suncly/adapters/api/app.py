"""The HTTP API: a thin FastAPI adapter over the application services (schema §6).

Every route authenticates the bearer token through the configured verifiers,
resolves the organization from the URL and checks the membership's role
through ``core/authz.py``. Routes translate bodies into service calls and
service results into JSON; no decision lives here.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from suncly import __version__
from suncly.adapters.api import schemas
from suncly.adapters.api.errors import install_error_handlers, request_id_of
from suncly.adapters.report.view import build_view
from suncly.adapters.report.writer import result_document
from suncly.core import integrity, signing
from suncly.core.app import AppServices
from suncly.core.attestations_app import AttestationWorkflow, StartAttestationRequest
from suncly.core.authz import AuthorizedContext
from suncly.core.contracts_app import ContractDetail, ContractWorkflow, DraftSource
from suncly.core.registry import AgentRegistry, RegisterAgentRequest
from suncly.core.resolution import FlagResolutionService
from suncly.domain.errors import AuthenticationError, ConflictError, NotFoundError
from suncly.domain.ledger import SpendingLimit
from suncly.domain.models import JsonObject
from suncly.domain.policy import PolicyRecord
from suncly.domain.tenancy import Membership, Organization, Principal, Role
from suncly.ports.app_store import ReevaluationSchedule

API_TITLE = "Suncly API"
API_DESCRIPTION = (
    "Attestation for A2A agents. Register a sandbox agent, review and approve a versioned "
    "behavioural contract, run an attestation within a spending limit, read signed evidence, "
    "resolve flagged decisions, and consume the result from CI. Every error uses one envelope: "
    "{error: {code, message, detail, next_step, request_id}}."
)


# -- dependencies ---------------------------------------------------------------------
# Module level on purpose: FastAPI resolves the (postponed) annotations of route functions
# in this module's namespace, so the aliases must live here, not inside ``create_app``.


def services_of(request: Request) -> AppServices:
    services: AppServices = request.app.state.services
    return services


def principal(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError(
            "A bearer token is required.",
            "No Authorization: Bearer header was sent.",
            "Sign in with the configured identity provider and send its token.",
        )
    token = authorization.split(None, 1)[1].strip()
    last: AuthenticationError | None = None
    for verifier in services_of(request).verifiers:
        try:
            return verifier.verify(token)
        except AuthenticationError as exc:
            last = exc
    raise last or AuthenticationError("The token could not be verified.")


AuthenticatedPrincipal = Annotated[Principal, Depends(principal)]


def context_for(permission: str) -> Callable[..., AuthorizedContext]:
    """A dependency resolving the caller's membership in the organization of the URL."""

    def dependency(
        request: Request, organization_id: UUID, who: AuthenticatedPrincipal
    ) -> AuthorizedContext:
        return services_of(request).authorizer.require(who, organization_id, permission)

    return dependency


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(
        title=API_TITLE,
        version=__version__,
        description=API_DESCRIPTION,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.state.services = services
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(services.app_config.cors_origins),
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
        allow_credentials=False,
    )
    install_error_handlers(app)

    @app.middleware("http")
    async def request_ids(request: Request, call_next: Callable[[Request], Any]) -> Response:
        request_id = request_id_of(request)
        response: Response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response

    # -- serializers ------------------------------------------------------------

    def organization_json(organization: Organization, membership: Membership | None) -> JsonObject:
        data = organization.model_dump(mode="json")
        data["role"] = membership.role.value if membership else None
        return data

    def contract_json(detail: ContractDetail) -> JsonObject:
        return {
            "contract": detail.contract.model_dump(mode="json"),
            "content_hash": detail.content_hash,
            "source": detail.source,
            "card_version": {
                "id": str(detail.card_version.id),
                "card_hash": detail.card_version.card_hash,
                "fetched_at": detail.card_version.fetched_at.isoformat(),
            },
            "card": detail.parsed.card.model_dump(mode="json", by_alias=False),
            "registration_id": str(detail.registration.id),
            "test_cases": [tc.model_dump(mode="json") for tc in detail.test_cases],
            "not_testable": [n.model_dump(mode="json") for n in detail.not_testable],
            "uncovered_skills": detail.uncovered_skills,
            "suite": detail.suite.model_dump(mode="json") if detail.suite else None,
        }

    def attestation_json(view: Any) -> JsonObject:
        job = view.job
        return {
            "attestation": view.attestation.model_dump(mode="json"),
            "registration_id": str(view.registration.id),
            "contract": {
                "id": str(view.contract.id),
                "version": view.contract.version,
                "content_hash": view.meta.contract_content_hash,
            },
            "meta": view.meta.model_dump(mode="json"),
            "job": None
            if job is None
            else {
                "id": str(job.id),
                "status": job.status.value,
                "attempts": job.attempts,
                "max_attempts": job.max_attempts,
                "cancel_requested": job.cancel_requested,
                "last_error": job.last_error,
                "run_after": job.run_after.isoformat(),
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            },
            "progress": view.progress,
        }

    # -- health ---------------------------------------------------------------

    @app.get("/v1/health", tags=["operations"])
    def health() -> JsonObject:
        return {"status": "ok", "version": __version__}

    @app.get("/v1/ready", tags=["operations"])
    def ready() -> JsonObject:
        services.app_store.list_signing_keys()
        return {"status": "ready", "environment": services.app_config.environment}

    @app.get("/v1/keys", tags=["verification"])
    def trusted_keys() -> JsonObject:
        return {
            "issuer": services.app_config.issuer,
            "keys": [
                {
                    "key_id": key.key_id,
                    "issuer": key.issuer,
                    "public_key": signing.b64url(key.public_key),
                    "created_at": key.created_at.isoformat(),
                    "revoked_at": key.revoked_at.isoformat() if key.revoked_at else None,
                    "revocation_reason": key.revocation_reason,
                }
                for key in services.app_store.list_signing_keys()
            ],
        }

    # -- identity and organizations ---------------------------------------------

    @app.get("/v1/me", tags=["identity"])
    def me(who: AuthenticatedPrincipal) -> JsonObject:
        organizations = services.app_store.list_organizations_for_subject(who.subject)
        return {
            "principal": who.model_dump(mode="json"),
            "organizations": [
                organization_json(o, services.app_store.get_membership(o.id, who.subject))
                for o in organizations
            ],
        }

    @app.post("/v1/organizations", status_code=201, tags=["organizations"])
    def create_organization(
        body: schemas.CreateOrganization, who: AuthenticatedPrincipal
    ) -> JsonObject:
        if services.app_store.get_organization_by_slug(body.slug) is not None:
            raise ConflictError("An organization with this slug exists.", f"Slug {body.slug!r}.")
        organization = Organization(
            id=services.ids.new_id(),
            slug=body.slug,
            name=body.name,
            created_at=services.clock.now(),
        )
        services.app_store.add_organization(organization)
        membership = Membership(
            id=services.ids.new_id(),
            organization_id=organization.id,
            subject=who.subject,
            email=who.email,
            role=Role.ADMINISTRATOR,
            created_at=services.clock.now(),
        )
        services.app_store.add_membership(membership)
        return organization_json(organization, membership)

    @app.get("/v1/organizations/{organization_id}", tags=["organizations"])
    def get_organization(
        ctx: Annotated[AuthorizedContext, Depends(context_for("agents:read"))],
    ) -> JsonObject:
        return organization_json(ctx.organization, ctx.membership)

    @app.get("/v1/organizations/{organization_id}/members", tags=["organizations"])
    def list_members(
        ctx: Annotated[AuthorizedContext, Depends(context_for("members:read"))],
    ) -> JsonObject:
        members = services.app_store.list_memberships(ctx.organization_id)
        return {"members": [m.model_dump(mode="json") for m in members]}

    @app.post(
        "/v1/organizations/{organization_id}/members", status_code=201, tags=["organizations"]
    )
    def add_member(
        body: schemas.AddMember,
        ctx: Annotated[AuthorizedContext, Depends(context_for("members:manage"))],
    ) -> JsonObject:
        membership = Membership(
            id=services.ids.new_id(),
            organization_id=ctx.organization_id,
            subject=body.subject,
            email=body.email,
            role=body.role,
            created_at=services.clock.now(),
        )
        services.app_store.add_membership(membership)
        return membership.model_dump(mode="json")

    # -- agents -------------------------------------------------------------------

    @app.post("/v1/organizations/{organization_id}/agents", status_code=201, tags=["agents"])
    def register_agent(
        body: schemas.RegisterAgent,
        ctx: Annotated[AuthorizedContext, Depends(context_for("agents:write"))],
    ) -> JsonObject:
        registration = AgentRegistry(services).register(
            ctx,
            RegisterAgentRequest(
                name=body.name,
                card_url=body.card_url,
                risk_level=body.risk_level,
                owner=body.owner,
                sandbox_declared=body.sandbox_declared,
                credential=body.credential,
                sandbox_idempotent=body.sandbox_idempotent,
                bring_your_own_model_key=body.bring_your_own_model_key,
            ),
        )
        return registration.model_dump(mode="json")

    @app.get("/v1/organizations/{organization_id}/agents", tags=["agents"])
    def list_agents(
        ctx: Annotated[AuthorizedContext, Depends(context_for("agents:read"))],
    ) -> JsonObject:
        return {"agents": [r.model_dump(mode="json") for r in AgentRegistry(services).list(ctx)]}

    @app.get("/v1/organizations/{organization_id}/agents/{registration_id}", tags=["agents"])
    def get_agent(
        registration_id: UUID,
        ctx: Annotated[AuthorizedContext, Depends(context_for("agents:read"))],
    ) -> JsonObject:
        return AgentRegistry(services).get(ctx, registration_id).model_dump(mode="json")

    @app.delete("/v1/organizations/{organization_id}/agents/{registration_id}", tags=["agents"])
    def archive_agent(
        registration_id: UUID,
        ctx: Annotated[AuthorizedContext, Depends(context_for("agents:write"))],
    ) -> JsonObject:
        return AgentRegistry(services).archive(ctx, registration_id).model_dump(mode="json")

    # -- contracts ----------------------------------------------------------------

    @app.post(
        "/v1/organizations/{organization_id}/agents/{registration_id}/contracts/draft",
        status_code=201,
        tags=["contracts"],
    )
    def draft_contract(
        registration_id: UUID,
        body: schemas.DraftContract,
        ctx: Annotated[AuthorizedContext, Depends(context_for("contracts:draft"))],
    ) -> JsonObject:
        detail = ContractWorkflow(services).draft(
            ctx,
            registration_id,
            DraftSource(kind=body.source, suite=body.suite, contract_file=body.contract_file),
        )
        return contract_json(detail)

    @app.get(
        "/v1/organizations/{organization_id}/agents/{registration_id}/contracts",
        tags=["contracts"],
    )
    def list_contracts(
        registration_id: UUID,
        ctx: Annotated[AuthorizedContext, Depends(context_for("contracts:read"))],
    ) -> JsonObject:
        contracts = ContractWorkflow(services).list_for_agent(ctx, registration_id)
        return {"contracts": [c.model_dump(mode="json") for c in contracts]}

    @app.get("/v1/organizations/{organization_id}/contracts/{contract_id}", tags=["contracts"])
    def get_contract(
        contract_id: UUID,
        ctx: Annotated[AuthorizedContext, Depends(context_for("contracts:read"))],
    ) -> JsonObject:
        return contract_json(ContractWorkflow(services).get(ctx, contract_id))

    @app.post(
        "/v1/organizations/{organization_id}/contracts/{contract_id}/approve", tags=["contracts"]
    )
    def approve_contract(
        contract_id: UUID,
        ctx: Annotated[AuthorizedContext, Depends(context_for("contracts:approve"))],
    ) -> JsonObject:
        return contract_json(ContractWorkflow(services).approve(ctx, contract_id))

    @app.post(
        "/v1/organizations/{organization_id}/contracts/{contract_id}/reject", tags=["contracts"]
    )
    def reject_contract(
        contract_id: UUID,
        ctx: Annotated[AuthorizedContext, Depends(context_for("contracts:reject"))],
    ) -> JsonObject:
        return contract_json(ContractWorkflow(services).reject(ctx, contract_id))

    # -- attestations ---------------------------------------------------------------

    @app.post(
        "/v1/organizations/{organization_id}/attestations", status_code=202, tags=["attestations"]
    )
    def start_attestation(
        body: schemas.StartAttestation,
        ctx: Annotated[AuthorizedContext, Depends(context_for("attestations:start"))],
    ) -> JsonObject:
        view = AttestationWorkflow(services).start(
            ctx,
            StartAttestationRequest(
                registration_id=body.registration_id,
                contract_id=body.contract_id,
                runs=body.runs,
                budget_limit=body.budget_limit,
                trigger=body.trigger_value,
                external_tools=tuple(dict.fromkeys(body.external_tools)),
            ),
        )
        return attestation_json(view)

    @app.get("/v1/organizations/{organization_id}/attestations", tags=["attestations"])
    def list_attestations(
        ctx: Annotated[AuthorizedContext, Depends(context_for("attestations:read"))],
        registration_id: Annotated[UUID | None, Query()] = None,
    ) -> JsonObject:
        views = AttestationWorkflow(services).list(ctx, registration_id)
        return {"attestations": [attestation_json(v) for v in views]}

    @app.get(
        "/v1/organizations/{organization_id}/attestations/{attestation_id}", tags=["attestations"]
    )
    def get_attestation(
        attestation_id: UUID,
        ctx: Annotated[AuthorizedContext, Depends(context_for("attestations:read"))],
    ) -> JsonObject:
        return attestation_json(AttestationWorkflow(services).owned(ctx, attestation_id))

    @app.post(
        "/v1/organizations/{organization_id}/attestations/{attestation_id}/cancel",
        tags=["attestations"],
    )
    def cancel_attestation(
        attestation_id: UUID,
        ctx: Annotated[AuthorizedContext, Depends(context_for("attestations:cancel"))],
    ) -> JsonObject:
        return attestation_json(AttestationWorkflow(services).cancel(ctx, attestation_id))

    @app.get(
        "/v1/organizations/{organization_id}/attestations/{attestation_id}/evidence",
        tags=["attestations"],
    )
    def attestation_evidence(
        attestation_id: UUID,
        ctx: Annotated[AuthorizedContext, Depends(context_for("evidence:read"))],
    ) -> JsonObject:
        bundle = AttestationWorkflow(services).evidence(ctx, attestation_id)
        transcripts = {
            str(evidence.run.id): services.transcripts.get(evidence.run.transcript_ref).decode(
                "utf-8"
            )
            for evidence in bundle.runs
        }
        view = build_view(bundle)
        return {
            "result": result_document(bundle),
            "transcripts": transcripts,
            "summary": {
                "decision_line": view.decision_line,
                "decision_detail": view.decision_detail,
                "not_tested": [list(item) for item in view.not_tested],
            },
        }

    @app.get(
        "/v1/organizations/{organization_id}/attestations/{attestation_id}/verification",
        tags=["verification"],
    )
    def attestation_verification(
        attestation_id: UUID,
        ctx: Annotated[AuthorizedContext, Depends(context_for("evidence:read"))],
    ) -> JsonObject:
        bundle = AttestationWorkflow(services).evidence(ctx, attestation_id)
        files = {
            str(evidence.run.id): services.transcripts.get(evidence.run.transcript_ref)
            for evidence in bundle.runs
        }
        policies = services.app_store.list_policies(ctx.organization_id)
        trust = integrity.TrustContext(
            now=services.clock.now(),
            trusted_keys={k.key_id: k for k in services.app_store.list_signing_keys()},
            expected_issuer=services.app_config.issuer,
            current_policy_hash=policies[-1].content_hash if policies else None,
        )
        return integrity.verify_layers(result_document(bundle), files, trust).to_json()

    @app.post(
        "/v1/organizations/{organization_id}/attestations/{attestation_id}/decisions",
        status_code=201,
        tags=["attestations"],
    )
    def resolve_flag(
        attestation_id: UUID,
        body: schemas.ResolveDecision,
        ctx: Annotated[AuthorizedContext, Depends(context_for("decisions:resolve"))],
    ) -> JsonObject:
        decision, note = FlagResolutionService(services).resolve(
            ctx, attestation_id, body.outcome, body.rationale
        )
        return {"decision": decision.model_dump(mode="json"), "note": note.model_dump(mode="json")}

    # -- policy ---------------------------------------------------------------------

    @app.get("/v1/organizations/{organization_id}/policies", tags=["policy"])
    def list_policies(
        ctx: Annotated[AuthorizedContext, Depends(context_for("policy:read"))],
    ) -> JsonObject:
        return {
            "policies": [
                p.model_dump(mode="json")
                for p in services.app_store.list_policies(ctx.organization_id)
            ]
        }

    @app.post("/v1/organizations/{organization_id}/policies", status_code=201, tags=["policy"])
    def create_policy(
        body: schemas.CreatePolicy,
        ctx: Annotated[AuthorizedContext, Depends(context_for("policy:write"))],
    ) -> JsonObject:
        record = PolicyRecord(
            id=services.ids.new_id(),
            organization_id=ctx.organization_id,
            policy_version=body.configuration.policy_version,
            content_hash=body.configuration.content_hash(),
            configuration=body.configuration,
            created_at=services.clock.now(),
            created_by=ctx.reviewer_id,
        )
        services.app_store.add_policy(record)
        return record.model_dump(mode="json")

    @app.get("/v1/organizations/{organization_id}/policies/{policy_id}", tags=["policy"])
    def get_policy(
        policy_id: UUID,
        ctx: Annotated[AuthorizedContext, Depends(context_for("policy:read"))],
    ) -> JsonObject:
        record = services.app_store.get_policy(ctx.organization_id, policy_id)
        if record is None:
            raise NotFoundError("The policy does not exist in this organization.")
        return record.model_dump(mode="json")

    # -- usage and billing ------------------------------------------------------------

    @app.get("/v1/organizations/{organization_id}/usage", tags=["billing"])
    def usage(
        ctx: Annotated[AuthorizedContext, Depends(context_for("usage:read"))],
    ) -> JsonObject:
        entitlement = services.usage.entitlement(ctx.organization_id)
        events = services.app_store.list_usage_events(
            ctx.organization_id, services.usage.period_start(ctx.organization_id)
        )
        return {
            "entitlement": entitlement.model_dump(mode="json"),
            "events": [e.model_dump(mode="json") for e in events[-200:]],
            "reservations": [
                r.model_dump(mode="json")
                for r in services.app_store.list_reservations(ctx.organization_id)[-50:]
            ],
        }

    @app.put("/v1/organizations/{organization_id}/spending-limit", tags=["billing"])
    def set_spending_limit(
        body: schemas.SetSpendingLimit,
        ctx: Annotated[AuthorizedContext, Depends(context_for("limits:write"))],
    ) -> JsonObject:
        limit = SpendingLimit(
            organization_id=ctx.organization_id,
            currency=services.usage.currency,
            period_limit_minor=body.period_limit_minor,
            set_by=ctx.reviewer_id,
            set_at=services.clock.now(),
        )
        services.app_store.add_spending_limit(limit)
        return limit.model_dump(mode="json")

    @app.get("/v1/billing/plans", tags=["billing"])
    def plans() -> JsonObject:
        return {
            "catalog_version": services.app_config.billing.plan_catalog_version,
            "price_table_version": services.app_config.price_table_version,
            "plans": [p.model_dump(mode="json") for p in services.billing.plans.values()],
            "note": "Test catalog. No live product or price exists.",
        }

    @app.get("/v1/organizations/{organization_id}/subscription", tags=["billing"])
    def subscription(
        ctx: Annotated[AuthorizedContext, Depends(context_for("billing:read"))],
    ) -> JsonObject:
        current = services.app_store.get_subscription(ctx.organization_id)
        return {
            "subscription": current.model_dump(mode="json") if current else None,
            "entitlement": services.usage.entitlement(ctx.organization_id).model_dump(mode="json"),
        }

    @app.post("/v1/organizations/{organization_id}/billing/checkout", tags=["billing"])
    def checkout(
        body: schemas.StartCheckout,
        ctx: Annotated[AuthorizedContext, Depends(context_for("billing:manage"))],
    ) -> JsonObject:
        session = services.billing.start_checkout(
            ctx.organization_id, ctx.organization.slug, body.plan_id, ctx.principal.email
        )
        return session.model_dump(mode="json")

    @app.post("/v1/organizations/{organization_id}/billing/portal", tags=["billing"])
    def portal(
        ctx: Annotated[AuthorizedContext, Depends(context_for("billing:manage"))],
    ) -> JsonObject:
        return services.billing.open_portal(ctx.organization_id).model_dump(mode="json")

    @app.get("/v1/organizations/{organization_id}/billing/reconciliation", tags=["billing"])
    def reconciliation(
        ctx: Annotated[AuthorizedContext, Depends(context_for("billing:manage"))],
    ) -> JsonObject:
        return services.billing.reconciliation(ctx.organization_id)

    @app.post("/v1/webhooks/stripe", tags=["billing"])
    async def stripe_webhook(
        request: Request,
        stripe_signature: Annotated[str | None, Header()] = None,
    ) -> JsonObject:
        payload = await request.body()
        return {"result": services.billing.handle_webhook(payload, stripe_signature)}

    # -- schedules ----------------------------------------------------------------------

    @app.post("/v1/organizations/{organization_id}/schedules", status_code=201, tags=["schedules"])
    def create_schedule(
        body: schemas.CreateSchedule,
        ctx: Annotated[AuthorizedContext, Depends(context_for("schedules:write"))],
    ) -> JsonObject:
        AgentRegistry(services).get(ctx, body.registration_id)
        schedule = ReevaluationSchedule(
            id=services.ids.new_id(),
            organization_id=ctx.organization_id,
            registration_id=body.registration_id,
            interval_hours=body.interval_hours,
            runs_per_test_case=body.runs,
            budget_limit=str(body.budget_limit),
            next_run_at=services.clock.now() + timedelta(hours=body.interval_hours),
            created_by=ctx.reviewer_id,
            created_at=services.clock.now(),
        )
        services.app_store.add_schedule(schedule)
        return schedule.model_dump(mode="json")

    @app.get("/v1/organizations/{organization_id}/schedules", tags=["schedules"])
    def list_schedules(
        ctx: Annotated[AuthorizedContext, Depends(context_for("agents:read"))],
    ) -> JsonObject:
        return {
            "schedules": [
                s.model_dump(mode="json")
                for s in services.app_store.list_schedules(ctx.organization_id)
            ]
        }

    return app
