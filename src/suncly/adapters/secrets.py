"""Secret resolvers for the Runner-side executor (``ports/secrets.py``).

- ``NoSecrets``: provider ``none`` only; anything else is refused. Wired into
  every process that must never see a credential (API, judge, renderer).
- ``EnvironmentSecrets``: local development; resolves ``env`` references
  against a mapping the composition root passed in.
- ``SecretManagerSecrets``: Google Secret Manager, imported lazily so the
  dependency is optional. The Runner's service identity alone has access to
  the agent-credential secrets (deploy/README.md).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from suncly.domain.errors import RunnerError
from suncly.domain.tenancy import CredentialReference


class NoSecrets:
    def resolve(self, reference: CredentialReference) -> str | None:
        if reference.provider == "none":
            return None
        raise RunnerError(
            "This process cannot resolve credentials.",
            f"A {reference.provider} reference was requested from a component without access.",
        )


class EnvironmentSecrets:
    def __init__(self, environment: Mapping[str, str]) -> None:
        self._env = environment

    def resolve(self, reference: CredentialReference) -> str | None:
        if reference.provider == "none":
            return None
        if reference.provider != "env":
            raise RunnerError(
                "Only environment references are resolvable here.",
                f"Provider {reference.provider} is not configured.",
            )
        value = self._env.get(reference.ref, "").strip()
        if not value:
            raise RunnerError(
                "The referenced environment variable is empty.", f"{reference.ref} is not set."
            )
        return value


AccessSecret = Callable[[str], str]


class SecretManagerSecrets:
    """Google Secret Manager. ``accessor`` is injectable for tests."""

    def __init__(self, accessor: AccessSecret | None = None) -> None:
        self._accessor = accessor or self._default_accessor

    @staticmethod
    def _default_accessor(name: str) -> str:
        try:
            from google.cloud import secretmanager  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - needs the optional extra
            raise RunnerError(
                "Secret Manager support is not installed.",
                "Install suncly[gcp] in the Runner image.",
            ) from exc
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": name})
        return str(response.payload.data.decode("utf-8"))

    def resolve(self, reference: CredentialReference) -> str | None:
        if reference.provider == "none":
            return None
        if reference.provider != "secret-manager":
            raise RunnerError(
                "Only Secret Manager references are resolvable here.",
                f"Provider {reference.provider} is not configured.",
            )
        name = reference.ref
        if "/versions/" not in name:
            name = f"{name}/versions/latest"
        try:
            value = self._accessor(name)
        except RunnerError:
            raise
        except Exception as exc:
            raise RunnerError(
                "The credential could not be read from Secret Manager.",
                f"{type(exc).__name__} while accessing the referenced secret.",
            ) from exc
        if not value.strip():
            raise RunnerError("The referenced secret is empty.", f"{reference.ref} has no value.")
        return value.strip()
