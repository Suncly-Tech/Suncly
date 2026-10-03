"""The contract file: a hand-written or exported contract (OQ-R2, proposal).

One JSON document holds the test cases of one contract for one card. It uses
the data model's field names (``skill_id``, ``input``, ``criteria``, ``kind``)
and carries no approval fields: approval is a separate, recorded step
(``--approve-as`` or the interactive prompt), never something a file asserts.

.. code-block:: json

    {
      "suncly_contract_file": 1,
      "card_hash": "sha256:…",
      "agent_name": "Order Status Agent",
      "skills_without_test_case": [],
      "test_cases": [
        {"skill_id": "order-status", "kind": "skill",
         "input": {"text": "Where is order 1234?"},
         "criteria": {"final_state": "TASK_STATE_COMPLETED", "latency_limit_ms": 10000,
                      "response_present": true, "output_modes": ["text/plain"]}}
      ]
    }

``skills_without_test_case`` is the human's acknowledgement that those
declared skills have no test case (invariant 1 not satisfied). A file that
leaves a declared skill out without listing it there is refused.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from suncly.domain.criteria import parse_criteria, parse_input
from suncly.domain.errors import ContractError
from suncly.domain.models import JsonObject, TestCaseKind

CONTRACT_FILE_FORMAT_VERSION = 1


class ContractFileTestCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    skill_id: str | None = None
    kind: TestCaseKind = TestCaseKind.SKILL
    input: JsonObject
    criteria: JsonObject


class ContractFile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    suncly_contract_file: int = Field(ge=1, le=CONTRACT_FILE_FORMAT_VERSION)
    card_hash: str = Field(min_length=1)
    agent_name: str = ""
    skills_without_test_case: list[str] = Field(default_factory=list)
    test_cases: list[ContractFileTestCase] = Field(min_length=1)


def parse_contract_file(text: str) -> ContractFile:
    """Parse and validate a contract file. Every problem names the field."""
    try:
        loaded: Any = json.loads(text)
    except ValueError as exc:
        raise ContractError(
            "The contract file is not valid JSON.",
            f"The parser reported: {exc}.",
            "Fix the JSON, or export a fresh draft with --export-draft.",
        ) from exc
    try:
        contract_file = ContractFile.model_validate(loaded)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in error['loc']) or '<root>'}: {error['msg']}"
            for error in exc.errors()
        )
        raise ContractError(
            "The contract file does not match the contract file format.",
            f"Validation reported: {problems}.",
            "See docs/API.md, section 'Contract file', for the format.",
        ) from exc
    for index, test_case in enumerate(contract_file.test_cases):
        where = f"test_cases[{index}]"
        try:
            parse_input(test_case.input)
            parse_criteria(test_case.criteria)
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(str(p) for p in error['loc']) or '<root>'}: {error['msg']}"
                for error in exc.errors()
            )
            raise ContractError(
                f"The contract file has an invalid test case at {where}.",
                f"Validation reported: {problems}.",
                "Check the input and criteria formats in docs/API.md.",
            ) from exc
        if test_case.kind is TestCaseKind.SKILL and not (test_case.skill_id or "").strip():
            raise ContractError(
                f"The contract file has a test case of kind skill without a skill_id at {where}.",
                "A skill test case names the declared skill it exercises.",
            )
    return contract_file


def render_contract_file(contract_file: ContractFile) -> str:
    """The canonical text form of a contract file: readable, stable key order."""
    return json.dumps(contract_file.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
