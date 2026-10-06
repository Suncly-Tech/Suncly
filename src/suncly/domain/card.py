"""Agent Card parsing and hashing.

Field names follow the A2A specification v1.0.1 (docs/ARCHITECTURE.md: A2A
protocol dependencies). Unrecognized fields are kept, because the spec says
implementations should ignore them (A2A §5.7), and ``raw_json`` is stored
exactly as fetched (docs/DATA_MODEL.md: card_version).
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from suncly.domain.canonical import canonical_sha256
from suncly.domain.errors import CardNotParsableError
from suncly.domain.models import JsonObject

#: The field excluded from the hash, as A2A §8.4.1 excludes it from signing (OQ-A7, proposal).
SIGNATURES_FIELD = "signatures"

#: Top-level fields of the pre-1.0 Agent Card format (A2A v0.3.0 §5.6.1: ``url`` and
#: ``preferredTransport`` were REQUIRED, ``protocolVersion`` was a top-level string).
#: In 1.0 all three live inside ``supportedInterfaces`` entries. Used only to name the
#: cause when such a card is refused; Suncly speaks no 0.3 (OQ-A4).
LEGACY_CARD_FIELDS = ("url", "preferredTransport", "protocolVersion")

#: Agent Card fields the specification marks REQUIRED (A2A §4.4.1).
SPEC_REQUIRED_CARD_FIELDS = (
    "name",
    "description",
    "supportedInterfaces",
    "version",
    "capabilities",
    "defaultInputModes",
    "defaultOutputModes",
    "skills",
)


class CardModel(BaseModel):
    """Lenient base: camelCase aliases, unknown fields kept."""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="allow", frozen=True
    )


class AgentInterface(CardModel):
    """One entry of ``supportedInterfaces`` (A2A §4.4.6)."""

    url: str = Field(min_length=1)
    protocol_binding: str = Field(min_length=1)
    protocol_version: str = Field(min_length=1)
    tenant: str | None = None


class AgentCapabilities(CardModel):
    """``capabilities`` (A2A §4.4.3). All fields are optional in the spec."""

    streaming: bool | None = None
    push_notifications: bool | None = None
    extended_agent_card: bool | None = None
    extensions: list[Any] | None = None


class AgentSkill(CardModel):
    """One declared skill (A2A §4.4.5)."""

    id: str = Field(min_length=1)
    name: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    examples: list[str] | None = None
    input_modes: list[str] | None = None
    output_modes: list[str] | None = None
    security_requirements: list[Any] | None = None


class AgentCard(CardModel):
    """The parts of an Agent Card that Suncly reads (A2A §4.4.1)."""

    name: str = Field(min_length=1)
    description: str = ""
    version: str = ""
    supported_interfaces: list[AgentInterface] = Field(min_length=1)
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    default_input_modes: list[str] = Field(default_factory=list)
    default_output_modes: list[str] = Field(default_factory=list)
    skills: list[AgentSkill] = Field(default_factory=list)

    def skill_ids(self) -> list[str]:
        return [skill.id for skill in self.skills]

    def output_modes_for(self, skill: AgentSkill) -> list[str]:
        """The media types a skill answers in: its own list, else the card default."""
        return list(skill.output_modes or self.default_output_modes)


class ParsedCard(BaseModel):
    """A card as fetched, as JSON, as a model, and its hash."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    raw_json: str
    json_object: JsonObject
    card: AgentCard
    card_hash: str

    def missing_required_fields(self) -> list[str]:
        """Fields the spec requires that this card omits. Reported, never invented."""
        return [name for name in SPEC_REQUIRED_CARD_FIELDS if name not in self.json_object]


def compute_card_hash(card_json: JsonObject) -> str:
    """``card_hash``: SHA-256 of the RFC 8785 form of the card without ``signatures``.

    Proposal for OQ-A7. Re-signing an unchanged card therefore keeps its hash.
    """
    without_signatures = {k: v for k, v in card_json.items() if k != SIGNATURES_FIELD}
    return canonical_sha256(without_signatures)


def legacy_card_markers(card_json: JsonObject) -> list[str]:
    """The pre-1.0 top-level fields a card carries instead of ``supportedInterfaces``.

    Empty for every card that declares ``supportedInterfaces``, including the hybrid
    cards that 1.x SDKs serve in 0.3 compatibility mode.
    """
    if "supportedInterfaces" in card_json:
        return []
    return [name for name in LEGACY_CARD_FIELDS if name in card_json]


def parse_agent_card(raw_json: str) -> ParsedCard:
    """Parse the text of an Agent Card. Fails visibly on anything unusable (OQ-A11)."""
    try:
        loaded = json.loads(raw_json)
    except ValueError as exc:
        raise CardNotParsableError(
            "The Agent Card is not valid JSON.",
            f"The parser reported: {exc}.",
            "Check the card URL serves the card itself, not an HTML page or an error.",
        ) from exc
    if not isinstance(loaded, dict):
        raise CardNotParsableError(
            "The Agent Card is not a JSON object.",
            f"The document is a JSON {type(loaded).__name__}.",
            "An Agent Card is a JSON object with name, skills and supportedInterfaces.",
        )
    try:
        card = AgentCard.model_validate(loaded)
    except ValidationError as exc:
        markers = legacy_card_markers(loaded)
        if markers:
            declared = loaded.get("protocolVersion")
            version = f"protocolVersion {declared!r}" if declared else "no protocolVersion"
            raise CardNotParsableError(
                "The Agent Card uses the pre-1.0 A2A card format, which Suncly does not speak.",
                f"It declares {version} and the top-level field(s) {', '.join(markers)} instead "
                "of supportedInterfaces (A2A 1.0, §8.3).",
                "Suncly attests A2A 1.0 interfaces only (OQ-A4). Serve a 1.0 Agent Card with a "
                "JSONRPC 1.0 interface.",
            ) from exc
        problems = "; ".join(
            f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}" for error in exc.errors()
        )
        raise CardNotParsableError(
            "The Agent Card does not have the structure Suncly needs.",
            f"Validation reported: {problems}.",
            "The card needs a name, at least one entry in supportedInterfaces, and a skills list.",
        ) from exc
    try:
        card_hash = compute_card_hash(loaded)
    except Exception as exc:  # rfc8785 raises its own hierarchy
        raise CardNotParsableError(
            "The Agent Card cannot be canonicalized.",
            f"RFC 8785 canonicalization failed: {exc}.",
            "Remove non-JSON values such as NaN or Infinity from the card.",
        ) from exc
    return ParsedCard(raw_json=raw_json, json_object=loaded, card=card, card_hash=card_hash)
