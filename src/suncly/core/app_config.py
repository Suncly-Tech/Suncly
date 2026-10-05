"""Configuration of the hosted application layer. One frozen object, built once.

Everything a hosted process needs beyond ``core/config.py``: the environment
name, the network mode, identity-provider settings, the pinned model, pricing,
the payment provider and the worker's lease and polling intervals. The loader
in ``adapters/config_loader.py`` reads it from the environment. No secret
value lives here: secrets are referenced by name and resolved by the adapter
that needs them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from suncly.domain.errors import ConfigError
from suncly.domain.tenancy import DeploymentMode
from suncly.ports.model import ModelConfig

Environment = Literal["production", "staging", "development", "test"]

#: The judge's deterministic layer version, bound into every signed payload (OQ-D4).
JUDGE_VERSION = "suncly-judge/2"
#: Model configuration recorded when drafting or judging through Anthropic's API.
DEFAULT_MODEL = ModelConfig(
    provider="anthropic", model="claude-opus-5-5", max_output_tokens=4096, effort="medium"
)


@dataclass(frozen=True)
class AuthConfig:
    """OpenID Connect settings. ``local_auth_enabled`` can never be true in production."""

    issuer: str | None = None
    audience: str | None = None
    jwks_url: str | None = None
    allowed_algorithms: tuple[str, ...] = ("RS256", "ES256")
    local_auth_enabled: bool = False
    local_auth_secret_env: str = "SUNCLY_LOCAL_AUTH_SECRET"  # noqa: S105 - a variable name

    @property
    def oidc_configured(self) -> bool:
        return bool(self.issuer and self.audience and self.jwks_url)


@dataclass(frozen=True)
class BillingConfig:
    provider: Literal["stripe", "fake"] = "fake"
    secret_key_env: str = "STRIPE_SECRET_KEY"  # noqa: S105 - a variable name
    webhook_secret_env: str = "STRIPE_WEBHOOK_SECRET"  # noqa: S105 - a variable name
    allow_live_keys: bool = False
    """Live Stripe keys are refused unless this is set, and never in test environments."""
    plan_catalog_version: str = "2026-10-test"
    checkout_success_url: str = "http://localhost:3100/app/settings?checkout=success"
    checkout_cancel_url: str = "http://localhost:3100/app/settings?checkout=cancelled"
    portal_return_url: str = "http://localhost:3100/app/settings"


@dataclass(frozen=True)
class WorkerConfig:
    lease_seconds: float = 60.0
    heartbeat_seconds: float = 15.0
    poll_seconds: float = 2.0
    max_attempts: int = 3
    retry_base_seconds: float = 5.0
    retry_cap_seconds: float = 300.0
    runner_timeout_s: float = 30.0
    external_tool_timeout_s: float = 900.0
    """Deadline for one external tool run (the TCK or a Promptfoo pack)."""


@dataclass(frozen=True)
class AppConfig:
    environment: Environment = "development"
    network_mode: DeploymentMode = DeploymentMode.PUBLIC
    public_base_url: str = "http://localhost:8000"
    issuer: str = "suncly-local"
    """The attestation issuer name bound into signed payloads and the key registry."""
    attestation_validity_days: int = 90
    auth: AuthConfig = field(default_factory=AuthConfig)
    model: ModelConfig | None = None
    """``None`` means no model provider: model-judged criteria stay inconclusive."""
    model_api_key_env: str = "ANTHROPIC_API_KEY"
    billing: BillingConfig = field(default_factory=BillingConfig)
    worker: WorkerConfig = field(default_factory=WorkerConfig)
    price_table_version: str = "2026-10-test"
    currency: str = "EUR"
    evidence_bucket: str | None = None
    """When set, transcripts live in this object-storage bucket instead of the local disk."""
    a2a_tck_dir: str | None = None
    """A checkout of the pinned A2A TCK (worker only); unset means the tool is unavailable."""
    promptfoo_pack: str | None = None
    """The approved Promptfoo pack the worker runs (worker only); unset means unavailable."""
    promptfoo_bin: str = "promptfoo"
    """The promptfoo executable in the worker image."""
    secret_manager_project: str | None = None
    signing_key_secret: str | None = None
    """Secret Manager resource holding the signing key versions (worker and rotation)."""
    cors_origins: tuple[str, ...] = ("http://localhost:3100", "http://localhost:3000")

    def __post_init__(self) -> None:
        if self.environment == "production":
            if self.auth.local_auth_enabled:
                raise ConfigError(
                    "The local authentication adapter cannot be enabled in production.",
                    "SUNCLY_ENVIRONMENT is production and SUNCLY_LOCAL_AUTH_ENABLED is set.",
                    "Configure the OpenID Connect issuer, audience and JWKS URL instead.",
                )
            if not self.auth.oidc_configured:
                raise ConfigError(
                    "Production needs an identity provider.",
                    "SUNCLY_OIDC_ISSUER, SUNCLY_OIDC_AUDIENCE and SUNCLY_OIDC_JWKS_URL are "
                    "required.",
                )
            if self.network_mode is DeploymentMode.LOCAL:
                raise ConfigError(
                    "Production cannot run in local network mode.",
                    "SUNCLY_NETWORK_MODE=local allows loopback targets, which is never public.",
                )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"
