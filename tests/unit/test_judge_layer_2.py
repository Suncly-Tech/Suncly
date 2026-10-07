"""Judge Layer 2 (ROADMAP stage 4, items 1 to 3): the pinned model, the rubric, the subprocess.

Every verdict path (pass, fail, inconclusive, malformed output, timeout, wrong
model, no model configured), the rule that Layer 2 judges only what Layer 1
cannot decide, the provenance in the evidence document, DR-004, the criteria
format, and the isolation of the judge subprocess: a from-scratch environment,
one key variable, one endpoint host, and a key that never appears in any
evidence, report or log. The subprocess speaks the Anthropic Messages API to a
loopback fake in the verified wire shape (docs/IMPLEMENTATION_NOTES.md, section
4), including its error, refusal and truncation cases; no test calls the real
API (that is tests/live, skipped without a key).
"""

from __future__ import annotations

import io
import json
import os
import subprocess
from collections.abc import Callable, Iterator
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from suncly.adapters.judge_subprocess import SubprocessModelJudge, child_environment
from suncly.adapters.report.writer import FolderReportWriter
from suncly.core import rubric
from suncly.core.attestation import AttestationService, AttestRequest, Services
from suncly.core.cards import agent_id_for_url
from suncly.core.config import Config
from suncly.core.coverage import semantic_correctness
from suncly.core.judge import (
    NO_VERDICT,
    JudgeService,
    agent_output_text,
    interpret_answer,
    judge_run,
    judge_with_model,
    model_judge_settings,
    undecided_model_checks,
)
from suncly.domain.card import parse_agent_card
from suncly.domain.contract_file import ContractFile, ContractFileTestCase
from suncly.domain.criteria import Criteria, ModelCheck, parse_criteria
from suncly.domain.errors import ConfigError
from suncly.domain.models import JudgeLayer, RunVerdict, TestCase, TestCaseKind
from suncly.domain.transcript import RunOutcome
from suncly.judge import process
from suncly.judge.job import JudgeJob
from suncly.judge.key import JUDGE_KEY_ENV_VAR, ModelKey, read_key
from suncly.ports.model_judge import ModelRequest, ModelResponse
from suncly.ports.run_executor import RunJob, RunResult
from tests.fakes import (
    PINNED_MODEL,
    FakeClock,
    FakeExecutor,
    FakeModelJudge,
    SeqIds,
    StaticFetcher,
    answering_judge,
    card_text,
    make_transcript,
    model_answer,
    task_response,
)

CARD_URL = "https://agent.example.com/.well-known/agent-card.json"
KEY = "sk-judge-test-key-0123456789"

TONE = ModelCheck(
    name="tone", criterion="the answer is polite and complete", expected="yes_no", pass_rule="yes"
)
NO_UPSELL = ModelCheck(
    name="no_upsell", criterion="the answer sells nothing", expected="yes_no", pass_rule="no"
)
QUALITY = ModelCheck(
    name="quality",
    criterion="the answer is correct and useful",
    expected="score_0_to_10",
    pass_rule="at_least 7",
)
CRITERIA = Criteria(latency_limit_ms=1000, model_checks=[TONE])


def settings_for(model: str = PINNED_MODEL, timeout_s: float = 5.0) -> Any:
    config = Config(
        home=Path("/h"),
        judge_model=model,
        judge_endpoint="https://judge.example.com/v1",
        judge_rubric_version=rubric.RUBRIC_VERSION,
        judge_timeout_s=timeout_s,
    )
    settings = model_judge_settings(config)
    assert settings is not None
    return settings


def a_test_case(criteria: Criteria, text: str = "Where is my order?") -> TestCase:
    return TestCase(
        id=UUID(int=4),
        contract_id=UUID(int=3),
        skill_id="orders",
        input={"text": text},
        criteria=criteria.model_dump(mode="json"),
        kind=TestCaseKind.SKILL,
    )


def layer_2(
    judge: FakeModelJudge,
    criteria: Criteria = CRITERIA,
    transcript: Any = None,
    model: str = PINNED_MODEL,
) -> Any:
    transcript = transcript if transcript is not None else make_transcript()
    layer_1 = judge_run(transcript, criteria)
    return judge_with_model(
        layer_1, criteria, transcript, a_test_case(criteria), settings_for(model), judge
    )


# -- the criteria format (OQ-D7, decided) -------------------------------------------------


def test_a_model_check_is_an_object_with_exactly_four_required_keys() -> None:
    parsed = parse_criteria(
        {
            "latency_limit_ms": 1000,
            "model_checks": [
                {"name": "tone", "criterion": "polite", "expected": "yes_no", "pass_rule": "yes"}
            ],
        }
    )
    assert parsed.model_checks == [
        ModelCheck(name="tone", criterion="polite", expected="yes_no", pass_rule="yes")
    ]
    for missing in ("name", "criterion", "expected", "pass_rule"):
        check = {"name": "t", "criterion": "c", "expected": "yes_no", "pass_rule": "yes"}
        del check[missing]
        with pytest.raises(ValidationError):
            parse_criteria({"latency_limit_ms": 1000, "model_checks": [check]})


def test_unknown_keys_and_the_old_string_form_are_refused() -> None:
    with pytest.raises(ValidationError, match="extra"):
        ModelCheck.model_validate(
            {"name": "t", "criterion": "c", "expected": "yes_no", "pass_rule": "yes", "weight": 2}
        )
    with pytest.raises(ValidationError):
        parse_criteria({"latency_limit_ms": 1000, "model_checks": ["tone"]})


def test_the_pass_rule_must_fit_the_answer_shape_and_names_are_unique() -> None:
    with pytest.raises(ValidationError, match="'yes' or 'no'"):
        ModelCheck(name="t", criterion="c", expected="yes_no", pass_rule="at_least 7")
    with pytest.raises(ValidationError, match="at_least <n>"):
        ModelCheck(name="t", criterion="c", expected="score_0_to_10", pass_rule="yes")
    with pytest.raises(ValidationError, match="at_least <n>"):
        ModelCheck(name="t", criterion="c", expected="score_0_to_10", pass_rule="at_least 11")
    with pytest.raises(ValidationError, match="unique"):
        Criteria(latency_limit_ms=1000, model_checks=[TONE, TONE])
    assert QUALITY.passes(7) and QUALITY.passes(10) and not QUALITY.passes(6)
    assert NO_UPSELL.passes("no") and not NO_UPSELL.passes("yes")


# -- verdicts ---------------------------------------------------------------------------------


def test_pass_when_the_pinned_model_answers_in_shape_and_the_rule_passes() -> None:
    judge = answering_judge("yes")
    judgement = layer_2(judge)
    assert judgement.verdict is RunVerdict.PASS and judgement.judge_layer is JudgeLayer.MODEL
    assert judgement.rationale == "tone: the response states it plainly"
    assert judgement.summary == "pass: every Layer 1 check passed and Layer 2 passed tone"
    assert all(check.passed is True for check in judgement.checks)
    assert len(judge.requests) == 1 and judge.requests[0].model == PINNED_MODEL


def test_fail_when_the_answer_is_in_shape_but_the_rule_fails() -> None:
    judgement = layer_2(answering_judge("no"))
    assert judgement.verdict is RunVerdict.FAIL and judgement.judge_layer is JudgeLayer.MODEL
    assert judgement.summary == "fail: Layer 2 failed tone"
    scored = layer_2(answering_judge(6), Criteria(latency_limit_ms=1000, model_checks=[QUALITY]))
    assert scored.verdict is RunVerdict.FAIL
    assert layer_2(answering_judge(7), Criteria(latency_limit_ms=1000, model_checks=[QUALITY]))
    inverted = layer_2(
        answering_judge("yes"), Criteria(latency_limit_ms=1000, model_checks=[NO_UPSELL])
    )
    assert inverted.verdict is RunVerdict.FAIL, "pass_rule 'no' makes a yes a fail"


def test_inconclusive_never_pass_when_the_model_fails() -> None:
    failing = FakeModelJudge(lambda r: ModelResponse(error="HTTP 503 from the endpoint"))
    judgement = layer_2(failing)
    assert judgement.verdict is RunVerdict.INCONCLUSIVE
    assert judgement.judge_layer is JudgeLayer.MODEL
    assert judgement.rationale == "tone: no model verdict: HTTP 503 from the endpoint"
    assert judgement.summary == "inconclusive: Layer 2 could not decide tone"

    def explode(request: ModelRequest) -> ModelResponse:
        raise RuntimeError("the adapter blew up")

    judgement = layer_2(FakeModelJudge(explode))
    assert judgement.verdict is RunVerdict.INCONCLUSIVE and "blew up" in (judgement.rationale or "")


def test_inconclusive_on_a_timeout() -> None:
    timed_out = FakeModelJudge(
        lambda r: ModelResponse(error="timeout: no answer within 5s", timed_out=True)
    )
    judgement = layer_2(timed_out)
    assert judgement.verdict is RunVerdict.INCONCLUSIVE
    assert judgement.judge_layer is JudgeLayer.MODEL
    assert "timeout" in (judgement.rationale or "")


@pytest.mark.parametrize(
    "text",
    [
        "Sure! The answer is yes.",
        '{"answer": "yes"}',
        '{"answer": "yes", "rationale": ""}',
        '{"answer": "maybe", "rationale": "unsure"}',
        '{"answer": true, "rationale": "x"}',
        '{"answer": "yes", "rationale": "x", "confidence": 0.9}',
        '["yes", "x"]',
        "",
    ],
)
def test_inconclusive_on_malformed_output(text: str) -> None:
    judgement = layer_2(FakeModelJudge(lambda r: ModelResponse(model=PINNED_MODEL, text=text)))
    assert judgement.verdict is RunVerdict.INCONCLUSIVE
    assert "malformed model output" in (judgement.rationale or "")
    assert judgement.layer_2 is not None and judgement.layer_2.checks[0].raw_response == text


@pytest.mark.parametrize("answer", [11, -1, 7.5, "7", True])
def test_a_score_must_be_a_whole_number_from_0_to_10(answer: object) -> None:
    criteria = Criteria(latency_limit_ms=1000, model_checks=[QUALITY])
    response = ModelResponse(
        model=PINNED_MODEL, text=json.dumps({"answer": answer, "rationale": "x"})
    )
    passed, parsed, rationale = interpret_answer(QUALITY, response, PINNED_MODEL)
    assert passed is None and parsed is None and "0 to 10" in rationale
    assert layer_2(FakeModelJudge(lambda r: response), criteria).verdict is RunVerdict.INCONCLUSIVE


def test_an_answer_from_another_model_than_the_pinned_one_is_no_verdict() -> None:
    judgement = layer_2(answering_judge("yes", model="some-other-model"))
    assert judgement.verdict is RunVerdict.INCONCLUSIVE
    assert "not the pinned model" in (judgement.rationale or "") and "DR-004" in judgement.rationale
    unnamed = FakeModelJudge(lambda r: ModelResponse(model=None, text=model_answer("yes").text))
    assert layer_2(unnamed).verdict is RunVerdict.INCONCLUSIVE


def test_yes_no_answers_are_read_case_and_space_insensitively() -> None:
    judge = FakeModelJudge(
        lambda r: ModelResponse(model=PINNED_MODEL, text='{"answer": " Yes ", "rationale": "ok"}')
    )
    assert layer_2(judge).verdict is RunVerdict.PASS


# -- Layer 2 judges only what Layer 1 cannot decide ------------------------------------------


def test_layer_2_is_not_asked_when_layer_1_decided() -> None:
    judge = answering_judge("yes")
    failed = layer_2(judge, Criteria(latency_limit_ms=1, model_checks=[TONE]))
    assert failed.verdict is RunVerdict.FAIL and failed.judge_layer is JudgeLayer.DETERMINISTIC
    passed = layer_2(judge, Criteria(latency_limit_ms=1000))
    assert passed.verdict is RunVerdict.PASS and passed.judge_layer is JudgeLayer.DETERMINISTIC
    assert judge.requests == [], "nothing undecided, nothing asked"


def test_layer_2_is_not_asked_when_there_is_no_response_to_judge() -> None:
    judge = answering_judge("yes")
    unreachable = make_transcript(outcome=RunOutcome.UNREACHABLE, failure="refused")
    judgement = layer_2(judge, transcript=unreachable)
    assert judgement.verdict is RunVerdict.INCONCLUSIVE
    assert judgement.judge_layer is JudgeLayer.DETERMINISTIC
    assert judge.requests == []
    assert undecided_model_checks(judge_run(None, CRITERIA), CRITERIA) == []


def test_layer_2_asks_once_per_undecided_model_check_with_the_criterion_in_the_prompt() -> None:
    criteria = Criteria(latency_limit_ms=1000, model_checks=[TONE, QUALITY])
    judge = FakeModelJudge(lambda r: model_answer("yes" if "polite" in r.prompt else 9))
    judgement = layer_2(judge, criteria, make_transcript(final_response=task_response("Here.")))
    assert judgement.verdict is RunVerdict.PASS
    assert [
        r.prompt.count(c.criterion) for r, c in zip(judge.requests, [TONE, QUALITY], strict=True)
    ] == [1, 1]
    for request in judge.requests:
        assert "<<<AGENT RESPONSE>>>\nHere.\n<<<END AGENT RESPONSE>>>" in request.prompt
        assert "<<<AGENT INPUT>>>\nWhere is my order?\n<<<END AGENT INPUT>>>" in request.prompt
        assert request.timeout_s == 5.0
    assert "whole number from 0 to 10" in judge.requests[1].prompt
    names = [check.name for check in judgement.checks]
    assert names[-2:] == ["model_check tone", "model_check quality"], "Layer 1 order is kept"


def test_a_mix_of_decided_and_undecided_model_checks_stays_inconclusive() -> None:
    criteria = Criteria(latency_limit_ms=1000, model_checks=[TONE, QUALITY])
    judge = FakeModelJudge(
        lambda r: model_answer("yes") if "polite" in r.prompt else ModelResponse(error="down")
    )
    judgement = layer_2(judge, criteria)
    assert (
        judgement.verdict is RunVerdict.INCONCLUSIVE and judgement.judge_layer is JudgeLayer.MODEL
    )
    assert judgement.summary == "inconclusive: Layer 2 could not decide quality"


def test_agent_output_text_covers_every_part_kind() -> None:
    response = task_response("Plain")
    response["artifacts"][0]["parts"] += [
        {"data": {"total": 12}},
        {"raw": "AAAA", "mediaType": "image/png"},
        {"url": "https://x.example/file", "mediaType": "application/pdf"},
    ]
    text = agent_output_text(make_transcript(final_response=response))
    assert text == 'Plain\n{"total": 12}\n[raw part, image/png]\n[url part, application/pdf]'
    message = {"messageId": "m", "role": "ROLE_AGENT", "parts": [{"text": "hi"}]}
    direct = make_transcript(outcome=RunOutcome.RESPONDED_MESSAGE, final_response=message)
    assert agent_output_text(direct) == "hi"


# -- no model configured ----------------------------------------------------------------------


def test_without_a_configured_model_a_model_check_is_inconclusive_and_layer_1_decided(
    tmp_path: Path,
) -> None:
    from suncly.adapters.file_store import FileEvidenceStore
    from suncly.adapters.local_transcripts import LocalTranscriptStorage

    service = JudgeService(
        FileEvidenceStore(tmp_path / "s"),
        LocalTranscriptStorage(tmp_path / "t"),
        FakeClock(),
        SeqIds(),
    )
    assert not service.layer_2_configured
    judgement = service.judge(make_transcript(), a_test_case(CRITERIA))
    assert judgement.verdict is RunVerdict.INCONCLUSIVE
    assert judgement.judge_layer is JudgeLayer.DETERMINISTIC and judgement.rationale is None
    assert judgement.summary.endswith(
        "no judge model is configured (judge_model), so Layer 2 did not run"
    )
    assert Config(home=tmp_path).judge_model is None, "the model id has no default (DR-004)"
    assert model_judge_settings(Config(home=tmp_path)) is None


# -- DR-004: changing the model or the rubric is a configuration change --------------------------


def test_a_judge_configured_only_in_part_is_refused_before_anything_runs(
    services_factory: Callable[..., Services], config: Config
) -> None:
    executor = FakeExecutor(lambda job, n: RunResult(transcript=make_transcript(job)))
    partial = replace(config, judge_model=PINNED_MODEL)
    services = services_factory(
        StaticFetcher({CARD_URL: card_text()}), executor=executor, judge_config=partial
    )
    with pytest.raises(ConfigError, match="judge_endpoint, judge_rubric_version are not set"):
        AttestationService(services).attest(
            AttestRequest(card_url=CARD_URL, sandbox_declared=True, runs=1, approve_as="t")
        )
    assert executor.jobs == [], "nothing ran"
    assert services.store.get_agent(agent_id_for_url(CARD_URL)) is None, "nothing stored"


def test_a_rubric_version_this_build_does_not_carry_is_refused(config: Config) -> None:
    other = replace(
        config,
        judge_model=PINNED_MODEL,
        judge_endpoint="https://judge.example.com/v1",
        judge_rubric_version="2",
    )
    with pytest.raises(
        ConfigError, match="rubric version is not the one this Suncly carries"
    ) as info:
        model_judge_settings(other)
    assert rubric.rubric_hash() in str(info.value)


def test_the_pinned_model_comes_from_the_configuration_alone() -> None:
    judge = answering_judge("yes", model="other-pinned-model")
    judgement = layer_2(judge, model="other-pinned-model")
    assert judgement.verdict is RunVerdict.PASS
    assert judge.requests[0].model == "other-pinned-model"
    assert judgement.layer_2 is not None and judgement.layer_2.model == "other-pinned-model"
    assert layer_2(judge, model=PINNED_MODEL).verdict is RunVerdict.INCONCLUSIVE, (
        "the same endpoint answering from another model than the one now pinned is no verdict"
    )


def test_the_rubric_is_versioned_and_hashed_and_a_changed_frame_changes_the_hash() -> None:
    assert rubric.rubric_hash().startswith("sha256:")
    assert rubric.rubric_hash() != rubric.rubric_hash(frame=rubric.RUBRIC_FRAME + " ")
    assert rubric.rubric_hash() != rubric.rubric_hash(version="2")
    prompt = rubric.build_prompt(TONE, "in", "out")
    assert prompt.startswith(rubric.RUBRIC_FRAME[:60]) and TONE.criterion in prompt
    long_output = "x" * (rubric.MAX_EMBEDDED_CHARS + 5)
    assert "5 more characters not shown to the judge" in rubric.build_prompt(
        TONE, "in", long_output
    )


# -- provenance in the evidence document (OQ-D4, decided) and the run record -------------------


def contract_file_with_model_checks(card: str, *checks: ModelCheck) -> ContractFile:
    criteria = Criteria(
        latency_limit_ms=2000, output_modes=["text/plain"], model_checks=list(checks)
    )
    return ContractFile(
        suncly_contract_file=1,
        card_hash=parse_agent_card(card).card_hash,
        test_cases=[
            ContractFileTestCase(
                skill_id="echo", input={"text": "hello"}, criteria=criteria.model_dump(mode="json")
            )
        ],
    )


def judged_config(config: Config, endpoint: str = "https://judge.example.com/v1") -> Config:
    return replace(
        config,
        judge_model=PINNED_MODEL,
        judge_endpoint=endpoint,
        judge_rubric_version=rubric.RUBRIC_VERSION,
        judge_timeout_s=5.0,
    )


def test_the_evidence_document_records_everything_layer_2_saw_and_said(
    services_factory: Callable[..., Services], config: Config
) -> None:
    card = card_text()
    judge = FakeModelJudge(lambda r: model_answer("yes", rationale="HELLO is a complete answer"))
    services = services_factory(
        StaticFetcher({CARD_URL: card}), model_judge=judge, judge_config=judged_config(config)
    )
    outcome = AttestationService(services).attest(
        AttestRequest(
            card_url=CARD_URL,
            sandbox_declared=True,
            runs=2,
            approve_as="t",
            contract_file=contract_file_with_model_checks(card, TONE),
        )
    )
    assert outcome.bundle is not None and outcome.attestation is not None
    result = outcome.bundle.results[0]
    assert (result.pass_count, result.fail_count, result.inconclusive_count) == (2, 0, 0), (
        "results are counted per test case (OQ-PO6)"
    )
    for evidence in outcome.bundle.runs:
        run = evidence.run
        assert run.verdict is RunVerdict.PASS and run.judge_layer is JudgeLayer.MODEL
        assert run.rationale == "tone: HELLO is a complete answer"
        judgement = evidence.document["judgement"]
        assert judgement["judge_layer"] == "model" and judgement["rationale"] == run.rationale
        layer_2 = judgement["layer_2"]
        assert layer_2["model"] == PINNED_MODEL
        assert layer_2["rubric_version"] == rubric.RUBRIC_VERSION
        assert layer_2["rubric_hash"] == rubric.rubric_hash()
        [record] = layer_2["checks"]
        assert record["criterion"] == TONE.criterion and record["name"] == "tone"
        assert record["expected"] == "yes_no" and record["pass_rule"] == "yes"
        assert record["prompt"] == judge.requests[0].prompt
        assert record["raw_response"] == model_answer("yes", "HELLO is a complete answer").text
        assert record["answer"] == "yes" and record["passed"] is True
        assert record["rationale"] == "HELLO is a complete answer"
    assert outcome.bundle.signature_payload is not None
    assert "layer_2" not in json.dumps(outcome.bundle.signature_payload), (
        "the payload format is unchanged; the provenance is bound through the document hash"
    )
    semantic = [i for i in outcome.bundle.not_tested if i.category == "semantic correctness"]
    assert semantic == [], "every test case carried a model check and Layer 2 judged it"


def test_layer_1_verdicts_have_no_rationale_and_a_layer_1_document_carries_no_layer_2(
    services_factory: Callable[..., Services],
) -> None:
    services = services_factory(StaticFetcher({CARD_URL: card_text()}))
    outcome = AttestationService(services).attest(
        AttestRequest(card_url=CARD_URL, sandbox_declared=True, runs=1, approve_as="t")
    )
    assert outcome.bundle is not None
    [evidence] = outcome.bundle.runs
    assert evidence.run.judge_layer is JudgeLayer.DETERMINISTIC and evidence.run.rationale is None
    assert evidence.document["judgement"]["layer_2"] is None


def test_what_was_not_tested_names_semantic_correctness_truthfully() -> None:
    plain = a_test_case(Criteria(latency_limit_ms=1000))
    with_check = a_test_case(CRITERIA).model_copy(update={"id": UUID(int=5), "skill_id": "b"})
    [item] = semantic_correctness([plain], [], layer_2_configured=False)
    assert "no test case carries a model check" in item.detail
    [item] = semantic_correctness([plain, with_check], [], layer_2_configured=False)
    assert "1 test case(s) carry model checks, but no judge model is configured" in item.detail
    items = semantic_correctness([plain, with_check], [], layer_2_configured=True)
    assert [i.detail for i in items] == [
        (
            "Layer 1 checks structure, state, output modes and latency; the test cases of "
            "skill(s) 'orders' carry no model check, so the content of their answers was not judged"
        ),
        (
            "1 test case(s) carry model checks but no run of theirs reached Layer 2: Layer 1 "
            "decided or could not read every run"
        ),
    ]


# -- the judge subprocess: the Anthropic Messages API on a loopback fake -------------------------

MESSAGES_API_PATH = "/v1/messages"
REQUEST_ID = "req_011CSHoEeqs5C35K2UUqR7Fy"

Behaviour = Callable[[dict[str, str], dict[str, Any]], tuple[int, bytes]]


class EndpointServer:
    """A loopback stand-in for the Messages API: ``behaviour(headers, body) -> (status, body)``.

    Header names are handed to the behaviour in lower case, as HTTP treats them.
    """

    def __init__(self, behaviour: Behaviour):
        self.behaviour = behaviour
        self.requests: list[dict[str, Any]] = []
        self.headers_seen: list[dict[str, str]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                headers = {name.lower(): value for name, value in self.headers.items()}
                outer.requests.append(body)
                outer.headers_seen.append(headers)
                status, payload = outer.behaviour(headers, body)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: Any) -> None:
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> EndpointServer:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._server.shutdown()
        self._server.server_close()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}{MESSAGES_API_PATH}"


def message_body(
    model: str | None, text: str | None, stop_reason: str = "end_turn", **extra: Any
) -> bytes:
    """A Messages API answer in the verified shape; ``text`` ``None`` leaves no text block."""
    message: dict[str, Any] = {
        "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [] if text is None else [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 512, "output_tokens": 40},
        **extra,
    }
    if model is None:
        del message["model"]
    return json.dumps(message).encode()


def error_body(error_type: str, message: str) -> bytes:
    """The API's error shape: ``type`` ``error``, an ``error`` object and a ``request_id``."""
    return json.dumps(
        {
            "type": "error",
            "error": {"type": error_type, "message": message},
            "request_id": REQUEST_ID,
        }
    ).encode()


def echoing_endpoint(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
    """Answers yes, and echoes the key it received into the rationale (a leaky endpoint)."""
    answer = {"answer": "yes", "rationale": f"seen {headers.get('authorization')}"}
    return 200, message_body(body["model"], json.dumps(answer))


def judge_job(endpoint: str, **overrides: object) -> JudgeJob:
    data: dict[str, object] = {
        "endpoint": endpoint,
        "model": PINNED_MODEL,
        "prompt": rubric.build_prompt(TONE, "in", "out"),
        "timeout_s": 5.0,
    }
    data.update(overrides)
    return JudgeJob.model_validate(data)


def run_judge_process(job: JudgeJob | str, env: dict[str, str]) -> tuple[ModelResponse, str]:
    stdin = io.StringIO(job if isinstance(job, str) else job.model_dump_json())
    stdout = io.StringIO()
    assert process.main(stdin, stdout, env) == 0
    text = stdout.getvalue()
    return ModelResponse.model_validate_json(text), text


def ask(behaviour: Behaviour, **overrides: object) -> tuple[ModelResponse, str, EndpointServer]:
    """One judge question to a loopback endpoint with the test key; the key must never come back."""
    with EndpointServer(behaviour) as server:
        response, text = run_judge_process(
            judge_job(server.url, **overrides), {JUDGE_KEY_ENV_VAR: KEY}
        )
    assert KEY not in text
    return response, text, server


def test_the_subprocess_asks_the_messages_api_in_its_wire_shape_and_redacts_the_key() -> None:
    response, _, server = ask(echoing_endpoint)
    assert response.model == PINNED_MODEL and response.error is None
    assert "seen Bearer [REDACTED]" in (response.text or "")
    assert interpret_answer(TONE, response, PINNED_MODEL)[0] is True
    [request], [headers] = server.requests, server.headers_seen
    job = judge_job(server.url)
    assert request == process.build_request(job)
    assert request == {
        "model": PINNED_MODEL,
        "max_tokens": process.MAX_OUTPUT_TOKENS,
        "messages": [{"role": "user", "content": job.prompt}],
        "output_config": {"format": {"type": "json_schema", "schema": process.ANSWER_SCHEMA}},
    }
    assert headers["anthropic-version"] == "2023-06-01"
    assert headers["content-type"] == "application/json"
    assert headers["authorization"] == f"Bearer {KEY}"
    assert "x-api-key" not in headers, "the key travels in one header"


def test_the_request_asks_for_a_strict_json_object_with_the_rubric_keys_only() -> None:
    schema = process.ANSWER_SCHEMA
    assert schema["type"] == "object" and schema["additionalProperties"] is False
    assert sorted(schema["required"]) == ["answer", "rationale"] == sorted(schema["properties"])
    assert schema["properties"]["rationale"] == {"type": "string"}
    assert set(schema["properties"]["answer"]["type"]) == {"string", "integer"}, (
        "yes/no or 0 to 10; the core checks the value against the check's answer shape"
    )


@pytest.mark.parametrize(
    ("model", "generation", "temperature"),
    [
        ("claude-haiku-4-5-20251001", (4, 5), 0),
        ("claude-haiku-4-5", (4, 5), 0),
        ("claude-opus-4-5-20251101", (4, 5), 0),
        ("claude-opus-4-6", (4, 6), 0),
        ("claude-sonnet-4-6", (4, 6), 0),
        ("claude-opus-4-7", (4, 7), None),
        ("claude-sonnet-5", (5, 0), None),
        ("claude-sonnet-5-5", (5, 5), None),
        ("claude-opus-5-5", (5, 5), None),
        ("claude-fable-5-1", (5, 1), None),
        ("claude-mythos-preview", None, None),
        (PINNED_MODEL, None, None),
    ],
)
def test_temperature_0_is_sent_only_to_the_models_whose_api_accepts_sampling(
    model: str, generation: tuple[int, int] | None, temperature: int | None
) -> None:
    assert process.model_generation(model) == generation
    assert process.accepts_sampling(model) is (temperature is not None)
    body = process.build_request(judge_job("https://api.anthropic.com/v1/messages", model=model))
    assert body.get("temperature") == temperature
    assert "thinking" not in body and "effort" not in body["output_config"], (
        "model-specific thinking settings are not sent; the API rejects them on the wrong model"
    )


def test_the_subprocess_answers_an_error_without_a_key_or_with_a_bad_job() -> None:
    with EndpointServer(echoing_endpoint) as server:
        response, _ = run_judge_process(judge_job(server.url), {})
        assert response.error is not None and "no model key" in response.error
        assert server.requests == [], "no key, no call"
    response, _ = run_judge_process("{not json", {JUDGE_KEY_ENV_VAR: KEY})
    assert response.error is not None and "invalid judge job" in response.error


def test_the_subprocess_turns_api_errors_into_errors_with_the_key_redacted() -> None:
    def unauthorised(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
        return 401, error_body("authentication_error", f"bad key {headers.get('authorization')}")

    response, _, _ = ask(unauthorised)
    assert response.error == (
        "the Messages API answered HTTP 401 authentication_error: bad key Bearer [REDACTED] "
        f"(request {REQUEST_ID})"
    )
    assert response.text is None and response.model is None

    def overloaded(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
        return 529, error_body("overloaded_error", "Overloaded")

    response, _, _ = ask(overloaded)
    assert response.error is not None and response.error.startswith(
        "the Messages API answered HTTP 529 overloaded_error: Overloaded"
    )

    def failing(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
        return 500, f"boom {headers.get('authorization')}".encode()

    response, _, _ = ask(failing)
    assert response.error == "the Messages API answered HTTP 500: boom Bearer [REDACTED]"

    def not_json(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
        return 200, b"<html>"

    response, _, _ = ask(not_json)
    assert response.error is not None and "not JSON" in response.error

    def not_a_message(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
        return 200, error_body("api_error", "odd")

    response, _, _ = ask(not_a_message)
    assert response.error == "the Messages API answered with a 'error' object, not a message"


@pytest.mark.parametrize(
    ("stop_reason", "extra", "expected"),
    [
        (
            "refusal",
            {"stop_details": {"type": "refusal", "category": "cyber", "explanation": "x"}},
            "the model refused to answer (stop_reason 'refusal', category 'cyber')",
        ),
        ("refusal", {"stop_details": None}, "category None"),
        ("max_tokens", {}, "the answer is incomplete (stop_reason 'max_tokens'"),
        ("model_context_window_exceeded", {}, "the answer is incomplete"),
        ("tool_use", {}, "the model stopped before a complete answer (stop_reason 'tool_use')"),
        ("pause_turn", {}, "stopped before a complete answer"),
    ],
)
def test_a_refusal_a_truncated_answer_or_an_unexpected_stop_is_no_verdict(
    stop_reason: str, extra: dict[str, Any], expected: str
) -> None:
    def endpoint(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
        well_formed = model_answer("yes").text or ""
        return 200, message_body(body["model"], well_formed, stop_reason=stop_reason, **extra)

    response, _, _ = ask(endpoint)
    assert response.error is not None and expected in response.error
    assert response.text is None, "an incomplete answer is never handed to the core as text"
    passed, answer, rationale = interpret_answer(TONE, response, PINNED_MODEL)
    assert passed is None and answer is None and rationale.startswith(NO_VERDICT)


def test_an_answer_attributed_to_another_model_is_carried_and_is_no_verdict() -> None:
    def other_model(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
        return 200, message_body("claude-other-model", model_answer("yes").text)

    response, _, _ = ask(other_model)
    assert response.error is None and response.model == "claude-other-model"
    passed, _, rationale = interpret_answer(TONE, response, PINNED_MODEL)
    assert passed is None and "not the pinned model" in rationale

    def unnamed(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
        return 200, message_body(None, model_answer("yes").text)

    response, _, _ = ask(unnamed)
    assert response.error is None and response.model is None
    assert interpret_answer(TONE, response, PINNED_MODEL)[0] is None


def test_the_text_comes_from_the_text_blocks_and_a_message_without_one_is_no_answer() -> None:
    def with_thinking(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
        message = json.loads(message_body(body["model"], model_answer("yes").text))
        message["content"].insert(0, {"type": "thinking", "thinking": "", "signature": "s"})
        return 200, json.dumps(message).encode()

    response, _, _ = ask(with_thinking)
    assert response.text == model_answer("yes").text
    assert interpret_answer(TONE, response, PINNED_MODEL)[0] is True

    def no_text(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
        return 200, message_body(body["model"], None)

    response, _, _ = ask(no_text)
    assert response.error == "the message carries no text block"


def test_the_subprocess_reports_a_timeout_as_such() -> None:
    import time

    def slow(headers: dict[str, str], body: dict[str, Any]) -> tuple[int, bytes]:
        time.sleep(0.5)
        return 200, b"{}"

    with EndpointServer(slow) as server:
        response, _ = run_judge_process(
            judge_job(server.url, timeout_s=0.05), {JUDGE_KEY_ENV_VAR: KEY}
        )
    assert response.timed_out and response.error is not None and "timeout" in response.error


def test_the_subprocess_talks_to_the_configured_endpoint_host_only() -> None:
    with pytest.raises(process.EndpointRefusedError, match="must use https"):
        process.endpoint_client("http://judge.example.com/v1", 1.0)
    with process.endpoint_client("https://judge.example.com/v1", 1.0) as client:
        with pytest.raises(
            process.EndpointRefusedError, match="refused a request to https://other"
        ):
            client.get("https://other.example.com/")
        with pytest.raises(process.EndpointRefusedError, match="refused a request"):
            client.get("https://judge.example.com:8443/v1")
    response, _ = run_judge_process(
        judge_job("http://judge.example.com/v1"), {JUDGE_KEY_ENV_VAR: KEY}
    )
    assert response.error is not None and "must use https" in response.error
    assert process.is_loopback_host("localhost") and process.is_loopback_host("[::1]")
    assert not process.is_loopback_host("judge.example.com") and not process.is_loopback_host(None)


def test_the_key_reader_hides_the_value_and_redacts_it() -> None:
    key = read_key({JUDGE_KEY_ENV_VAR: f" {KEY} "})
    assert key.value == KEY and KEY not in repr(key)
    assert key.headers() == {"Authorization": f"Bearer {KEY}"}
    assert key.redact(f"x {KEY} y {KEY}") == "x [REDACTED] y [REDACTED]"
    empty = read_key({})
    assert empty.value is None and empty.headers() == {} and empty.redact(KEY) == KEY
    assert repr(ModelKey("v")) == "ModelKey(<set>)"


# -- the subprocess adapter: a from-scratch environment with one variable ----------------------


def test_the_child_environment_holds_the_key_and_nothing_else_from_the_parent() -> None:
    parent = {
        JUDGE_KEY_ENV_VAR: KEY,
        "SUNCLY_AGENT_AUTHORIZATION": "Bearer agent-secret",
        "DATABASE_URL": "postgresql://x/y",
        "HTTPS_PROXY": "http://proxy:3128",
        "PATH": "/usr/bin",
        "SYSTEMROOT": r"C:\Windows",
    }
    assert child_environment(parent) == {JUDGE_KEY_ENV_VAR: KEY, "SYSTEMROOT": r"C:\Windows"}
    assert child_environment({}) == {}


def test_the_adapter_spawns_the_judge_process_with_the_from_scratch_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        seen["command"] = command
        seen.update(kwargs)
        return subprocess.CompletedProcess(
            args=command, returncode=0, stdout=model_answer("yes").model_dump_json().encode()
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    adapter = SubprocessModelJudge(
        "https://judge.example.com/v1", {JUDGE_KEY_ENV_VAR: KEY, "HOME": "/h"}
    )
    response = adapter.ask(ModelRequest(model=PINNED_MODEL, prompt="p", timeout_s=3.0))
    assert response.model == PINNED_MODEL
    assert seen["command"][1:] == ["-m", "suncly.judge.process"]
    assert seen["env"] == {JUDGE_KEY_ENV_VAR: KEY}
    assert seen["timeout"] == 13.0 and seen["capture_output"] is True
    job = JudgeJob.model_validate_json(seen["input"])
    assert job.endpoint == "https://judge.example.com/v1" and job.model == PINNED_MODEL


def test_the_adapter_treats_a_killed_silent_or_garbled_process_as_a_model_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ModelRequest(model=PINNED_MODEL, prompt="p", timeout_s=1.0)
    adapter = SubprocessModelJudge("https://judge.example.com/v1", {})
    missing = SubprocessModelJudge(
        "https://judge.example.com/v1", {}, python=str(Path("no") / "python")
    )
    assert "could not start" in (missing.ask(request).error or "")

    def killed(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(cmd="x", timeout=11.0)

    monkeypatch.setattr(subprocess, "run", killed)
    response = adapter.ask(request)
    assert response.timed_out and "was killed" in (response.error or "")

    def silent(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            args=[], returncode=3, stdout=b"", stderr=b"the key is " + KEY.encode()
        )

    monkeypatch.setattr(subprocess, "run", silent)
    response = adapter.ask(request)
    assert "no answer" in (response.error or "") and KEY not in response.model_dump_json()

    def garbage(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=b"not json", stderr=b"")

    monkeypatch.setattr(subprocess, "run", garbage)
    assert "unreadable answer" in (adapter.ask(request).error or "")


def test_the_fixture_key_is_never_a_real_key_of_this_process() -> None:
    """KEY is a fixture: no leak test may pass by finding a credential this process holds.

    The live smoke test (tests/live) is the one reason the real variable may be set.
    """
    assert KEY not in os.environ.values()
    assert os.environ.get(JUDGE_KEY_ENV_VAR, "") != KEY


# -- the key never appears in any evidence, report or log -----------------------------------------


class RecordingProgress:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def on_event(self, event: str, **data: Any) -> None:
        self.events.append((event, data))


def files_under(folder: Path) -> Iterator[Path]:
    yield from (p for p in folder.rglob("*") if p.is_file())


def test_a_real_judge_subprocess_against_a_leaky_endpoint_leaves_the_key_nowhere(
    services_factory: Callable[..., Services], config: Config, tmp_path: Path
) -> None:
    card = card_text()
    progress = RecordingProgress()
    with EndpointServer(echoing_endpoint) as server:
        # The real process environment stands in for the parent's; the adapter keeps the key
        # and what Python needs to start on this platform, and drops the rest.
        adapter = SubprocessModelJudge(server.url, {**os.environ, JUDGE_KEY_ENV_VAR: KEY})
        services = services_factory(
            StaticFetcher({CARD_URL: card}),
            model_judge=adapter,
            judge_config=judged_config(config, endpoint=server.url),
        )
        services.progress = progress
        services.report_writer = FolderReportWriter(tmp_path / "out", services.transcripts)
        outcome = AttestationService(services).attest(
            AttestRequest(
                card_url=CARD_URL,
                sandbox_declared=True,
                runs=1,
                approve_as="t",
                contract_file=contract_file_with_model_checks(card, TONE),
            )
        )
    assert outcome.bundle is not None and outcome.report_dir is not None
    [evidence] = outcome.bundle.runs
    assert evidence.run.verdict is RunVerdict.PASS and evidence.run.judge_layer is JudgeLayer.MODEL
    assert evidence.run.rationale == "tone: seen Bearer [REDACTED]", "the leak came back redacted"
    everything = [
        *files_under(outcome.report_dir),
        *files_under(config.transcripts_dir),
        *files_under(config.store_dir),
    ]
    assert len(everything) >= 5
    for path in everything:
        assert KEY not in path.read_text(encoding="utf-8", errors="replace"), path
    log = json.dumps([(e, {k: str(v) for k, v in d.items()}) for e, d in progress.events])
    assert KEY not in log and "run_recorded" in log
    assert KEY not in json.dumps(outcome.bundle.model_dump(mode="json"))
    assert KEY not in json.dumps(evidence.document)


def test_the_runner_never_receives_the_model_key(services_factory: Callable[..., Services]) -> None:
    """The judge job is not a run job: the two subprocesses share no field and no variable."""
    assert "SUNCLY_JUDGE" not in json.dumps(RunJob.model_json_schema())
    assert "key" not in {f.lower() for f in JudgeJob.model_fields}
    assert "authorization" not in {f.lower() for f in JudgeJob.model_fields}
    assert JUDGE_KEY_ENV_VAR not in json.dumps(ModelRequest.model_json_schema())
