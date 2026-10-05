"""Agent registration: the customer's record of an agent and its sandbox (OQ-P2, OQ-A2).

A registration creates the core ``agent`` record and holds what the seven
entities do not: the card URL, the sandbox declaration, the credential
reference and the retry policy for unknown outcomes. The deployment mode is
the deployment's, never the request's: a private-network Runner is a
separately authorized deployment, not a per-agent option.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from suncly.core.app import AppServices
from suncly.core.authz import AuthorizedContext
from suncly.domain.errors import NotFoundError, TargetHostRefusedError, ValidationFailedError
from suncly.domain.models import Agent, RiskLevel
from suncly.domain.network import NetworkPolicy, check_url
from suncly.domain.tenancy import AgentRegistration, CredentialReference


@dataclass(frozen=True)
class RegisterAgentRequest:
    name: str
    card_url: str
    risk_level: RiskLevel
    owner: str
    sandbox_declared: bool
    credential: CredentialReference
    sandbox_idempotent: bool = False
    bring_your_own_model_key: bool = False


class AgentRegistry:
    def __init__(self, services: AppServices) -> None:
        self._s = services

    def register(self, ctx: AuthorizedContext, request: RegisterAgentRequest) -> AgentRegistration:
        mode = self._s.app_config.network_mode
        try:
            check_url(request.card_url, NetworkPolicy.for_mode(mode), "card URL")
        except TargetHostRefusedError as exc:
            raise ValidationFailedError(exc.what, exc.why, exc.next_step) from exc
        if request.credential.provider == "env" and self._s.app_config.is_production:
            raise ValidationFailedError(
                "Environment credentials are not available in production.",
                "Use a Secret Manager reference the Runner identity may read.",
            )
        agent = Agent(
            id=self._s.ids.new_id(),
            name=request.name.strip(),
            owner=request.owner.strip() or "unspecified",
            risk_level=request.risk_level,
        )
        self._s.store.add_agent(agent)
        registration = AgentRegistration(
            id=self._s.ids.new_id(),
            organization_id=ctx.organization_id,
            agent_id=agent.id,
            name=agent.name,
            card_url=request.card_url.strip(),
            risk_level=request.risk_level,
            owner=agent.owner,
            sandbox_declared=request.sandbox_declared,
            sandbox_idempotent=request.sandbox_idempotent,
            credential=request.credential,
            deployment_mode=mode,
            bring_your_own_model_key=request.bring_your_own_model_key,
            created_at=self._s.clock.now(),
            created_by=ctx.reviewer_id,
        )
        self._s.app_store.add_registration(registration)
        return registration

    def get(self, ctx: AuthorizedContext, registration_id: UUID) -> AgentRegistration:
        registration = self._s.app_store.get_registration(ctx.organization_id, registration_id)
        if registration is None:
            raise NotFoundError(
                "The agent registration does not exist in this organization.",
                f"No registration {registration_id}.",
            )
        return registration

    def list(self, ctx: AuthorizedContext) -> list[AgentRegistration]:
        return self._s.app_store.list_registrations(ctx.organization_id)

    def archive(self, ctx: AuthorizedContext, registration_id: UUID) -> AgentRegistration:
        archived = self._s.app_store.archive_registration(
            ctx.organization_id, registration_id, self._s.clock.now()
        )
        if archived is None:
            raise NotFoundError(
                "The agent registration does not exist in this organization.",
                f"No registration {registration_id}.",
            )
        return archived

    def by_agent(self, ctx: AuthorizedContext, agent_id: UUID) -> AgentRegistration:
        """The registration of a core agent, if it belongs to the caller's organization."""
        registration = self._s.app_store.get_registration_by_agent(agent_id)
        if registration is None or registration.organization_id != ctx.organization_id:
            raise NotFoundError(
                "The record does not exist in this organization.",
                f"Agent {agent_id} is not registered here.",
            )
        return registration
