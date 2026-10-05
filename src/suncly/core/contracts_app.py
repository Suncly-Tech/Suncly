"""The contract review workflow: draft, view, reject, approve (SCHEMA.md §2, §4).

Drafting fetches the card through the deployment's network policy, records
the card version, and builds a draft from one of four sources: the
deterministic drafter, the model drafter, a behavioural suite the customer
wrote, or a format 1 contract file. The draft is stored as a contract with
status ``draft``. Approval records the authenticated reviewer's identity;
nothing in a request body can name the approver.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from suncly.core.app import AppServices
from suncly.core.authz import AuthorizedContext
from suncly.core.cards import CardService
from suncly.core.contract_builder import (
    ContractService,
    contract_content_hash,
    draft_from_contract_file,
    uncovered_skills,
)
from suncly.core.model_drafter import ModelDrafter, draft_from_suite
from suncly.core.registry import AgentRegistry
from suncly.domain.behavioral import BehavioralSuite, render_behavioral_suite
from suncly.domain.card import ParsedCard
from suncly.domain.contract_file import ContractFile
from suncly.domain.errors import ConflictError, NotFoundError, StoreError, TranscriptExistsError
from suncly.domain.ledger import UsageOperation, UsageOutcome
from suncly.domain.models import CardVersion, Contract, ContractStatus, TestCase
from suncly.domain.tenancy import AgentRegistration
from suncly.ports.drafter import Draft, DraftSettings, NotTestableSkill
from suncly.ports.model import StructuredResponse


@dataclass(frozen=True)
class DraftSource:
    kind: str
    """``deterministic``, ``model``, ``suite`` or ``contract_file``."""
    suite: BehavioralSuite | None = None
    contract_file: ContractFile | None = None


@dataclass(frozen=True)
class ContractDetail:
    contract: Contract
    test_cases: list[TestCase]
    card_version: CardVersion
    registration: AgentRegistration
    parsed: ParsedCard
    not_testable: list[NotTestableSkill]
    uncovered_skills: list[str]
    content_hash: str
    source: str
    suite: BehavioralSuite | None = None


class ContractWorkflow:
    def __init__(self, services: AppServices) -> None:
        self._s = services
        self._registry = AgentRegistry(services)

    # -- drafting -------------------------------------------------------------------

    def draft(
        self, ctx: AuthorizedContext, registration_id: UUID, source: DraftSource
    ) -> ContractDetail:
        s = self._s
        registration = self._registry.get(ctx, registration_id)
        if not registration.active:
            raise ConflictError("The registration is archived.", "Archived agents are not drafted.")
        agent = s.store.get_agent(registration.agent_id)
        if agent is None:
            raise StoreError("The registration references an agent that does not exist.")
        cards = CardService(s.fetcher, s.store, s.clock, s.ids)
        fetched, parsed = cards.fetch_and_parse(registration.card_url)
        cards.require_attestable(parsed)
        card_version = cards.ensure_card_version(agent, fetched, parsed)
        settings = DraftSettings(
            latency_limit_ms=s.config.latency_limit_ms,
            max_test_cases_per_skill=s.config.max_test_cases_per_skill,
        )
        suite: BehavioralSuite | None = None
        if source.kind == "model":
            draft, suite, name = self._model_draft(ctx, registration, parsed, settings)
        elif source.kind == "suite" and source.suite is not None:
            draft = draft_from_suite(source.suite, parsed)
            suite, name = source.suite, f"behavioral-suite/{source.suite.suite_version}"
        elif source.kind == "contract_file" and source.contract_file is not None:
            draft = draft_from_contract_file(source.contract_file, parsed)
            name = "contract-file/1"
        else:
            draft = s.drafter.draft(parsed.card, settings)
            name = s.drafter.name
        contracts = ContractService(s.store, s.clock, s.ids)
        existing = contracts.latest_draft_with_content(card_version.id, draft)
        contract, test_cases = existing or contracts.create_draft(card_version.id, draft)
        if suite is not None and existing is None:
            try:
                s.transcripts.put(
                    f"contracts/{contract.id}/suite.json",
                    render_behavioral_suite(suite).encode("utf-8"),
                )
            except TranscriptExistsError:
                pass
        return ContractDetail(
            contract=contract,
            test_cases=test_cases,
            card_version=card_version,
            registration=registration,
            parsed=parsed,
            not_testable=draft.not_testable,
            uncovered_skills=uncovered_skills(parsed.card, test_cases),
            content_hash=contract_content_hash(test_cases),
            source=name,
            suite=suite,
        )

    def _model_draft(
        self,
        ctx: AuthorizedContext,
        registration: AgentRegistration,
        parsed: ParsedCard,
        settings: DraftSettings,
    ) -> tuple[Draft, BehavioralSuite, str]:
        s = self._s
        if s.model_client is None or s.app_config.model is None:
            raise ConflictError(
                "No model provider is configured for drafting.",
                "The deployment has no model configuration.",
                "Use the deterministic drafter, or upload a behavioural suite.",
            )

        def record(response: StructuredResponse) -> None:
            s.usage.record_model_call(
                organization_id=ctx.organization_id,
                attestation_id=None,
                execution_attempt_id=None,
                reservation_id=None,
                provider=s.app_config.model.provider if s.app_config.model else "unknown",
                model=response.model or (s.app_config.model.model if s.app_config.model else ""),
                operation=UsageOperation.DRAFT,
                usage=response.usage,
                outcome=UsageOutcome.SETTLED if response.ok else UsageOutcome.FAILED,
                byok=registration.bring_your_own_model_key,
                note=f"drafting for registration {registration.id}",
            )

        drafter = ModelDrafter(s.model_client, s.app_config.model, on_response=record)
        suite = drafter.draft_suite(parsed, settings)
        return draft_from_suite(suite, parsed), suite, drafter.name

    # -- reading ----------------------------------------------------------------------

    def get(self, ctx: AuthorizedContext, contract_id: UUID) -> ContractDetail:
        s = self._s
        contract = s.store.get_contract(contract_id)
        card_version = s.store.get_card_version(contract.card_version_id) if contract else None
        if contract is None or card_version is None:
            raise NotFoundError(
                "The contract does not exist in this organization.", f"No contract {contract_id}."
            )
        registration = self._registry.by_agent(ctx, card_version.agent_id)
        from suncly.domain.card import parse_agent_card

        parsed = parse_agent_card(card_version.raw_json)
        test_cases = s.store.list_test_cases(contract.id)
        return ContractDetail(
            contract=contract,
            test_cases=test_cases,
            card_version=card_version,
            registration=registration,
            parsed=parsed,
            not_testable=[],
            uncovered_skills=uncovered_skills(parsed.card, test_cases),
            content_hash=contract_content_hash(test_cases),
            source="stored",
            suite=self._load_suite(contract.id),
        )

    def _load_suite(self, contract_id: UUID) -> BehavioralSuite | None:
        key = f"contracts/{contract_id}/suite.json"
        if not self._s.transcripts.exists(key):
            return None
        from suncly.domain.behavioral import parse_behavioral_suite

        return parse_behavioral_suite(self._s.transcripts.get(key).decode("utf-8"))

    def list_for_agent(self, ctx: AuthorizedContext, registration_id: UUID) -> list[Contract]:
        registration = self._registry.get(ctx, registration_id)
        contracts: list[Contract] = []
        agent = self._s.store.get_agent(registration.agent_id)
        if agent is None:
            return contracts
        # Card versions are reached through the attestations and contracts of the agent.
        seen: set[UUID] = set()
        for card_version_id in self._card_version_ids(agent.id):
            if card_version_id in seen:
                continue
            seen.add(card_version_id)
            contracts.extend(self._s.store.list_contracts(card_version_id))
        return sorted(contracts, key=lambda c: (c.created_at, c.version))

    def _card_version_ids(self, agent_id: UUID) -> list[UUID]:
        return [cv.id for cv in self._s.store.list_card_versions(agent_id)]

    # -- decisions on drafts -------------------------------------------------------------

    def approve(self, ctx: AuthorizedContext, contract_id: UUID) -> ContractDetail:
        detail = self.get(ctx, contract_id)
        if detail.contract.status is not ContractStatus.DRAFT:
            raise ConflictError(
                "Only a draft contract can be approved.",
                f"Contract {contract_id} is {detail.contract.status.value}.",
                "Draft a new version to change an approved contract (schema §2).",
            )
        approved = ContractService(self._s.store, self._s.clock, self._s.ids).approve(
            detail.contract, ctx.reviewer_id
        )
        return ContractDetail(**{**detail.__dict__, "contract": approved})

    def reject(self, ctx: AuthorizedContext, contract_id: UUID) -> ContractDetail:
        detail = self.get(ctx, contract_id)
        if detail.contract.status is not ContractStatus.DRAFT:
            raise ConflictError(
                "Only a draft contract can be rejected.",
                f"Contract {contract_id} is {detail.contract.status.value}.",
            )
        rejected = self._s.store.reject_contract(contract_id)
        return ContractDetail(**{**detail.__dict__, "contract": rejected})
