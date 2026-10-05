"""A hosted-product world on fakes: memory application store, local evidence, local tokens.

Shared by the authorization, worker and API tests. Nothing here reaches the
network unless a test hands in a real fetcher or executor factory on purpose.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from suncly.adapters.auth import LocalTokenVerifier, issue_local_token
from suncly.adapters.file_store import FileEvidenceStore
from suncly.adapters.local_transcripts import LocalTranscriptStorage
from suncly.adapters.memory_app_store import MemoryApplicationStore
from suncly.adapters.stripe_billing import FakeBillingProvider
from suncly.core.app import AppServices
from suncly.core.app_config import AppConfig, AuthConfig, WorkerConfig
from suncly.core.authz import AuthorizedContext, Authorizer
from suncly.core.billing import BillingService
from suncly.core.config import Config
from suncly.core.contract_builder import DeterministicDrafter
from suncly.core.jobs import WorkerLoop
from suncly.core.pricing import TEST_PRICE_TABLE, plan_catalog
from suncly.core.reevaluation import ReevaluationJobHandler
from suncly.core.usage import UsageService
from suncly.core.worker import AttestationJobHandler
from suncly.domain.tenancy import DeploymentMode, Membership, Organization, Principal, Role
from suncly.ports.card_fetcher import CardFetcher
from suncly.ports.model import StructuredModelClient
from suncly.ports.run_executor import RunExecutor
from suncly.ports.signer import SigningKeys
from tests.fakes import FakeClock, MemorySigningKeys, SeqIds, StaticFetcher, passing_executor

LOCAL_SECRET = "local-test-secret-with-enough-length"
ISSUER = "suncly-test"


@dataclass
class HostedWorld:
    services: AppServices
    clock: FakeClock
    ids: SeqIds
    secret: str = LOCAL_SECRET

    # -- identities -------------------------------------------------------------------

    def token(self, subject: str, email: str | None = None) -> str:
        return issue_local_token(self.secret, subject, email or f"{subject}@example.test", subject)

    def principal(self, subject: str) -> Principal:
        return self.services.verifiers[0].verify(self.token(subject))

    def organization(
        self,
        slug: str,
        members: dict[str, Role],
        max_concurrent_jobs: int = 2,
        subscribed: bool = True,
    ) -> Organization:
        organization = Organization(
            id=self.ids.new_id(),
            slug=slug,
            name=slug.title(),
            created_at=self.clock.now(),
            max_concurrent_jobs=max_concurrent_jobs,
        )
        self.services.app_store.add_organization(organization)
        for subject, role in members.items():
            self.services.app_store.add_membership(
                Membership(
                    id=self.ids.new_id(),
                    organization_id=organization.id,
                    subject=subject,
                    email=f"{subject}@example.test",
                    role=role,
                    created_at=self.clock.now(),
                )
            )
        if subscribed:
            self.subscribe(organization)
        return organization

    def subscribe(
        self, organization: Organization, plan_id: str = "pilot", status: Any = None
    ) -> None:
        """An entitled test-plan subscription, as a verified checkout webhook would record it."""
        from suncly.domain.billing import Subscription, SubscriptionStatus

        now = self.clock.now()
        self.services.app_store.upsert_subscription(
            Subscription(
                organization_id=organization.id,
                plan_id=plan_id,
                status=status or SubscriptionStatus.ACTIVE,
                provider="fake",
                provider_customer_id=f"cus_{organization.slug}",
                provider_subscription_id=f"sub_{organization.slug}",
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                provider_updated_at=now,
                updated_at=now,
            )
        )

    def context(self, subject: str, organization_id: UUID, permission: str) -> AuthorizedContext:
        return self.services.authorizer.require(
            self.principal(subject), organization_id, permission
        )

    # -- the worker ---------------------------------------------------------------------

    def worker(self, worker_id: str = "worker-1", log: list[str] | None = None) -> WorkerLoop:
        services = self.services
        return WorkerLoop(
            services.app_store,
            services.clock,
            services.app_config.worker,
            [AttestationJobHandler(services), ReevaluationJobHandler(services)],
            worker_id,
            on_log=(log.append if log is not None else None),
        )


def build_world(
    tmp_path: Path,
    *,
    fetcher: CardFetcher | None = None,
    executor_factory: Callable[[Any], RunExecutor] | None = None,
    model_client: StructuredModelClient | None = None,
    keys: SigningKeys | None = None,
    network_mode: DeploymentMode = DeploymentMode.LOCAL,
    runs: int = 2,
    worker: WorkerConfig | None = None,
    clock: FakeClock | None = None,
    model: Any | None = None,
) -> HostedWorld:
    clock = clock or FakeClock()
    ids = SeqIds()
    config = Config(
        home=tmp_path / "home",
        reports_dir=tmp_path / "reports",
        runs=runs,
        run_timeout_s=5.0,
        latency_limit_ms=5000,
        max_retries=1,
        concurrency=2,
        poll_interval_s=0.01,
    )
    app_config = AppConfig(
        environment="test",
        network_mode=network_mode,
        issuer=ISSUER,
        auth=AuthConfig(local_auth_enabled=True),
        model=model,
        worker=worker
        or WorkerConfig(
            lease_seconds=60.0,
            heartbeat_seconds=0.05,
            poll_seconds=0.01,
            max_attempts=3,
            retry_base_seconds=1.0,
            retry_cap_seconds=8.0,
        ),
    )
    app_store = MemoryApplicationStore()
    plans = plan_catalog(
        app_config.billing.plan_catalog_version,
        {"pilot": "price_test_pilot", "team": "price_test_team"},
    )
    usage = UsageService(app_store, clock, ids, TEST_PRICE_TABLE, plans)
    billing = BillingService(
        app_store,
        FakeBillingProvider(),
        clock,
        plans,
        "http://localhost:3100/ok",
        "http://localhost:3100/cancel",
        "http://localhost:3100/portal",
    )
    services = AppServices(
        config=config,
        app_config=app_config,
        store=FileEvidenceStore(config.store_dir),
        app_store=app_store,
        transcripts=LocalTranscriptStorage(config.transcripts_dir),
        fetcher=fetcher or StaticFetcher({}, clock),
        drafter=DeterministicDrafter(),
        keys=keys or MemorySigningKeys(),
        clock=clock,
        ids=ids,
        usage=usage,
        billing=billing,
        authorizer=Authorizer(app_store),
        verifiers=[LocalTokenVerifier(LOCAL_SECRET, "test")],
        model_client=model_client,
        executor_factory=executor_factory or (lambda registration: passing_executor(clock)),
    )
    return HostedWorld(services=services, clock=clock, ids=ids)


# -- the customer workflow on services, without HTTP -----------------------------------


def prepare_attestation(
    world: HostedWorld,
    subject: str,
    organization: Organization,
    card_url: str,
    *,
    risk_level: Any = None,
    sandbox_idempotent: bool = False,
    runs: int = 2,
    budget_limit: Any = None,
) -> tuple[Any, Any, Any]:
    """Register, draft, approve and start: returns (registration, contract detail, view)."""
    from suncly.core.attestations_app import AttestationWorkflow, StartAttestationRequest
    from suncly.core.contracts_app import ContractWorkflow, DraftSource
    from suncly.core.registry import AgentRegistry, RegisterAgentRequest
    from suncly.domain.models import RiskLevel
    from suncly.domain.tenancy import CredentialReference

    ctx = world.context(subject, organization.id, "agents:write")
    registration = AgentRegistry(world.services).register(
        ctx,
        RegisterAgentRequest(
            name="Sandbox agent",
            card_url=card_url,
            risk_level=risk_level or RiskLevel.LOW,
            owner="team",
            sandbox_declared=True,
            credential=CredentialReference(provider="none"),
            sandbox_idempotent=sandbox_idempotent,
        ),
    )
    contracts = ContractWorkflow(world.services)
    detail = contracts.draft(ctx, registration.id, DraftSource(kind="deterministic"))
    detail = contracts.approve(ctx, detail.contract.id)
    view = AttestationWorkflow(world.services).start(
        ctx,
        StartAttestationRequest(
            registration_id=registration.id,
            contract_id=detail.contract.id,
            runs=runs,
            budget_limit=budget_limit,
        ),
    )
    return registration, detail, view
