"""Agent Card parsing and hashing (OQ-A7 proposal; A2A v1.0.1 field names)."""

from __future__ import annotations

import json

import pytest

from suncly.core.cards import agent_id_for_url, select_interface
from suncly.domain.card import compute_card_hash, parse_agent_card
from suncly.domain.errors import CardNotAttestableError, CardNotParsableError
from tests.fakes import card_json, card_text


def test_identical_cards_with_different_key_order_and_whitespace_hash_the_same() -> None:
    card = card_json()
    a = json.dumps(card, indent=4)
    b = json.dumps(dict(reversed(list(card.items()))), separators=(",", ":"))
    assert parse_agent_card(a).card_hash == parse_agent_card(b).card_hash
    assert parse_agent_card(a).raw_json == a, "raw_json is kept exactly as fetched"


def test_a_changed_value_changes_the_hash() -> None:
    assert (
        parse_agent_card(card_text(name="A")).card_hash
        != parse_agent_card(card_text(name="B")).card_hash
    )


def test_the_signatures_field_does_not_affect_the_hash() -> None:
    unsigned = card_json()
    signed = {**card_json(), "signatures": [{"protected": "e30", "signature": "abc"}]}
    assert compute_card_hash(unsigned) == compute_card_hash(signed)
    assert compute_card_hash(unsigned).startswith("sha256:")


def test_invalid_json_fails_with_a_distinct_error() -> None:
    with pytest.raises(CardNotParsableError, match="not valid JSON"):
        parse_agent_card("{not json")


def test_a_non_object_fails_with_a_distinct_error() -> None:
    with pytest.raises(CardNotParsableError, match="not a JSON object"):
        parse_agent_card("[1, 2]")


def test_a_card_missing_what_suncly_needs_fails_with_the_field_named() -> None:
    with pytest.raises(CardNotParsableError, match="supportedInterfaces"):
        parse_agent_card(json.dumps({"name": "x", "skills": []}))


def test_unknown_fields_are_kept_and_missing_required_fields_are_reported() -> None:
    card = card_json(extra={"futureField": {"a": 1}})
    del card["capabilities"]
    parsed = parse_agent_card(json.dumps(card))
    assert parsed.json_object["futureField"] == {"a": 1}
    assert parsed.missing_required_fields() == ["capabilities"]


def test_skill_output_modes_fall_back_to_the_card_default() -> None:
    parsed = parse_agent_card(
        card_text(
            skills=[
                {
                    "id": "a",
                    "name": "A",
                    "description": "",
                    "tags": ["t"],
                    "outputModes": ["application/json"],
                },
                {"id": "b", "name": "B", "description": "", "tags": ["t"]},
            ]
        )
    )
    card = parsed.card
    assert card.output_modes_for(card.skills[0]) == ["application/json"]
    assert card.output_modes_for(card.skills[1]) == ["text/plain"]
    assert card.skill_ids() == ["a", "b"]


def test_select_interface_takes_the_first_jsonrpc_1_0_entry() -> None:
    card = card_json()
    card["supportedInterfaces"] = [
        {"url": "https://a.example.com/grpc", "protocolBinding": "GRPC", "protocolVersion": "1.0"},
        {
            "url": "https://a.example.com/old",
            "protocolBinding": "JSONRPC",
            "protocolVersion": "0.3",
        },
        {
            "url": "https://a.example.com/rpc",
            "protocolBinding": "JSONRPC",
            "protocolVersion": "1.0",
        },
    ]
    assert select_interface(parse_agent_card(json.dumps(card))).url == "https://a.example.com/rpc"


def test_select_interface_refuses_a_card_without_jsonrpc_1_0() -> None:
    with pytest.raises(CardNotAttestableError, match=r"GRPC 1\.0"):
        select_interface(parse_agent_card(card_text(binding="GRPC")))


def test_agent_ids_are_stable_per_card_url() -> None:
    assert agent_id_for_url("https://a.example.com/card") == agent_id_for_url(
        "https://a.example.com/card "
    )
    assert agent_id_for_url("https://a.example.com/card") != agent_id_for_url(
        "https://b.example.com/card"
    )
