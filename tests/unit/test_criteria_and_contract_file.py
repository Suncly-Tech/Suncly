"""The input, criteria and contract file formats (OQ-D7 and OQ-R2 proposals)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from suncly.domain.contract_file import (
    ContractFile,
    ContractFileTestCase,
    parse_contract_file,
    render_contract_file,
)
from suncly.domain.criteria import Criteria, TestInput, parse_criteria, parse_input
from suncly.domain.errors import ContractError
from suncly.domain.models import TestCaseKind


def test_input_is_text_or_parts_but_not_both() -> None:
    assert parse_input({"text": "hi"}).to_parts() == [{"text": "hi"}]
    assert parse_input({"parts": [{"data": {"a": 1}}]}).to_parts() == [{"data": {"a": 1}}]
    invalid: list[dict[str, object]] = [
        {},
        {"text": "hi", "parts": []},
        {"text": "  "},
        {"parts": []},
    ]
    for bad in invalid:
        with pytest.raises(ValidationError):
            TestInput.model_validate(bad)


def test_criteria_defaults_and_validation() -> None:
    criteria = parse_criteria({"latency_limit_ms": 100})
    assert criteria.final_state == "TASK_STATE_COMPLETED"
    assert criteria.response_present and criteria.output_modes is None
    with pytest.raises(ValidationError, match="terminal task state"):
        parse_criteria({"latency_limit_ms": 100, "final_state": "TASK_STATE_WORKING"})
    with pytest.raises(ValidationError, match="JSON pointers"):
        parse_criteria({"latency_limit_ms": 100, "required_fields": ["artifacts"]})
    with pytest.raises(ValidationError):
        parse_criteria({"latency_limit_ms": 0})


def test_unknown_criteria_keys_are_rejected_so_typos_cannot_weaken_a_check() -> None:
    with pytest.raises(ValidationError):
        Criteria.model_validate({"latency_limit_ms": 100, "latency_limit": 5})


def contract_file(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "suncly_contract_file": 1,
        "card_hash": "sha256:abc",
        "test_cases": [
            {"skill_id": "echo", "input": {"text": "hi"}, "criteria": {"latency_limit_ms": 100}},
        ],
    }
    base.update(overrides)
    return base


def test_contract_file_round_trips() -> None:
    parsed = parse_contract_file(json.dumps(contract_file()))
    assert parsed.test_cases[0].kind is TestCaseKind.SKILL
    text = render_contract_file(parsed)
    assert parse_contract_file(text) == parsed
    assert text.endswith("\n")


def test_contract_file_errors_name_the_problem() -> None:
    with pytest.raises(ContractError, match="not valid JSON"):
        parse_contract_file("{")
    with pytest.raises(ContractError, match="test_cases"):
        parse_contract_file(json.dumps(contract_file(test_cases=[])))
    with pytest.raises(ContractError, match="approved_by"):
        parse_contract_file(json.dumps(contract_file(approved_by="someone")))
    with pytest.raises(ContractError, match="invalid test case at test_cases\\[0\\]"):
        parse_contract_file(
            json.dumps(contract_file(test_cases=[{"skill_id": "e", "input": {}, "criteria": {}}]))
        )
    with pytest.raises(ContractError, match="without a skill_id"):
        parse_contract_file(
            json.dumps(
                contract_file(
                    test_cases=[{"input": {"text": "x"}, "criteria": {"latency_limit_ms": 1}}]
                )
            )
        )


def test_contract_file_model_has_no_approval_fields() -> None:
    assert "approved_by" not in ContractFile.model_fields
    assert "approved_at" not in ContractFile.model_fields
    assert set(ContractFileTestCase.model_fields) == {"skill_id", "kind", "input", "criteria"}
