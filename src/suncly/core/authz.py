"""Authorization: what a membership role may do in an organization.

Every API route, background job and evidence read goes through
``Authorizer.require``. The organization comes from the URL and the principal
from the verified token; neither is ever read from a request body.
Non-members get ``NotFoundError`` so other tenants' organizations are
indistinguishable from ones that do not exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from suncly.domain.errors import AuthorizationError, NotFoundError
from suncly.domain.tenancy import Membership, Organization, Principal, Role
from suncly.ports.app_store import ApplicationStore

VIEWER_PERMISSIONS = frozenset(
    {
        "agents:read",
        "contracts:read",
        "attestations:read",
        "evidence:read",
        "usage:read",
        "policy:read",
        "members:read",
        "billing:read",
    }
)
REVIEWER_PERMISSIONS = VIEWER_PERMISSIONS | frozenset(
    {
        "agents:write",
        "contracts:draft",
        "contracts:approve",
        "contracts:reject",
        "attestations:start",
        "attestations:cancel",
        "decisions:resolve",
    }
)
ADMINISTRATOR_PERMISSIONS = REVIEWER_PERMISSIONS | frozenset(
    {
        "members:manage",
        "policy:write",
        "billing:manage",
        "limits:write",
        "schedules:write",
        "keys:manage",
    }
)

PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.VIEWER: VIEWER_PERMISSIONS,
    Role.REVIEWER: REVIEWER_PERMISSIONS,
    Role.ADMINISTRATOR: ADMINISTRATOR_PERMISSIONS,
}
ALL_PERMISSIONS = ADMINISTRATOR_PERMISSIONS


@dataclass(frozen=True)
class AuthorizedContext:
    """A principal acting in one organization with one role."""

    principal: Principal
    organization: Organization
    membership: Membership

    @property
    def organization_id(self) -> UUID:
        return self.organization.id

    @property
    def reviewer_id(self) -> str:
        return self.principal.reviewer_id

    def can(self, permission: str) -> bool:
        return permission in PERMISSIONS[self.membership.role]


class Authorizer:
    def __init__(self, store: ApplicationStore) -> None:
        self._store = store

    def require(
        self, principal: Principal, organization_id: UUID, permission: str
    ) -> AuthorizedContext:
        if permission not in ALL_PERMISSIONS:
            raise AuthorizationError(f"Unknown permission {permission!r}.")
        organization = self._store.get_organization(organization_id)
        membership = (
            self._store.get_membership(organization_id, principal.subject)
            if organization is not None
            else None
        )
        if organization is None or membership is None:
            raise NotFoundError(
                "The organization does not exist or you are not a member of it.",
                f"No membership for this principal in organization {organization_id}.",
            )
        context = AuthorizedContext(principal, organization, membership)
        if not context.can(permission):
            raise AuthorizationError(
                "This action is not allowed for your role.",
                f"Role {membership.role.value} lacks {permission}.",
                "Ask an administrator of the organization for the reviewer or administrator role.",
            )
        return context
