"""Card handling: fetch, parse, hash, and the agent and card_version records.

Schema §4, step 2. The component doing this is proposed to be the
Orchestrator (OQ-A7); it is kept in its own module so the proposal is easy to
move.
"""

from __future__ import annotations

import uuid

from suncly.domain.a2a import BINDING_JSONRPC, PROTOCOL_VERSION
from suncly.domain.card import AgentInterface, ParsedCard, parse_agent_card
from suncly.domain.errors import CardNotAttestableError
from suncly.domain.models import Agent, CardVersion, RiskLevel
from suncly.ports.card_fetcher import CardFetcher, FetchedCard
from suncly.ports.clock import Clock, IdGenerator
from suncly.ports.store import EvidenceStore

#: Namespace for deriving a stable ``agent.id`` from a card URL (OQ-P2, OQ-P5: NEEDS DECISION).
#: Nothing outside the seven entities is stored: the id is recomputed from the URL.
AGENT_ID_NAMESPACE = uuid.UUID("5d7f4a3e-8c2b-4e1a-9f6d-2b7c1e0a9d3f")


def agent_id_for_url(card_url: str) -> uuid.UUID:
    """The ``agent.id`` Suncly uses for an agent known only by its card URL."""
    return uuid.uuid5(AGENT_ID_NAMESPACE, card_url.strip())


def select_interface(parsed: ParsedCard) -> AgentInterface:
    """The first ``supportedInterfaces`` entry Suncly speaks (A2A §8.3.2; OQ-A4, proposal).

    This version speaks protocol 1.0 over JSON-RPC only.
    """
    for interface in parsed.card.supported_interfaces:
        if (
            interface.protocol_binding == BINDING_JSONRPC
            and interface.protocol_version == PROTOCOL_VERSION
        ):
            return interface
    offered = ", ".join(
        f"{i.protocol_binding} {i.protocol_version}" for i in parsed.card.supported_interfaces
    )
    raise CardNotAttestableError(
        "The Agent Card offers no interface Suncly can use.",
        f"Suncly speaks A2A {PROTOCOL_VERSION} over {BINDING_JSONRPC}; the card offers: {offered}.",
        "Add a JSONRPC interface with protocolVersion 1.0 to the card, or wait for another "
        "binding (OQ-A4).",
    )


class CardService:
    """Fetches and records Agent Cards."""

    def __init__(
        self, fetcher: CardFetcher, store: EvidenceStore, clock: Clock, ids: IdGenerator
    ) -> None:
        self._fetcher = fetcher
        self._store = store
        self._clock = clock
        self._ids = ids

    def fetch_and_parse(self, card_url: str) -> tuple[FetchedCard, ParsedCard]:
        """Fetch the card and parse it. Raises ``CardError`` subclasses; records nothing."""
        fetched = self._fetcher.fetch(card_url)
        parsed = parse_agent_card(fetched.raw_json)
        return fetched, parsed

    @staticmethod
    def require_attestable(parsed: ParsedCard) -> None:
        """A card with no skills is reported as not attestable (OQ-A11; A2A-T5)."""
        if not parsed.card.skills:
            raise CardNotAttestableError(
                "The Agent Card declares no skills, so there is nothing to attest.",
                "Suncly tests declared skills; this card's skills list is empty.",
                "Add the agent's skills to its card and run again.",
            )

    def ensure_agent(
        self, card_url: str, parsed: ParsedCard, owner: str, risk_level: RiskLevel
    ) -> Agent:
        """The agent record for this card URL, created on first sight (OQ-P2, proposal)."""
        agent_id = agent_id_for_url(card_url)
        existing = self._store.get_agent(agent_id)
        if existing is not None:
            return existing
        agent = Agent(id=agent_id, name=parsed.card.name, owner=owner, risk_level=risk_level)
        self._store.add_agent(agent)
        return agent

    def ensure_card_version(
        self, agent: Agent, fetched: FetchedCard, parsed: ParsedCard
    ) -> CardVersion:
        """The card version with this hash, reused when seen before (OQ-D9, proposal)."""
        existing = self._store.find_card_version(agent.id, parsed.card_hash)
        if existing is not None:
            return existing
        card_version = CardVersion(
            id=self._ids.new_id(),
            agent_id=agent.id,
            card_hash=parsed.card_hash,
            raw_json=fetched.raw_json,
            fetched_at=fetched.fetched_at,
        )
        self._store.add_card_version(card_version)
        return card_version
