"""The Judge (schema §2): Layer 1, deterministic; Layer 2, the pinned model.

Layer 1 checks valid schema, final task state, required fields and the latency
limit, plus the card's declared output modes. Layer 2 judges only the model
checks Layer 1 cannot decide, with the versioned rubric frame of
``core/rubric.py`` and the one model pinned in the configuration (DR-004). The
verdict is ``pass``, ``fail`` or ``inconclusive``; ``inconclusive`` is never
counted as a pass. No model configured, a model failure, a timeout, an answer
from another model or malformed output all give ``inconclusive``, never
``pass``. Everything Layer 2 saw and said goes into the per-run evidence
document (OQ-D4, decided 2026-10-07). Pure: the model is reached only through
the ``ModelJudge`` port.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any
from uuid import UUID

import jsonschema

from suncly.core import rubric
from suncly.core.config import Config
from suncly.domain import a2a
from suncly.domain.canonical import canonical_json
from suncly.domain.criteria import Criteria, ModelCheck, parse_criteria, parse_input
from suncly.domain.errors import ConfigError, TranscriptExistsError
from suncly.domain.models import JsonObject, JudgeLayer, Run, RunVerdict, TestCase
from suncly.domain.transcript import RunOutcome, Transcript
from suncly.ports.clock import Clock, IdGenerator
from suncly.ports.model_judge import ModelJudge, ModelRequest, ModelResponse
from suncly.ports.store import EvidenceStore
from suncly.ports.transcripts import TranscriptStorage

#: Prefix of the check name of every model check, in Layer 1 and Layer 2 alike.
MODEL_CHECK_PREFIX = "model_check "

#: Prefix of every rationale that explains why Layer 2 produced no verdict.
NO_VERDICT = "no model verdict: "


@dataclass(frozen=True)
class CheckResult:
    """One check. ``passed`` is ``None`` when the layer that ran could not decide it."""

    name: str
    passed: bool | None
    detail: str

    def to_json(self) -> JsonObject:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class ModelCheckRecord:
    """Everything Layer 2 saw and said for one model check (OQ-D4, decided)."""

    name: str
    criterion: str
    expected: str
    pass_rule: str
    prompt: str
    raw_response: str | None
    answer: str | int | None
    passed: bool | None
    rationale: str

    def to_json(self) -> JsonObject:
        return {
            "name": self.name,
            "criterion": self.criterion,
            "expected": self.expected,
            "pass_rule": self.pass_rule,
            "prompt": self.prompt,
            "raw_response": self.raw_response,
            "answer": self.answer,
            "passed": self.passed,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class Layer2Record:
    """The pinned model and rubric a verdict came from, and each check's record."""

    model: str
    rubric_version: str
    rubric_hash: str
    checks: list[ModelCheckRecord]

    def to_json(self) -> JsonObject:
        return {
            "model": self.model,
            "rubric_version": self.rubric_version,
            "rubric_hash": self.rubric_hash,
            "checks": [check.to_json() for check in self.checks],
        }


@dataclass(frozen=True)
class Judgement:
    verdict: RunVerdict
    judge_layer: JudgeLayer
    checks: list[CheckResult] = field(default_factory=list)
    summary: str = ""
    rationale: str | None = None
    """Layer 2's rationale; stored on the run (schema §2). ``None`` when Layer 1 decided."""
    layer_2: Layer2Record | None = None

    def to_json(self) -> JsonObject:
        return {
            "verdict": self.verdict.value,
            "judge_layer": self.judge_layer.value,
            "summary": self.summary,
            "checks": [check.to_json() for check in self.checks],
            "rationale": self.rationale,
            "layer_2": self.layer_2.to_json() if self.layer_2 is not None else None,
        }


def _verdict_from(checks: list[CheckResult]) -> RunVerdict:
    """``fail`` if any check failed; else ``inconclusive`` if any is undecided; else ``pass``."""
    if any(check.passed is False for check in checks):
        return RunVerdict.FAIL
    if any(check.passed is None for check in checks):
        return RunVerdict.INCONCLUSIVE
    return RunVerdict.PASS


def resolve_pointer(document: Any, pointer: str) -> Any:
    """Resolve an RFC 6901 JSON pointer. Raises ``KeyError`` when the path does not exist."""
    current = document
    if pointer == "":
        return current
    for raw_token in pointer.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                raise KeyError(pointer)
            current = current[token]
        elif isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError) as exc:
                raise KeyError(pointer) from exc
        else:
            raise KeyError(pointer)
    return current


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


# -- Layer 1 -------------------------------------------------------------------------------


def judge_run(transcript: Transcript | None, criteria: Criteria) -> Judgement:
    """Layer 1 verdict for one run. Pure: no I/O, no model."""
    layer = JudgeLayer.DETERMINISTIC
    if transcript is None:
        return Judgement(
            RunVerdict.INCONCLUSIVE,
            layer,
            [CheckResult("transcript_readable", None, "Suncly could not read the transcript")],
            "inconclusive: the transcript could not be read (Suncly's own fault, OQ-A11)",
        )
    if transcript.outcome is RunOutcome.UNREACHABLE:
        return Judgement(
            RunVerdict.INCONCLUSIVE,
            layer,
            [CheckResult("response_received", None, transcript.failure or "no connection")],
            "inconclusive: the agent was unreachable, so there is no response to judge",
        )
    if transcript.outcome is RunOutcome.TIMEOUT:
        return Judgement(
            RunVerdict.FAIL,
            layer,
            [
                CheckResult(
                    "latency_limit",
                    False,
                    f"no final state within the timeout; the latency limit is "
                    f"{criteria.latency_limit_ms} ms",
                )
            ],
            "fail: the agent did not finish in time",
        )
    if transcript.outcome is RunOutcome.PROTOCOL_ERROR or transcript.final_response is None:
        return Judgement(
            RunVerdict.FAIL,
            layer,
            [CheckResult("valid_schema", False, transcript.failure or "no usable A2A response")],
            "fail: the response is not a valid A2A response",
        )

    response = transcript.final_response
    is_task = transcript.outcome is RunOutcome.RESPONDED_TASK
    checks: list[CheckResult] = []

    problems = (
        a2a.structural_problems_of_task(response)
        if is_task
        else a2a.structural_problems_of_message(response)
    )
    checks.append(
        CheckResult(
            "valid_schema",
            not problems,
            "; ".join(problems)
            if problems
            else f"a well-formed {'Task' if is_task else 'Message'}",
        )
    )

    if is_task:
        state = transcript.final_task_state
        checks.append(
            CheckResult(
                "final_task_state",
                state == criteria.final_state,
                f"expected {criteria.final_state}, observed {state}",
            )
        )
    else:
        checks.append(
            CheckResult(
                "final_task_state",
                criteria.accept_direct_message,
                "the agent answered with a direct Message instead of a Task"
                + ("; accepted by the criteria" if criteria.accept_direct_message else ""),
            )
        )

    latency = transcript.latency_ms
    checks.append(
        CheckResult(
            "latency_limit",
            latency is not None and latency <= criteria.latency_limit_ms,
            f"{latency} ms against a limit of {criteria.latency_limit_ms} ms",
        )
    )

    parts = a2a.output_parts(response, is_task)
    if criteria.response_present:
        with_content = [part for part in parts if a2a.part_has_content(part)]
        checks.append(
            CheckResult(
                "response_present",
                bool(with_content),
                f"{len(with_content)} output part(s) with content",
            )
        )

    if criteria.output_modes is not None:
        allowed = set(criteria.output_modes)
        offending = [
            a2a.part_media_type(part) or "<none>"
            for part in parts
            if (a2a.part_media_type(part) or "") not in allowed
        ]
        checks.append(
            CheckResult(
                "output_modes",
                not offending,
                f"declared {sorted(allowed)}; "
                + (f"offending media types: {offending}" if offending else "every part conforms"),
            )
        )

    for pointer in criteria.required_fields:
        try:
            value = resolve_pointer(response, pointer)
            present = not _is_empty(value)
            detail = "present" if present else "present but empty"
        except KeyError:
            present, detail = False, "missing"
        checks.append(CheckResult(f"required_field {pointer}", present, detail))

    if criteria.response_schema is not None:
        validator_cls = jsonschema.validators.validator_for(criteria.response_schema)
        errors = sorted(
            validator_cls(criteria.response_schema).iter_errors(response), key=lambda e: e.path
        )
        checks.append(
            CheckResult(
                "response_schema",
                not errors,
                "; ".join(error.message for error in errors[:5]) if errors else "conforms",
            )
        )

    for check in criteria.model_checks:
        checks.append(
            CheckResult(
                MODEL_CHECK_PREFIX + check.name,
                None,
                f"Layer 1 cannot decide '{check.criterion}'; it needs Layer 2",
            )
        )

    verdict = _verdict_from(checks)
    failed = [check.name for check in checks if check.passed is False]
    undecided = [check.name for check in checks if check.passed is None]
    if verdict is RunVerdict.FAIL:
        summary = f"fail: {', '.join(failed)}"
    elif verdict is RunVerdict.INCONCLUSIVE:
        summary = f"inconclusive: Layer 1 cannot decide {', '.join(undecided)}"
    else:
        summary = "pass: every Layer 1 check passed"
    return Judgement(verdict, layer, checks, summary)


# -- Layer 2 -------------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelJudgeSettings:
    """The pinned model and rubric (DR-004), from the configuration and nowhere else."""

    model: str
    rubric_version: str
    timeout_s: float


def model_judge_settings(config: Config) -> ModelJudgeSettings | None:
    """``None`` when no judge is configured; ``ConfigError`` when it is configured only in part.

    Changing the model or the rubric is a configuration change (DR-004): the three
    settings are set together, and the rubric version must be the one this build carries.
    """
    values = {
        "judge_model": config.judge_model,
        "judge_endpoint": config.judge_endpoint,
        "judge_rubric_version": config.judge_rubric_version,
    }
    if all(value is None for value in values.values()):
        return None
    missing = [name for name, value in values.items() if value is None]
    if missing:
        raise ConfigError(
            "The judge configuration is incomplete, so nothing ran.",
            f"Layer 2 needs judge_model, judge_endpoint and judge_rubric_version together; "
            f"{', '.join(missing)} {'is' if len(missing) == 1 else 'are'} not set.",
            "Set all three (docs/STAGE_4_BRIEF.md), or none to run Layer 1 only.",
        )
    if config.judge_rubric_version != rubric.RUBRIC_VERSION:
        raise ConfigError(
            "The configured rubric version is not the one this Suncly carries, so nothing ran.",
            f"judge_rubric_version is {config.judge_rubric_version!r}; this build carries "
            f"rubric {rubric.RUBRIC_VERSION!r} ({rubric.rubric_hash()}).",
            f"Review the rubric frame in core/rubric.py, then set judge_rubric_version to "
            f"{rubric.RUBRIC_VERSION!r} (DR-004: a rubric change is a configuration change).",
        )
    assert config.judge_model is not None and config.judge_rubric_version is not None
    return ModelJudgeSettings(
        model=config.judge_model,
        rubric_version=config.judge_rubric_version,
        timeout_s=config.judge_timeout_s,
    )


def undecided_model_checks(judgement: Judgement, criteria: Criteria) -> list[ModelCheck]:
    """The model checks Layer 1 left undecided, when they are all that is undecided.

    Empty when Layer 1 failed the run (fail wins), passed it, or could not decide for
    another reason (no transcript, no response): then there is nothing Layer 2 can judge.
    """
    if judgement.verdict is not RunVerdict.INCONCLUSIVE:
        return []
    undecided = {check.name for check in judgement.checks if check.passed is None}
    by_name = {MODEL_CHECK_PREFIX + check.name: check for check in criteria.model_checks}
    if not undecided or not undecided <= by_name.keys():
        return []
    return [by_name[name] for name in by_name if name in undecided]


def agent_input_text(test_case: TestCase) -> str:
    parsed = parse_input(test_case.input)
    if parsed.text is not None:
        return parsed.text
    return json.dumps(parsed.parts, ensure_ascii=False, sort_keys=True)


def agent_output_text(transcript: Transcript) -> str:
    """The agent's output parts as text: text verbatim, data as JSON, the rest by its key."""
    if transcript.final_response is None:
        return ""
    is_task = transcript.outcome is RunOutcome.RESPONDED_TASK
    pieces: list[str] = []
    for part in a2a.output_parts(transcript.final_response, is_task):
        key = a2a.part_content_key(part)
        if key == "text":
            pieces.append(str(part["text"]))
        elif key == "data":
            pieces.append(json.dumps(part["data"], ensure_ascii=False, sort_keys=True))
        elif key is not None:
            media = a2a.part_media_type(part) or "unknown media type"
            pieces.append(f"[{key} part, {media}]")
    return "\n".join(pieces)


def _parse_answer(check: ModelCheck, text: str) -> tuple[str | int, str]:
    """The answer and the rationale from the model's text, or ``ValueError`` saying why not."""
    try:
        loaded = json.loads(text.strip())
    except ValueError as exc:
        raise ValueError(f"the output is not JSON ({exc.__class__.__name__})") from exc
    if not isinstance(loaded, dict):
        raise ValueError("the output is not a JSON object")
    unknown = sorted(set(loaded) - {"answer", "rationale"})
    if unknown:
        raise ValueError(f"the output carries unknown keys {unknown}")
    rationale = loaded.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("the output has no rationale text")
    raw = loaded.get("answer")
    if check.expected == "yes_no":
        if not isinstance(raw, str) or raw.strip().lower() not in ("yes", "no"):
            raise ValueError(f"the answer is not 'yes' or 'no': {raw!r}")
        return raw.strip().lower(), rationale.strip()
    if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= 10:
        raise ValueError(f"the answer is not a whole number from 0 to 10: {raw!r}")
    return raw, rationale.strip()


def interpret_answer(
    check: ModelCheck, response: ModelResponse, pinned_model: str
) -> tuple[bool | None, str | int | None, str]:
    """``(passed, answer, rationale)``; ``passed`` is ``None`` whenever there is no verdict."""
    if response.error is not None or response.text is None:
        return None, None, NO_VERDICT + (response.error or "the model gave no answer")
    if response.model != pinned_model:
        return (
            None,
            None,
            NO_VERDICT + f"the answer came from model {response.model!r}, not the pinned model "
            f"{pinned_model!r} (DR-004)",
        )
    try:
        answer, rationale = _parse_answer(check, response.text)
    except ValueError as exc:
        return None, None, NO_VERDICT + f"malformed model output: {exc}"
    return check.passes(answer), answer, rationale


def judge_with_model(
    layer_1: Judgement,
    criteria: Criteria,
    transcript: Transcript,
    test_case: TestCase,
    settings: ModelJudgeSettings,
    model_judge: ModelJudge,
) -> Judgement:
    """Layer 2 for the model checks Layer 1 left undecided; ``layer_1`` unchanged otherwise."""
    pending = undecided_model_checks(layer_1, criteria)
    if not pending:
        return layer_1
    agent_input = agent_input_text(test_case)
    agent_output = agent_output_text(transcript)
    results = {check.name: check for check in layer_1.checks}
    records: list[ModelCheckRecord] = []
    for check in pending:
        prompt = rubric.build_prompt(check, agent_input, agent_output)
        try:
            response = model_judge.ask(
                ModelRequest(model=settings.model, prompt=prompt, timeout_s=settings.timeout_s)
            )
        except Exception as exc:  # a failing judge adapter is a model failure, never a pass
            response = ModelResponse(error=f"{type(exc).__name__}: {exc}")
        passed, answer, rationale = interpret_answer(check, response, settings.model)
        records.append(
            ModelCheckRecord(
                name=check.name,
                criterion=check.criterion,
                expected=check.expected,
                pass_rule=check.pass_rule,
                prompt=prompt,
                raw_response=response.text,
                answer=answer,
                passed=passed,
                rationale=rationale,
            )
        )
        results[MODEL_CHECK_PREFIX + check.name] = CheckResult(
            MODEL_CHECK_PREFIX + check.name, passed, rationale
        )
    checks = list(results.values())
    verdict = _verdict_from(checks)
    names = ", ".join(record.name for record in records)
    if verdict is RunVerdict.FAIL:
        summary = f"fail: Layer 2 failed {', '.join(r.name for r in records if r.passed is False)}"
    elif verdict is RunVerdict.INCONCLUSIVE:
        summary = (
            f"inconclusive: Layer 2 could not decide "
            f"{', '.join(r.name for r in records if r.passed is None)}"
        )
    else:
        summary = f"pass: every Layer 1 check passed and Layer 2 passed {names}"
    return Judgement(
        verdict,
        JudgeLayer.MODEL,
        checks,
        summary,
        rationale="\n".join(f"{record.name}: {record.rationale}" for record in records),
        layer_2=Layer2Record(
            model=settings.model,
            rubric_version=settings.rubric_version,
            rubric_hash=rubric.rubric_hash(),
            checks=records,
        ),
    )


# -- the service -------------------------------------------------------------------------


class JudgeService:
    """Judges a transcript and writes the run to the Evidence store (schema §4, step 5).

    The stored evidence document holds the transcript and the judgement, with
    everything Layer 2 saw and said. Its hash is what the attestation signature
    covers (schema §11).
    """

    def __init__(
        self,
        store: EvidenceStore,
        transcripts: TranscriptStorage,
        clock: Clock,
        ids: IdGenerator,
        model_judge: ModelJudge | None = None,
        model_settings: ModelJudgeSettings | None = None,
    ) -> None:
        self._store = store
        self._transcripts = transcripts
        self._clock = clock
        self._ids = ids
        self._model_judge = model_judge
        self._model_settings = model_settings

    @property
    def layer_2_configured(self) -> bool:
        return self._model_judge is not None and self._model_settings is not None

    @staticmethod
    def transcript_key(attestation_id: UUID, test_case_id: UUID, attempt: int) -> str:
        return f"{attestation_id}/{test_case_id}-{attempt}.json"

    @staticmethod
    def evidence_document(transcript: Transcript, judgement: Judgement) -> JsonObject:
        return {
            "transcript": transcript.model_dump(mode="json"),
            "judgement": judgement.to_json(),
        }

    def judge(self, transcript: Transcript, test_case: TestCase) -> Judgement:
        """Layer 1, then Layer 2 for what Layer 1 could not decide, if a judge is configured."""
        criteria = parse_criteria(test_case.criteria)
        judgement = judge_run(transcript, criteria)
        if not undecided_model_checks(judgement, criteria):
            return judgement
        if self._model_judge is None or self._model_settings is None:
            return replace(
                judgement,
                summary=judgement.summary
                + "; no judge model is configured (judge_model), so Layer 2 did not run",
            )
        return judge_with_model(
            judgement, criteria, transcript, test_case, self._model_settings, self._model_judge
        )

    def record(self, transcript: Transcript, test_case: TestCase) -> tuple[Run, Judgement]:
        """Judge, store the evidence document, then record the run. Never updates a run."""
        judgement = self.judge(transcript, test_case)
        document = self.evidence_document(transcript, judgement)
        data = canonical_json(document)
        key = self.transcript_key(transcript.attestation_id, test_case.id, transcript.attempt)
        try:
            transcript_ref = self._transcripts.put(key, data)
        except TranscriptExistsError:
            # An earlier attempt under this run key stored its document but did not get to
            # record the run. The key keeps the result unique either way (DR-001).
            transcript_ref = key
        run = Run(
            id=self._ids.new_id(),
            attestation_id=transcript.attestation_id,
            test_case_id=test_case.id,
            attempt=transcript.attempt,
            verdict=judgement.verdict,
            judge_layer=judgement.judge_layer,
            rationale=judgement.rationale,
            latency_ms=transcript.latency_ms,
            cost=transcript.cost,
            transcript_ref=transcript_ref,
            started_at=transcript.started_at,
            finished_at=transcript.finished_at,
        )
        self._store.add_run(run)
        return run, judgement
