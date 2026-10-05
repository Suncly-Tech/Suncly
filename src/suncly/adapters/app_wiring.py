"""Builds the hosted ``AppServices`` from configuration and an environment mapping.

This is the composition root of the API and the worker. It is the only
place that turns configuration into adapters, and it hands secrets (an
Anthropic key, Stripe keys, the local auth secret) straight from the
environment mapping to the adapter that needs them. The API never receives
a secret resolver or an executor; the worker does.
"""

from __future__ import annotations

from collections.abc import Mapping

from suncly.adapters.auth import LocalTokenVerifier, OidcTokenVerifier
from suncly.adapters.fake_model import HeuristicJudgeClient
from suncly.adapters.file_keys import FileSigningKeys
from suncly.adapters.file_store import FileEvidenceStore
from suncly.adapters.httpx_card_fetcher import HttpxCardFetcher
from suncly.adapters.local_transcripts import LocalTranscriptStorage
from suncly.adapters.memory_app_store import MemoryApplicationStore
from suncly.adapters.scoped_executor import ScopedSubprocessRunExecutor
from suncly.adapters.secret_keys import (
    SIGNING_KEY_ENV_VAR,
    EnvSigningKeys,
    SecretManagerSigningKeys,
)
from suncly.adapters.secrets import EnvironmentSecrets, NoSecrets, SecretManagerSecrets
from suncly.adapters.stripe_billing import FakeBillingProvider, StripeBillingProvider
from suncly.adapters.system import SystemClock, UuidIds
from suncly.core.app import AppServices, ExternalToolFactory
from suncly.core.app_config import AppConfig
from suncly.core.authz import Authorizer
from suncly.core.billing import BillingService
from suncly.core.config import Config
from suncly.core.contract_builder import DeterministicDrafter
from suncly.core.pricing import plan_catalog, price_table
from suncly.core.usage import UsageService
from suncly.domain.errors import ConfigError
from suncly.domain.network import NetworkPolicy
from suncly.domain.tenancy import AgentRegistration
from suncly.ports.app_store import ApplicationStore
from suncly.ports.billing_provider import BillingProvider
from suncly.ports.external_tools import ExternalToolRunner
from suncly.ports.identity import TokenVerifier
from suncly.ports.model import StructuredModelClient
from suncly.ports.run_executor import RunExecutor
from suncly.ports.secrets import SecretResolver
from suncly.ports.signer import SigningKeys
from suncly.ports.store import EvidenceStore
from suncly.ports.transcripts import TranscriptStorage


def build_stores(config: Config) -> tuple[EvidenceStore, ApplicationStore]:
    if config.uses_postgres:
        from suncly.adapters.postgres.app_store import PostgresApplicationStore
        from suncly.adapters.postgres.store import PostgresEvidenceStore

        assert config.database_url is not None
        return PostgresEvidenceStore(config.database_url), PostgresApplicationStore(
            config.database_url
        )
    return FileEvidenceStore(config.store_dir), MemoryApplicationStore()


def build_transcripts(config: Config, app_config: AppConfig) -> TranscriptStorage:
    if app_config.evidence_bucket:
        from suncly.adapters.gcs_transcripts import GcsTranscriptStorage

        return GcsTranscriptStorage.for_bucket(app_config.evidence_bucket)
    return LocalTranscriptStorage(config.transcripts_dir)


def build_verifiers(app_config: AppConfig, env: Mapping[str, str]) -> list[TokenVerifier]:
    verifiers: list[TokenVerifier] = []
    auth = app_config.auth
    if auth.oidc_configured:
        assert auth.issuer and auth.audience and auth.jwks_url
        verifiers.append(
            OidcTokenVerifier(auth.issuer, auth.audience, auth.jwks_url, auth.allowed_algorithms)
        )
    if auth.local_auth_enabled:
        secret = env.get(auth.local_auth_secret_env, "")
        if not secret:
            raise ConfigError(
                "Local authentication is enabled but no secret is set.",
                f"{auth.local_auth_secret_env} is empty.",
            )
        verifiers.append(LocalTokenVerifier(secret, app_config.environment))
    if not verifiers:
        raise ConfigError(
            "No identity provider is configured.",
            "Set the OIDC settings, or enable local auth outside production.",
        )
    return verifiers


def build_model_client(
    app_config: AppConfig, env: Mapping[str, str]
) -> StructuredModelClient | None:
    if app_config.model is None:
        return None
    if app_config.model.provider == "fake":
        return HeuristicJudgeClient()
    if app_config.model.provider == "anthropic":
        key = env.get(app_config.model_api_key_env, "")
        if not key:
            raise ConfigError(
                "The Anthropic provider is configured without a key.",
                f"{app_config.model_api_key_env} is empty.",
            )
        from suncly.adapters.anthropic_model import AnthropicStructuredClient

        return AnthropicStructuredClient(key)
    raise ConfigError(f"Unknown model provider {app_config.model.provider!r}.")


def build_billing_provider(app_config: AppConfig, env: Mapping[str, str]) -> BillingProvider:
    billing = app_config.billing
    if billing.provider == "fake":
        return FakeBillingProvider(env.get(billing.webhook_secret_env) or "whsec_test_fake_secret")
    secret_key = env.get(billing.secret_key_env, "")
    webhook_secret = env.get(billing.webhook_secret_env, "")
    if not secret_key or not webhook_secret:
        raise ConfigError(
            "Stripe is configured without its keys.",
            f"{billing.secret_key_env} and {billing.webhook_secret_env} are required.",
        )
    allow_live = billing.allow_live_keys and app_config.environment == "production"
    return StripeBillingProvider(secret_key, webhook_secret, allow_live=allow_live)


def build_secret_resolver(app_config: AppConfig, env: Mapping[str, str]) -> SecretResolver:
    if app_config.secret_manager_project:
        return SecretManagerSecrets()
    if app_config.is_production:
        return NoSecrets()
    return EnvironmentSecrets(env)


def build_signing_keys(
    config: Config, app_config: AppConfig, env: Mapping[str, str]
) -> SigningKeys:
    """Secret Manager when configured (rotation-capable), else the platform-filled variable,
    else the CLI's key files under ``SUNCLY_HOME``."""
    if app_config.signing_key_secret:
        return SecretManagerSigningKeys(app_config.signing_key_secret)
    if env.get(SIGNING_KEY_ENV_VAR, "").strip():
        return EnvSigningKeys(env)
    return FileSigningKeys(config.keys_dir)


def build_app_services(
    config: Config,
    app_config: AppConfig,
    env: Mapping[str, str],
    *,
    worker: bool = False,
    stores: tuple[EvidenceStore, ApplicationStore] | None = None,
) -> AppServices:
    store, app_store = stores or build_stores(config)
    clock, ids = SystemClock(), UuidIds()
    table = price_table(app_config.price_table_version)
    price_ids = {
        plan: env[f"STRIPE_PRICE_{plan.upper()}"]
        for plan in ("pilot", "team")
        if env.get(f"STRIPE_PRICE_{plan.upper()}")
    }
    plans = plan_catalog(app_config.billing.plan_catalog_version, price_ids)
    usage = UsageService(app_store, clock, ids, table, plans)
    billing = BillingService(
        app_store,
        build_billing_provider(app_config, env),
        clock,
        plans,
        app_config.billing.checkout_success_url,
        app_config.billing.checkout_cancel_url,
        app_config.billing.portal_return_url,
    )
    policy = NetworkPolicy.for_mode(app_config.network_mode)
    services = AppServices(
        config=config,
        app_config=app_config,
        store=store,
        app_store=app_store,
        transcripts=build_transcripts(config, app_config),
        fetcher=HttpxCardFetcher(config.card_timeout_s, config.card_max_bytes, policy=policy),
        drafter=DeterministicDrafter(),
        keys=build_signing_keys(config, app_config, env),
        clock=clock,
        ids=ids,
        usage=usage,
        billing=billing,
        authorizer=Authorizer(app_store),
        verifiers=build_verifiers(app_config, env),
        model_client=build_model_client(app_config, env),
    )
    if worker:
        resolver = build_secret_resolver(app_config, env)
        base_env = dict(env)

        def factory(registration: AgentRegistration) -> RunExecutor:
            return ScopedSubprocessRunExecutor(
                resolver, registration.credential, registration.deployment_mode, base_env
            )

        services.executor_factory = factory
        services.external_tools = build_external_tools(app_config, resolver, base_env)
    return services


def build_external_tools(
    app_config: AppConfig, resolver: SecretResolver, base_env: Mapping[str, str]
) -> dict[str, ExternalToolFactory]:
    """The external tool runners this worker can provision, by tool name.

    Each factory builds a ``ToolProcess`` scoped to one registration: the
    Runner's minimal environment, the deployment's network mode and, only for
    a tool that needs it to reach the sandbox, the agent credential in the one
    variable that tool is documented to read.
    """
    from pathlib import Path

    from suncly.adapters.external import A2ATckRunner, PromptfooRunner, ToolProcess
    from suncly.adapters.external.process import credential_environment

    def process_for(registration: AgentRegistration, with_credential: bool) -> ToolProcess:
        extra = (
            credential_environment(resolver.resolve(registration.credential))
            if with_credential
            else {}
        )
        return ToolProcess(base_env, registration.deployment_mode, extra)

    tools: dict[str, ExternalToolFactory] = {}
    if app_config.a2a_tck_dir:
        checkout = Path(app_config.a2a_tck_dir)

        def tck(registration: AgentRegistration) -> ExternalToolRunner:
            # The TCK fetches the card and talks to the agent itself; it has no credential
            # option, so it runs without one (a sandbox that requires auth fails its checks).
            return A2ATckRunner(process_for(registration, with_credential=False), checkout)

        tools["a2a-tck"] = tck
    if app_config.promptfoo_pack:
        pack = Path(app_config.promptfoo_pack)
        binary = app_config.promptfoo_bin

        def promptfoo(registration: AgentRegistration) -> ExternalToolRunner:
            return PromptfooRunner(
                process_for(registration, with_credential=True), pack, command=[binary]
            )

        tools["promptfoo"] = promptfoo
    return tools
