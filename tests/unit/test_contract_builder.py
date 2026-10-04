"""The deterministic drafter, contract versions and recorded approval."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from suncly.adapters.file_store import FileEvidenceStore
from suncly.core.contract_builder import (
    NO_EXAMPLES_REASON,
    ContractService,
    DeterministicDrafter,
    contract_file_from_draft,
    draft_from_contract_file,
    same_content,
    uncovered_skills,
)
from suncly.domain.card import parse_agent_card
from suncly.domain.contract_file import parse_contract_file, render_contract_file
from suncly.domain.errors import ContractError
from suncly.domain.models import Agent, CardVersion, ContractStatus, RiskLevel, TestCaseKind
from suncly.ports.drafter import Draft, DraftSettings, DraftTestCase
from tests.fakes import FakeClock, SeqIds, card_json, card_text

SETTINGS = DraftSettings(latency_limit_ms=1500, max_test_cases_per_skill=2)


def skill(skill_id: str, examples: list[str] | None, **extra: object) -> dict[str, object]:
    data: dict[str, object] = {"id": skill_id, "name": skill_id, "description": "", "tags": ["t"]}
    if examples is not None:
        data["examples"] = examples
    data.update(extra)
    return data


def test_drafter_writes_one_skill_test_case_per_usable_example_up_to_the_cap() -> None:
    parsed = parse_agent_card(
        card_text(
            skills=[
                skill("a", ["one", " one ", "", "two", "three"]),
                skill("b", ["x"], outputModes=["application/json"]),
            ]
        )
    )
    draft = DeterministicDrafter().draft(parsed.card, SETTINGS)
    assert [(tc.skill_id, tc.input) for tc in draft.test_cases] == [
        ("a", {"text": "one"}),
        ("a", {"text": "two"}),
        ("b", {"text": "x"}),
    ]
    assert all(tc.kind is TestCaseKind.SKILL for tc in draft.test_cases)
    assert draft.test_cases[0].criteria == {
        "final_state": "TASK_STATE_COMPLETED",
        "latency_limit_ms": 1500,
        "response_present": True,
        "output_modes": ["text/plain"],
        "required_fields": [],
        "model_checks": [],
        "accept_direct_message": False,
    }
    assert draft.test_cases[2].criteria["output_modes"] == ["application/json"]
    assert draft.not_testable == []


def test_drafter_never_invents_input_for_a_skill_without_examples() -> None:
    parsed = parse_agent_card(card_text(skills=[skill("silent", None), skill("empty", ["  "])]))
    draft = DeterministicDrafter().draft(parsed.card, SETTINGS)
    assert draft.test_cases == []
    assert [(s.skill_id, s.reason) for s in draft.not_testable] == [
        ("silent", NO_EXAMPLES_REASON),
        ("empty", NO_EXAMPLES_REASON),
    ]
    assert uncovered_skills(parsed.card, draft.test_cases) == ["silent", "empty"]


def test_same_content_ignores_order_and_ids() -> None:
    a = DraftTestCase(
        skill_id="s", input={"text": "x"}, criteria={"latency_limit_ms": 1}, kind=TestCaseKind.SKILL
    )
    b = DraftTestCase(
        skill_id="s", input={"text": "y"}, criteria={"latency_limit_ms": 1}, kind=TestCaseKind.SKILL
    )
    assert same_content([a, b], [b, a])
    assert not same_content([a], [a, b])
    assert not same_content([a], [b])


def test_contract_file_import_checks_hash_skills_and_acknowledgements() -> None:
    parsed = parse_agent_card(card_text(skills=[skill("a", ["x"]), skill("b", None)]))
    draft = DeterministicDrafter().draft(parsed.card, SETTINGS)
    exported = contract_file_from_draft(draft, parsed)
    assert exported.skills_without_test_case == ["b"]
    reimported = draft_from_contract_file(
        parse_contract_file(render_contract_file(exported)), parsed
    )
    assert same_content(reimported.test_cases, draft.test_cases)

    with pytest.raises(ContractError, match="different card"):
        draft_from_contract_file(exported.model_copy(update={"card_hash": "sha256:other"}), parsed)
    with pytest.raises(ContractError, match="leaves declared skills"):
        draft_from_contract_file(
            exported.model_copy(update={"skills_without_test_case": []}), parsed
        )
    unknown = exported.model_copy(
        update={"test_cases": [exported.test_cases[0].model_copy(update={"skill_id": "zzz"})]}
    )
    with pytest.raises(ContractError, match="does not declare"):
        draft_from_contract_file(unknown, parsed)


@pytest.fixture
def service(tmp_path: Path) -> tuple[ContractService, FileEvidenceStore, CardVersion]:
    store = FileEvidenceStore(tmp_path)
    agent = Agent(id=SeqIds().new_id(), name="A", owner="o", risk_level=RiskLevel.LOW)
    store.add_agent(agent)
    card_version = CardVersion(
        id=SeqIds().new_id(),
        agent_id=agent.id,
        card_hash="sha256:1",
        raw_json=json.dumps(card_json()),
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    store.add_card_version(card_version)
    return ContractService(store, FakeClock(), SeqIds()), store, card_version


def a_draft(text: str = "x") -> Draft:
    return Draft(
        test_cases=[
            DraftTestCase(
                skill_id="echo",
                input={"text": text},
                criteria={"latency_limit_ms": 1},
                kind=TestCaseKind.SKILL,
            )
        ]
    )


def test_versions_count_per_card_version_and_approval_supersedes_older_versions(
    service: tuple[ContractService, FileEvidenceStore, CardVersion],
) -> None:
    contracts, store, card_version = service
    v1, _ = contracts.create_draft(card_version.id, a_draft("x"))
    v2, _ = contracts.create_draft(card_version.id, a_draft("y"))
    assert (v1.version, v2.version) == (1, 2)
    assert contracts.latest_approved(card_version.id) is None
    approved1 = contracts.approve(v1, "alice")
    assert approved1.status is ContractStatus.APPROVED and approved1.approved_by == "alice"
    approved2 = contracts.approve(v2, " bob ")
    assert approved2.approved_by == "bob"
    assert store.get_contract(v1.id).status is ContractStatus.SUPERSEDED  # type: ignore[union-attr]
    latest = contracts.latest_approved(card_version.id)
    assert latest is not None and latest[0].id == v2.id


def test_an_existing_draft_with_the_same_content_is_reused(
    service: tuple[ContractService, FileEvidenceStore, CardVersion],
) -> None:
    contracts, _, card_version = service
    created, _ = contracts.create_draft(card_version.id, a_draft())
    found = contracts.latest_draft_with_content(card_version.id, a_draft())
    assert found is not None and found[0].id == created.id
    assert contracts.latest_draft_with_content(card_version.id, a_draft("other")) is None


def test_empty_drafts_and_blank_approvers_are_refused(
    service: tuple[ContractService, FileEvidenceStore, CardVersion],
) -> None:
    contracts, _, card_version = service
    with pytest.raises(ContractError, match="no test cases"):
        contracts.create_draft(card_version.id, Draft())
    contract, _ = contracts.create_draft(card_version.id, a_draft())
    with pytest.raises(ContractError, match="identifier"):
        contracts.approve(contract, "   ")
