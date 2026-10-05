"""Reads the hosted application configuration from the environment (``core/app_config.py``).

Only names and non-secret settings are read here. Secrets stay in the
environment mapping and are handed to adapters by ``adapters/app_wiring.py``.
"""

from __future__ import annotations

from collections.abc import Mapping

from suncly.core.app_config import (
    DEFAULT_MODEL,
    AppConfig,
    AuthConfig,
    BillingConfig,
    Environment,
    WorkerConfig,
)
from suncly.domain.errors import ConfigError
from suncly.domain.tenancy import DeploymentMode
from suncly.ports.model import ModelConfig

ENVIRONMENTS: tuple[Environment, ...] = ("production", "staging", "development", "test")


def _flag(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw = env.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _text(env: Mapping[str, str], name: str, default: str) -> str:
    raw = env.get(name, "").strip()
    return raw or default


def _number(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"The setting {name} is not a number.", f"Its value is {raw!r}.") from exc


def load_app_config(env: Mapping[str, str]) -> AppConfig:
    environment = _text(env, "SUNCLY_ENVIRONMENT", "development")
    if environment not in ENVIRONMENTS:
        raise ConfigError(
            "SUNCLY_ENVIRONMENT is not a known environment.",
            f"Got {environment!r}; use one of {', '.join(ENVIRONMENTS)}.",
        )
    mode_raw = _text(env, "SUNCLY_NETWORK_MODE", "public")
    try:
        network_mode = DeploymentMode(mode_raw)
    except ValueError as exc:
        raise ConfigError(
            "SUNCLY_NETWORK_MODE is not a known mode.",
            f"Got {mode_raw!r}; use public, private_network or local.",
        ) from exc
    model: ModelConfig | None = None
    provider = _text(env, "SUNCLY_MODEL_PROVIDER", "")
    if provider:
        model = ModelConfig(
            provider=provider,
            model=_text(env, "SUNCLY_MODEL", DEFAULT_MODEL.model),
            max_output_tokens=int(_number(env, "SUNCLY_MODEL_MAX_OUTPUT_TOKENS", 4096)),
            effort=_text(env, "SUNCLY_MODEL_EFFORT", "medium") or None,
            timeout_s=_number(env, "SUNCLY_MODEL_TIMEOUT_S", 60.0),
        )
    billing_provider = _text(env, "SUNCLY_BILLING_PROVIDER", "fake")
    if billing_provider not in ("stripe", "fake"):
        raise ConfigError("SUNCLY_BILLING_PROVIDER must be stripe or fake.")
    cors = tuple(
        origin.strip() for origin in env.get("SUNCLY_CORS_ORIGINS", "").split(",") if origin.strip()
    ) or ("http://localhost:3100", "http://localhost:3000")
    return AppConfig(
        environment=environment,
        network_mode=network_mode,
        public_base_url=_text(env, "SUNCLY_PUBLIC_BASE_URL", "http://localhost:8000"),
        issuer=_text(env, "SUNCLY_ISSUER", "suncly-local"),
        attestation_validity_days=int(_number(env, "SUNCLY_ATTESTATION_VALIDITY_DAYS", 90)),
        auth=AuthConfig(
            issuer=env.get("SUNCLY_OIDC_ISSUER") or None,
            audience=env.get("SUNCLY_OIDC_AUDIENCE") or None,
            jwks_url=env.get("SUNCLY_OIDC_JWKS_URL") or None,
            local_auth_enabled=_flag(env, "SUNCLY_LOCAL_AUTH_ENABLED"),
        ),
        model=model,
        billing=BillingConfig(
            provider=billing_provider,  # type: ignore[arg-type]
            allow_live_keys=_flag(env, "SUNCLY_STRIPE_ALLOW_LIVE_KEYS"),
            checkout_success_url=_text(
                env, "SUNCLY_CHECKOUT_SUCCESS_URL", BillingConfig().checkout_success_url
            ),
            checkout_cancel_url=_text(
                env, "SUNCLY_CHECKOUT_CANCEL_URL", BillingConfig().checkout_cancel_url
            ),
            portal_return_url=_text(
                env, "SUNCLY_PORTAL_RETURN_URL", BillingConfig().portal_return_url
            ),
        ),
        worker=WorkerConfig(
            lease_seconds=_number(env, "SUNCLY_WORKER_LEASE_S", 60.0),
            heartbeat_seconds=_number(env, "SUNCLY_WORKER_HEARTBEAT_S", 15.0),
            poll_seconds=_number(env, "SUNCLY_WORKER_POLL_S", 2.0),
            max_attempts=int(_number(env, "SUNCLY_JOB_MAX_ATTEMPTS", 3)),
            external_tool_timeout_s=_number(env, "SUNCLY_EXTERNAL_TOOL_TIMEOUT_S", 900.0),
        ),
        price_table_version=_text(env, "SUNCLY_PRICE_TABLE_VERSION", "2026-10-test"),
        evidence_bucket=env.get("SUNCLY_EVIDENCE_BUCKET") or None,
        a2a_tck_dir=_text(env, "SUNCLY_A2A_TCK_DIR", "") or None,
        a2a_tck_python=_text(env, "SUNCLY_A2A_TCK_PYTHON", "") or None,
        promptfoo_pack=_text(env, "SUNCLY_PROMPTFOO_PACK", "") or None,
        promptfoo_bin=_text(env, "SUNCLY_PROMPTFOO_BIN", "promptfoo"),
        secret_manager_project=env.get("SUNCLY_SECRET_MANAGER_PROJECT") or None,
        signing_key_secret=env.get("SUNCLY_SIGNING_KEY_SECRET") or None,
        cors_origins=cors,
    )
