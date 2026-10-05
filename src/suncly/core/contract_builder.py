"""The Contract builder (schema §2): drafting, versioning and human approval.

This version drafts deterministically from the card alone, with no model
(``DeterministicDrafter``). The stage 2 model-based drafter implements the
same ``ContractDrafter`` port, so nothing here changes when it arrives.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from uuid import UUID

from suncly.domain.canonical import canonical_json
from suncly.domain.card import AgentCard, ParsedCard
from suncly.domain.contract_file import ContractFile, ContractFileTestCase
from suncly.domain.criteria import Criteria
from suncly.domain.errors import ContractError
from suncly.domain.models import Contract, ContractStatus, TestCase, TestCaseKind
from suncly.ports.clock import Clock, IdGenerator
from suncly.ports.drafter import Draft, DraftSettings, DraftTestCase, NotTestableSkill
from suncly.ports.store import EvidenceStore

#: Why a skill without examples gets no test case: Suncly never invents input.
NO_EXAMPLES_REASON = "the card declares no examples for this skill, and Suncly never invents input"
#: Longest example the drafter will turn into an input, in characters.
MAX_EXAMPLE_LENGTH = 4000


class DeterministicDrafter:
    """Drafts one test case of kind ``skill`` per declared example, up to a cap.

    Criteria are the Layer 1 checks the card itself supports: the task reaches
    ``TASK_STATE_COMPLETED``, a response is present, every output part uses one
    of the skill's declared output modes, and the latency limit from
    configuration. No model is involved.
    """

    name = "deterministic-examples-v1"

    def draft(self, card: AgentCard, settings: DraftSettings) -> Draft:
        test_cases: list[DraftTestCase] = []
        not_testable: list[NotTestableSkill] = []
        for skill in card.skills:
            examples = self._usable_examples(skill.examples)
            if not examples:
                not_testable.append(NotTestableSkill(skill_id=skill.id, reason=NO_EXAMPLES_REASON))
                continue
            output_modes = card.output_modes_for(skill)
            criteria = Criteria(
                latency_limit_ms=settings.latency_limit_ms,
                response_present=True,
                output_modes=output_modes or None,
            )
            for example in examples[: settings.max_test_cases_per_skill]:
                test_cases.append(
                    DraftTestCase(
                        skill_id=skill.id,
                        input={"text": example},
                        criteria=criteria.to_document(),
                        kind=TestCaseKind.SKILL,
                    )
                )
        return Draft(test_cases=test_cases, not_testable=not_testable)

    @staticmethod
    def _usable_examples(examples: Sequence[str] | None) -> list[str]:
        seen: set[str] = set()
        usable: list[str] = []
        for example in examples or []:
            text = example.strip()
            if not text or len(text) > MAX_EXAMPLE_LENGTH or text in seen:
                continue
            seen.add(text)
            usable.append(text)
        return usable


def uncovered_skills(card: AgentCard, test_cases: Sequence[DraftTestCase | TestCase]) -> list[str]:
    """Declared skills with no test case: where invariant 1 (schema §2) is not satisfied."""
    covered = {tc.skill_id for tc in test_cases if tc.kind is TestCaseKind.SKILL}
    return [skill_id for skill_id in card.skill_ids() if skill_id not in covered]


def content_key(test_case: DraftTestCase | TestCase | ContractFileTestCase) -> bytes:
    """What makes two test cases the same test: skill, kind, input and criteria."""
    return canonical_json(
        {
            "skill_id": test_case.skill_id,
            "kind": test_case.kind.value,
            "input": test_case.input,
            "criteria": test_case.criteria,
        }
    )


def same_content(
    left: Sequence[DraftTestCase | TestCase], right: Sequence[DraftTestCase | TestCase]
) -> bool:
    return Counter(content_key(tc) for tc in left) == Counter(content_key(tc) for tc in right)


def draft_from_contract_file(contract_file: ContractFile, parsed: ParsedCard) -> Draft:
    """Turn a hand-written contract file into a draft, refusing what the brief forbids.

    The file must be for the fetched card (same ``card_hash``) and must either
    cover every declared skill or acknowledge the skills it leaves out.
    """
    if contract_file.card_hash != parsed.card_hash:
        raise ContractError(
            "The contract file was written for a different card.",
            f"The file says card_hash {contract_file.card_hash}; the fetched card has "
            f"{parsed.card_hash}.",
            "Export a fresh draft with --export-draft and move your edits into it.",
        )
    test_cases = [
        DraftTestCase(skill_id=tc.skill_id, input=tc.input, criteria=tc.criteria, kind=tc.kind)
        for tc in contract_file.test_cases
    ]
    declared = set(parsed.card.skill_ids())
    unknown = sorted({tc.skill_id for tc in test_cases if tc.skill_id is not None} - declared)
    if unknown:
        raise ContractError(
            "The contract file names skills the card does not declare.",
            f"Unknown skill ids: {', '.join(unknown)}.",
            f"Use one of the declared skill ids: {', '.join(sorted(declared))}.",
        )
    missing = uncovered_skills(parsed.card, test_cases)
    acknowledged = set(contract_file.skills_without_test_case)
    not_acknowledged = [skill_id for skill_id in missing if skill_id not in acknowledged]
    if not_acknowledged:
        raise ContractError(
            "The contract file leaves declared skills without a test case.",
            f"No test case for: {', '.join(not_acknowledged)} (invariant 1, schema §2).",
            "Add a test case for each, or list them under skills_without_test_case to "
            "acknowledge that they stay untested.",
        )
    not_testable = [
        NotTestableSkill(skill_id=skill_id, reason="left out by the contract file")
        for skill_id in missing
    ]
    return Draft(test_cases=test_cases, not_testable=not_testable)


def contract_file_from_draft(draft: Draft, parsed: ParsedCard) -> ContractFile:
    """The exportable form of a draft, ready to edit and import again."""
    return ContractFile(
        suncly_contract_file=1,
        card_hash=parsed.card_hash,
        agent_name=parsed.card.name,
        skills_without_test_case=[skill.skill_id for skill in draft.not_testable],
        test_cases=[
            ContractFileTestCase(
                skill_id=tc.skill_id, kind=tc.kind, input=tc.input, criteria=tc.criteria
            )
            for tc in draft.test_cases
        ],
    )


class ContractService:
    """Contract records: versions, drafts and the recorded human approval."""

    def __init__(self, store: EvidenceStore, clock: Clock, ids: IdGenerator) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids

    def contracts(self, card_version_id: UUID) -> list[tuple[Contract, list[TestCase]]]:
        return [
            (contract, self._store.list_test_cases(contract.id))
            for contract in self._store.list_contracts(card_version_id)
        ]

    def latest_approved(self, card_version_id: UUID) -> tuple[Contract, list[TestCase]] | None:
        approved = [
            (c, tcs)
            for c, tcs in self.contracts(card_version_id)
            if c.status is ContractStatus.APPROVED
        ]
        return max(approved, key=lambda pair: pair[0].version, default=None)

    def latest_draft_with_content(
        self, card_version_id: UUID, draft: Draft
    ) -> tuple[Contract, list[TestCase]] | None:
        """An existing draft with exactly these test cases, so re-runs create no duplicates."""
        drafts = [
            (c, tcs)
            for c, tcs in self.contracts(card_version_id)
            if c.status is ContractStatus.DRAFT and same_content(tcs, draft.test_cases)
        ]
        return max(drafts, key=lambda pair: pair[0].version, default=None)

    def create_draft(self, card_version_id: UUID, draft: Draft) -> tuple[Contract, list[TestCase]]:
        """Record a new draft. Versions count per card version (OQ-D5, proposal)."""
        if not draft.test_cases:
            raise ContractError(
                "The draft has no test cases, so there is nothing to approve or run.",
                "No declared skill has a usable example"
                + (
                    f": {', '.join(s.skill_id for s in draft.not_testable)}."
                    if draft.not_testable
                    else "."
                ),
                "Add examples to the card's skills, or write a contract file (see docs/API.md).",
            )
        version = (
            max((c.version for c in self._store.list_contracts(card_version_id)), default=0) + 1
        )
        contract = Contract(
            id=self._ids.new_id(),
            card_version_id=card_version_id,
            version=version,
            status=ContractStatus.DRAFT,
            created_at=self._clock.now(),
        )
        test_cases = [
            TestCase(
                id=self._ids.new_id(),
                contract_id=contract.id,
                skill_id=tc.skill_id,
                input=tc.input,
                criteria=tc.criteria,
                kind=tc.kind,
            )
            for tc in draft.test_cases
        ]
        self._store.add_contract(contract, test_cases)
        return contract, test_cases

    def approve(self, contract: Contract, approved_by: str) -> Contract:
        """Record the human approval (schema §2). Older approved versions become superseded."""
        approver = approved_by.strip()
        if not approver:
            raise ContractError(
                "The approval needs the approver's identifier.",
                "An empty identifier was given.",
                "Pass --approve-as <identifier> or enter it at the prompt.",
            )
        approved = self._store.approve_contract(contract.id, approver, self._clock.now())
        for other in self._store.list_contracts(contract.card_version_id):
            if (
                other.status is ContractStatus.APPROVED
                and other.id != approved.id
                and other.version < approved.version
            ):
                self._store.supersede_contract(other.id)
        return approved
