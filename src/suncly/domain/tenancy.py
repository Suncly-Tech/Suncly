"""Tenancy: organizations, memberships, roles and agent registrations.

The hosted application layer sits around the attestation core. The seven
entities of SCHEMA.md §3 stay what they are; these records belong to the
commercial application layer (SCHEMA.md §12) and live in the ``suncly_app``
database schema. Nothing here is trusted from a request body: organization ids
and reviewer identities always come from the authenticated principal.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from suncly.domain.models import RiskLevel

JsonObject = dict[str, Any]


class Role(StrEnum):
    """Membership roles. Permissions are derived in ``core/authz.py``."""

    ADMINISTRATOR = "administrator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class Organization(BaseModel):
    """A tenant. Every registration, job, ledger entry and policy is scoped to one."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1, max_length=200)
    created_at: AwareDatetime
    #: Attestation jobs that may run at the same time for this tenant.
    max_concurrent_jobs: int = Field(default=2, ge=1, le=64)


class Membership(BaseModel):
    """A person's role in an organization. ``subject`` is the identity provider's stable id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    organization_id: UUID
    subject: str = Field(min_length=1, max_length=256)
    email: str | None = Field(default=None, max_length=320)
    role: Role
    created_at: AwareDatetime


class Principal(BaseModel):
    """The authenticated caller of one request, as the identity adapter verified it.

    The principal carries no organization: memberships are looked up in the
    store for the organization named in the URL, never taken from the token or
    the body. ``reviewer_id`` is what ``approved_by`` and ``decided_by`` record.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: str = Field(min_length=1)
    issuer: str = Field(min_length=1)
    email: str | None = None
    display_name: str | None = None
    #: The authentication adapter that verified the token (``oidc`` or ``local``).
    verified_by: str = Field(min_length=1)

    @property
    def reviewer_id(self) -> str:
        """The identifier recorded on approvals and decisions: email when known, else subject."""
        return self.email or self.subject


class DeploymentMode(StrEnum):
    """Where the Runner may connect (OQ-A2, docs/ARCHITECTURE.md: Runner security)."""

    PUBLIC = "public"
    """Hosted mode: only public addresses over https; loopback, private, link-local and
    metadata ranges are refused at connection time."""
    PRIVATE_NETWORK = "private_network"
    """A separately authorized Runner deployment inside the customer's network. Never
    selectable through the public API."""
    LOCAL = "local"
    """Developer mode on one machine: loopback over plain http is allowed."""


class CredentialReference(BaseModel):
    """Where the Runner finds the credential for a sandbox. Never the credential itself."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: ``secret-manager`` (Google Secret Manager), ``env`` (local development) or ``none``.
    provider: str = Field(pattern=r"^(secret-manager|env|none)$")
    #: The provider's reference: a Secret Manager resource name or an environment variable name.
    ref: str = Field(default="", max_length=512)

    @model_validator(mode="after")
    def _ref_matches_provider(self) -> CredentialReference:
        if self.provider == "none" and self.ref:
            raise ValueError("a credential reference of provider none carries no ref")
        if self.provider != "none" and not self.ref.strip():
            raise ValueError(f"a credential reference of provider {self.provider} needs a ref")
        for forbidden in ("Bearer ", "bearer ", "Basic "):
            if forbidden in self.ref:
                raise ValueError("the reference looks like a credential value; store a reference")
        return self


class AgentRegistration(BaseModel):
    """A customer's registration of an agent for attestation.

    It points at the core ``agent`` record (``agent_id``) and holds what the
    core does not store: the card URL, the sandbox declaration, the credential
    reference and the execution policy for unknown outcomes (OQ-D2, OQ-A2).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    organization_id: UUID
    agent_id: UUID
    name: str = Field(min_length=1, max_length=200)
    card_url: str = Field(min_length=1, max_length=2048)
    risk_level: RiskLevel
    owner: str = Field(min_length=1, max_length=200)
    sandbox_declared: bool
    """DR-006: the customer's declaration that the endpoint is a sandbox or dry-run endpoint."""
    sandbox_idempotent: bool = False
    """The customer's declaration that repeating a sandbox call is harmless. Only then is an
    attempt whose outcome is unknown (the Runner died after sending) retried."""
    credential: CredentialReference
    deployment_mode: DeploymentMode = DeploymentMode.PUBLIC
    bring_your_own_model_key: bool = False
    """BYOK: the tenant pays the model provider directly; Suncly records usage but bills nothing
    for it."""
    created_at: AwareDatetime
    created_by: str = Field(min_length=1)
    archived_at: AwareDatetime | None = None

    @property
    def active(self) -> bool:
        return self.archived_at is None


class ApiError(BaseModel):
    """The one error envelope every HTTP response uses (docs/API.md)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    detail: str = ""
    next_step: str = ""
    request_id: str | None = None
