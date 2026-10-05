"""Scoped secret delivery for the Runner (DR-003, OQ-P4).

A ``SecretResolver`` turns a ``CredentialReference`` into a value. Only the
Runner-side executor holds one; the API, the Judge and the report renderer are
wired without it, and the hosted deployment gives only the Runner's service
identity access to agent-credential secrets (deploy/README.md).
"""

from __future__ import annotations

from typing import Protocol

from suncly.domain.tenancy import CredentialReference


class SecretResolver(Protocol):
    def resolve(self, reference: CredentialReference) -> str | None:
        """The secret value, or ``None`` for provider ``none``. Raises ``RunnerError``."""
        ...
