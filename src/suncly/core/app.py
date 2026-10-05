"""The service bundle every hosted process (API, worker) runs on.

Built once by ``adapters/app_wiring.py``. The API gets no ``RunExecutor`` and
no ``SecretResolver``: it cannot run anything or read any agent credential.
The worker gets an executor factory that provisions one scoped executor per
registration.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from suncly.core.app_config import AppConfig
from suncly.core.authz import Authorizer
from suncly.core.billing import BillingService
from suncly.core.config import Config
from suncly.core.usage import UsageService
from suncly.domain.tenancy import AgentRegistration
from suncly.ports.app_store import ApplicationStore
from suncly.ports.card_fetcher import CardFetcher
from suncly.ports.clock import Clock, IdGenerator
from suncly.ports.drafter import ContractDrafter
from suncly.ports.external_tools import ExternalToolRunner
from suncly.ports.identity import TokenVerifier
from suncly.ports.model import StructuredModelClient
from suncly.ports.run_executor import RunExecutor
from suncly.ports.signer import SigningKeys
from suncly.ports.store import EvidenceStore
from suncly.ports.transcripts import TranscriptStorage

ExecutorFactory = Callable[[AgentRegistration], RunExecutor]


@dataclass
class AppServices:
    config: Config
    app_config: AppConfig
    store: EvidenceStore
    app_store: ApplicationStore
    transcripts: TranscriptStorage
    fetcher: CardFetcher
    drafter: ContractDrafter
    keys: SigningKeys
    clock: Clock
    ids: IdGenerator
    usage: UsageService
    billing: BillingService
    authorizer: Authorizer
    verifiers: list[TokenVerifier] = field(default_factory=list)
    model_client: StructuredModelClient | None = None
    executor_factory: ExecutorFactory | None = None
    """Present only in the worker."""
    external_tools: dict[str, ExternalToolRunner] = field(default_factory=dict)
    """External evaluation adapters available to the worker, by tool name."""

    def close(self) -> None:
        self.store.close()
        self.app_store.close()
