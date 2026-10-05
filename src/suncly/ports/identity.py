"""Identity: verifying a bearer token into a ``Principal`` (OQ-P3).

Suncly builds no identity system (SCHEMA.md §10). An established OpenID
Connect provider issues the tokens; the adapter validates issuer, audience,
expiry and the signature against the provider's published keys. A local
adapter exists for tests and development only and refuses to load in
production.
"""

from __future__ import annotations

from typing import Protocol

from suncly.domain.tenancy import Principal


class TokenVerifier(Protocol):
    name: str

    def verify(self, token: str) -> Principal:
        """Return the principal, or raise ``AuthenticationError``."""
        ...
