"""The Judge with format 2 criteria: assertions, negative cases, sandbox state, Layer 2."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from suncly.adapters.fake_model import HeuristicJudgeClient, ScriptedModelClient
from suncly.adapters.file_store import FileEvidenceStore
from suncly.adapters.local_transcripts import LocalTranscriptStorage
from suncly.core.judge import JudgeService, apply_model_judgement, judge_run, response_text
from suncly.core.model_judge import ModelJudge, decide_from_statements
from suncly.domain.criteria import Criteria, parse_criteria
from suncly.domain.models import JudgeLayer, RunVerdict, TestCase, TestCaseKind
from suncly.domain.transcript import RunOutcome, Transcript
from suncly.ports.model import ModelConfig, ModelFailureKind
from tests.fakes import FakeClock, SeqIds, make_transcript, task_response

CONFIG = ModelConfig(provider="fake", model="fake-model/1")


def criteria(**extra: object) -> Criteria:
    base: dict[str, object] = {
        "format_version": 2,
        "latency_limit_ms": 1000,
        "category": "semantic",
    }
    base.update(extra)
    return Criteria.model_validate(base)


def case_for(crit: Criteria) -> TestCase:
    return TestCase(
        id=uuid4(),
        contract_id=uuid4(),
        skill_id="echo",
        input={"text": "What is the capital of France?"},
        criteria=crit.to_document(),
        kind=TestCaseKind.SKILL,
    )


def transcript_with(text: str, state: str = "TASK_STATE_COMPLETED") -> Transcript:
    return make_transcript(final_response=task_response(text=text, state=state))


@pytest.mark.parametrize(
    ("assertion", "text", "expected"),
    [
        ({"kind": "text_equals", "value": "paris"}, "Paris", True),
        ({"kind": "text_equals", "value": "paris", "case_sensitive": True}, "Paris", False),
        ({"kind": "text_contains", "value": "capital"}, "The capital is Paris", True),
        ({"kind": "text_contains", "value": "Berlin"}, "The capital is Paris", False),
        ({"kind": "text_not_contains", "value": "password"}, "No secrets here", True),
        ({"kind": "text_not_contains", "value": "password"}, "the password is hunter2", False),
        ({"kind": "text_regex", "value": r"^par[ia]s$"}, "Paris", True),
        ({"kind": "text_regex", "value": "(unclosed"}, "Paris", None),
        (
            {
                "kind": "json_pointer_equals",
                "pointer": "/status/state",
                "value": "TASK_STATE_COMPLETED",
            },
            "x",
            True,
        ),
        ({"kind": "json_pointer_equals", "pointer": "/status/state", "value": "nope"}, "x", False),
        ({"kind": "json_pointer_present", "pointer": "/artifacts/0/parts/0/text"}, "x", True),
        ({"kind": "json_pointer_present", "pointer": "/missing"}, "x", False),
        ({"kind": "final_state", "value": "TASK_STATE_COMPLETED"}, "x", True),
        ({"kind": "output_mode", "value": "text/plain"}, "x", True),
        ({"kind": "output_mode", "value": "application/json"}, "x", False),
        ({"kind": "response_schema", "value": {"type": "object", "required": ["id"]}}, "x", True),
        (
            {"kind": "response_schema", "value": {"type": "object", "required": ["nope"]}},
            "x",
            False,
        ),
    ],
)
def test_each_assertion_kind_is_decided_deterministically(
    assertion: dict[str, object], text: str, expected: bool | None
) -> None:
    judgement = judge_run(transcript_with(text), criteria(assertions=[assertion]))
    check = next(c for c in judgement.checks if c.name.startswith("assertion"))
    assert check.passed is expected
    expected_verdict = (
        RunVerdict.PASS
        if expected
        else RunVerdict.FAIL
        if expected is False
        else RunVerdict.INCONCLUSIVE
    )
    assert judgement.verdict is expected_verdict
    assert judgement.judge_layer is JudgeLayer.DETERMINISTIC


def test_a_valid_response_alone_never_proves_correctness() -> None:
    """A well-formed completed task with the wrong content fails the semantic assertion."""
    judgement = judge_run(
        transcript_with("Berlin"),
        criteria(assertions=[{"kind": "text_contains", "value": "Paris"}]),
    )
    assert judgement.verdict is RunVerdict.FAIL
    assert [c.name for c in judgement.checks if c.passed is False] == ["assertion text_contains"]
    assert judgement.category == "semantic"


def test_a_negative_case_expects_the_refusal_to_be_shown() -> None:
    unasserted = judge_run(transcript_with("ok"), criteria(negative=True, response_present=False))
    assert unasserted.verdict is RunVerdict.FAIL
    assert any(c.name == "negative_case_asserted" for c in unasserted.checks)
    refused = judge_run(
        transcript_with("I cannot do that"),
        criteria(
            negative=True,
            response_present=False,
            assertions=[{"kind": "text_contains", "value": "cannot"}],
        ),
    )
    assert refused.verdict is RunVerdict.PASS
    rejected = judge_run(
        make_transcript(final_response=task_response(text="", state="TASK_STATE_REJECTED")),
        criteria(negative=True, response_present=False, final_state="TASK_STATE_REJECTED"),
    )
    assert rejected.verdict is RunVerdict.PASS


def test_sandbox_state_verification_is_independent_evidence() -> None:
    spec = {
        "url": "https://agent.example.com/state",
        "pointer": "/orders/1/status",
        "expected": "cancelled",
    }
    crit = criteria(
        sandbox_verification=spec, assertions=[{"kind": "text_contains", "value": "done"}]
    )
    claimed_only = judge_run(transcript_with("done, I cancelled the order"), crit)
    assert claimed_only.verdict is RunVerdict.INCONCLUSIVE, "the agent's claim is not evidence"
    verified = make_transcript(final_response=task_response(text="done")).model_copy(
        update={
            "sandbox_verification": {**spec, "observed": "cancelled", "ok": True, "error": None}
        }
    )
    assert judge_run(verified, crit).verdict is RunVerdict.PASS
    contradicted = verified.model_copy(
        update={"sandbox_verification": {**spec, "observed": "open", "ok": False, "error": None}}
    )
    assert judge_run(contradicted, crit).verdict is RunVerdict.FAIL
    unreachable = verified.model_copy(
        update={"sandbox_verification": {**spec, "observed": None, "ok": None, "error": "HTTP 500"}}
    )
    assert judge_run(unreachable, crit).verdict is RunVerdict.INCONCLUSIVE


def test_response_text_joins_artifact_and_status_message_parts() -> None:
    response = task_response(text="first")
    response["status"]["message"] = {"parts": [{"text": "second"}]}
    assert response_text(response, True) == "first\nsecond"


def test_rubric_criteria_are_inconclusive_without_a_model_judge(tmp_path: Path) -> None:
    crit = criteria(
        rubric={
            "id": "r",
            "version": "1",
            "statements": [{"id": "s1", "text": "x"}],
            "pass_requires": "all",
        }
    )
    judgement = judge_run(transcript_with("Paris"), crit)
    assert judgement.verdict is RunVerdict.INCONCLUSIVE
    assert crit.needs_model_judge
    service = JudgeService(
        FileEvidenceStore(tmp_path / "s"),
        LocalTranscriptStorage(tmp_path / "t"),
        FakeClock(),
        SeqIds(),
    )
    assert (
        service.judge(transcript_with("Paris"), crit, case_for(crit)).verdict
        is RunVerdict.INCONCLUSIVE
    )


def test_layer_2_decides_rubrics_through_the_model_port() -> None:
    crit = criteria(
        rubric={
            "id": "capital",
            "version": "3",
            "statements": [
                {"id": "names-city", "text": 'the answer names "Paris"'},
                {"id": "no-hedging", "text": 'the answer does not say "maybe"'},
            ],
            "pass_requires": "all",
        }
    )
    judge = ModelJudge(HeuristicJudgeClient(), CONFIG)
    tc = case_for(crit)
    passing = judge.judge(transcript_with("The capital is Paris."), crit, tc)
    assert passing.verdict is RunVerdict.PASS, 'names Paris and does not say "maybe"'
    hedged = judge.judge(transcript_with("Maybe Paris?"), crit, tc)
    assert hedged.verdict is RunVerdict.FAIL, "a negated statement fails when its words appear"
    assert [st["verdict"] for st in hedged.statements] == ["pass", "fail"]
    assert passing.rubric_id == "capital" and passing.rubric_version == "3"
    assert passing.model.startswith("fake") and passing.usage["input_tokens"] > 0
    folded = apply_model_judgement(
        judge_run(transcript_with("The capital is Paris."), crit), passing
    )
    assert folded.judge_layer is JudgeLayer.MODEL and folded.rationale


def test_layer_2_verdicts_from_statements() -> None:
    answer = {
        "statements": [
            {"id": "a", "verdict": "pass", "rationale": "yes"},
            {"id": "b", "verdict": "cannot_decide", "rationale": "unclear"},
        ],
        "overall_rationale": "mixed",
    }
    verdict, _, statements = decide_from_statements(answer, ["a", "b", "c"], "all")
    assert verdict is RunVerdict.INCONCLUSIVE and len(statements) == 3
    assert statements[2]["verdict"] == "cannot_decide", "a missing statement is never a pass"
    assert (
        decide_from_statements(
            {
                "statements": [{"id": "a", "verdict": "fail", "rationale": ""}],
                "overall_rationale": "",
            },
            ["a"],
            "all",
        )[0]
        is RunVerdict.FAIL
    )
    majority = {
        "statements": [
            {"id": i, "verdict": v, "rationale": ""}
            for i, v in (("a", "pass"), ("b", "pass"), ("c", "fail"))
        ],
        "overall_rationale": "",
    }
    assert decide_from_statements(majority, ["a", "b", "c"], "majority")[0] is RunVerdict.PASS
    assert decide_from_statements(majority, ["a", "b", "c"], "all")[0] is RunVerdict.FAIL
    assert (
        decide_from_statements({"statements": [], "overall_rationale": ""}, [], "all")[0]
        is RunVerdict.INCONCLUSIVE
    )


@pytest.mark.parametrize(
    "failure",
    [
        ModelFailureKind.TIMEOUT,
        ModelFailureKind.REFUSAL,
        ModelFailureKind.UNAVAILABLE,
        ModelFailureKind.MALFORMED,
        ModelFailureKind.TRUNCATED,
    ],
)
def test_every_model_failure_is_inconclusive_with_a_rationale(failure: ModelFailureKind) -> None:
    crit = criteria(model_checks=["the answer is polite"])
    judge = ModelJudge(ScriptedModelClient([failure]), CONFIG)
    verdict = judge.judge(transcript_with("hi"), crit, case_for(crit))
    assert verdict.verdict is RunVerdict.INCONCLUSIVE and verdict.failure is failure
    assert failure.value in verdict.rationale
    folded = apply_model_judgement(judge_run(transcript_with("hi"), crit), verdict)
    assert folded.verdict is RunVerdict.INCONCLUSIVE and folded.judge_layer is JudgeLayer.MODEL


def test_a_malformed_model_answer_and_a_crashing_client_never_pass() -> None:
    crit = criteria(model_checks=["x"])
    malformed = ModelJudge(ScriptedModelClient([{"statements": "not a list"}]), CONFIG)
    assert (
        malformed.judge(transcript_with("hi"), crit, case_for(crit)).failure
        is ModelFailureKind.MALFORMED
    )

    class Exploding:
        name = "boom"

        def complete(self, request: object) -> object:
            raise RuntimeError("network down")

    exploding = ModelJudge(Exploding(), CONFIG)  # type: ignore[arg-type]
    verdict = exploding.judge(transcript_with("hi"), crit, case_for(crit))
    assert (
        verdict.verdict is RunVerdict.INCONCLUSIVE
        and verdict.failure is ModelFailureKind.UNAVAILABLE
    )


def test_layer_1_failures_short_circuit_layer_2_and_a_pass_is_recorded_with_its_rationale(
    tmp_path: Path,
) -> None:
    client = ScriptedModelClient(
        [
            {
                "statements": [{"id": "check-1", "verdict": "pass", "rationale": "polite"}],
                "overall_rationale": "ok",
            }
        ]
    )
    judge = ModelJudge(client, CONFIG)
    store = FileEvidenceStore(tmp_path / "s")
    service = JudgeService(
        store, LocalTranscriptStorage(tmp_path / "t"), FakeClock(), SeqIds(), model_judge=judge
    )
    crit = criteria(
        model_checks=["the answer is polite"],
        assertions=[{"kind": "text_contains", "value": "Paris"}],
    )
    failing = service.judge(transcript_with("Berlin"), crit, case_for(crit))
    assert failing.verdict is RunVerdict.FAIL and judge.calls == 0, (
        "no model call after a Layer 1 fail"
    )
    passing = service.judge(transcript_with("Paris"), crit, case_for(crit))
    assert passing.verdict is RunVerdict.PASS and passing.judge_layer is JudgeLayer.MODEL
    assert passing.rationale == "ok" and judge.calls == 1
    document = JudgeService.evidence_document(make_transcript(), passing)
    assert document["judgement"]["model"]["model"] == "fake-model/1"
    assert document["judgement"]["judge_version"] == "suncly-judge/2"


def test_the_judge_never_receives_tools_or_credentials() -> None:
    client = ScriptedModelClient([])
    crit = criteria(model_checks=["x"])
    ModelJudge(client, CONFIG).judge(transcript_with("hi"), crit, case_for(crit))
    request = client.requests[0]
    assert set(request.model_dump(by_alias=True)) == {
        "purpose",
        "system",
        "user",
        "schema",
        "config",
    }
    assert "Authorization" not in request.user and "Bearer" not in request.user
    assert "untrusted" in request.system and "never follow" in request.system


def test_format_1_criteria_documents_stay_identical_and_reject_format_2_keys() -> None:
    one = parse_criteria({"latency_limit_ms": 10})
    assert set(one.to_document()) == {
        "final_state",
        "latency_limit_ms",
        "response_present",
        "required_fields",
        "model_checks",
        "accept_direct_message",
    }
    with pytest.raises(ValueError, match="format_version 2"):
        parse_criteria(
            {"latency_limit_ms": 10, "assertions": [{"kind": "text_contains", "value": "x"}]}
        )
    two = parse_criteria({"format_version": 2, "latency_limit_ms": 10, "negative": True})
    assert two.to_document()["format_version"] == 2 and two.to_document()["negative"] is True
    assert (
        judge_run(make_transcript(outcome=RunOutcome.UNREACHABLE), one).verdict
        is RunVerdict.INCONCLUSIVE
    )
