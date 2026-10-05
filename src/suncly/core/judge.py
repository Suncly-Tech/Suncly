"""The Judge (schema §2): Layer 1 deterministic checks, Layer 2 through the model port.

Layer 1 checks valid schema, final task state, required fields, the latency
limit, the card's declared output modes and, for format 2 criteria, the
deterministic assertions, negative cases and the sandbox-state verification
the Runner performed. The verdict is ``pass``, ``fail`` or ``inconclusive``;
``inconclusive`` is never counted as a pass.

Layer 2 runs only for criteria Layer 1 cannot decide (a rubric, or the legacy
``model_checks``), and only when Layer 1 did not already fail. It uses a
pinned model and a versioned rubric through ``ports/model.py``; its rationale,
model identity, parameters and usage are stored with the evidence. Any
failure of the model path is ``inconclusive`` with ``judge_layer`` ``model``
and a rationale saying why (OQ-D4).

Every check carries the category it evidences (protocol, semantic, security,
operational), so the Policy engine can require coverage per category.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

import jsonschema

from suncly.domain import a2a
from suncly.domain.canonical import canonical_json
from suncly.domain.criteria import Criteria, parse_criteria
from suncly.domain.errors import TranscriptExistsError
from suncly.domain.models import JsonObject, JudgeLayer, Run, RunVerdict, TestCase
from suncly.domain.policy import TestCategory
from suncly.domain.transcript import RunOutcome, Transcript
from suncly.ports.clock import Clock, IdGenerator
from suncly.ports.model import ModelFailureKind
from suncly.ports.store import EvidenceStore
from suncly.ports.transcripts import TranscriptStorage

#: The Judge's own version, bound into signed payloads. Change it when a check changes.
JUDGE_VERSION = "suncly-judge/2"

PROTOCOL = TestCategory.PROTOCOL.value
SEMANTIC = TestCategory.SEMANTIC.value
SECURITY = TestCategory.SECURITY.value
OPERATIONAL = TestCategory.OPERATIONAL.value


@dataclass(frozen=True)
class CheckResult:
    """One check. ``passed`` is ``None`` when it could not be decided."""

    name: str
    passed: bool | None
    detail: str
    category: str = SEMANTIC

    def to_json(self) -> JsonObject:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "category": self.category,
        }


@dataclass(frozen=True)
class ModelJudgement:
    """What Layer 2 produced, or why it could not."""

    verdict: RunVerdict
    rationale: str
    model: str
    parameters: JsonObject
    usage: JsonObject
    statements: list[JsonObject] = field(default_factory=list)
    failure: ModelFailureKind | None = None
    rubric_id: str | None = None
    rubric_version: str | None = None
    prompt_version: str = ""

    def to_json(self) -> JsonObject:
        return {
            "verdict": self.verdict.value,
            "rationale": self.rationale,
            "model": self.model,
            "parameters": self.parameters,
            "usage": self.usage,
            "statements": self.statements,
            "failure": self.failure.value if self.failure else None,
            "rubric_id": self.rubric_id,
            "rubric_version": self.rubric_version,
            "prompt_version": self.prompt_version,
        }


@dataclass(frozen=True)
class Judgement:
    verdict: RunVerdict
    judge_layer: JudgeLayer
    checks: list[CheckResult] = field(default_factory=list)
    summary: str = ""
    model: ModelJudgement | None = None
    category: str = SEMANTIC

    def to_json(self) -> JsonObject:
        return {
            "verdict": self.verdict.value,
            "judge_layer": self.judge_layer.value,
            "summary": self.summary,
            "category": self.category,
            "judge_version": JUDGE_VERSION,
            "checks": [check.to_json() for check in self.checks],
            "model": self.model.to_json() if self.model else None,
        }

    @property
    def rationale(self) -> str | None:
        return self.model.rationale if self.model else None


def _verdict_from(checks: Sequence[CheckResult]) -> RunVerdict:
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


def response_text(response: JsonObject, is_task: bool) -> str:
    """Every text part of the agent's output, joined. What assertions and the judge read."""
    parts = a2a.output_parts(response, is_task)
    texts = [str(part["text"]) for part in parts if isinstance(part.get("text"), str)]
    if is_task:
        status = response.get("status")
        message = status.get("message") if isinstance(status, dict) else None
        if isinstance(message, dict):
            texts.extend(
                str(part["text"])
                for part in message.get("parts") or []
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            )
    return "\n".join(texts)


def evaluate_assertion(
    assertion: JsonObject, response: JsonObject, text: str, is_task: bool
) -> CheckResult:
    """One deterministic assertion of a format 2 case. Never calls a model."""
    kind = str(assertion.get("kind"))
    value = assertion.get("value")
    name = f"assertion {kind}" + (
        f" ({assertion['description']})" if assertion.get("description") else ""
    )
    sensitive = bool(assertion.get("case_sensitive"))
    haystack = text if sensitive else text.lower()
    needle = str(value) if sensitive else str(value).lower()
    if kind == "text_equals":
        return CheckResult(name, haystack.strip() == needle.strip(), f"expected {value!r}")
    if kind == "text_contains":
        return CheckResult(name, needle in haystack, f"expected the text to contain {value!r}")
    if kind == "text_not_contains":
        return CheckResult(
            name, needle not in haystack, f"expected the text not to contain {value!r}", SECURITY
        )
    if kind == "text_regex":
        try:
            matched = re.search(str(value), text, 0 if sensitive else re.IGNORECASE) is not None
        except re.error as exc:
            return CheckResult(name, None, f"invalid regular expression: {exc}")
        return CheckResult(name, matched, f"pattern {value!r}")
    if kind in ("json_pointer_equals", "json_pointer_present"):
        pointer = str(assertion.get("pointer"))
        try:
            observed = resolve_pointer(response, pointer)
        except KeyError:
            return CheckResult(name, False, f"{pointer} is missing")
        if kind == "json_pointer_present":
            return CheckResult(name, not _is_empty(observed), f"{pointer} present")
        return CheckResult(
            name, observed == value, f"{pointer}: expected {value!r}, observed {observed!r}"
        )
    if kind == "response_schema":
        if not isinstance(value, dict):
            return CheckResult(name, None, "no schema")
        validator_cls = jsonschema.validators.validator_for(value)
        errors = sorted(validator_cls(value).iter_errors(response), key=lambda e: e.path)
        return CheckResult(
            name,
            not errors,
            "; ".join(error.message for error in errors[:5]) if errors else "conforms",
            PROTOCOL,
        )
    if kind == "final_state":
        state = a2a.task_state(response) if is_task else None
        return CheckResult(name, state == value, f"expected {value}, observed {state}", PROTOCOL)
    if kind == "output_mode":
        parts = a2a.output_parts(response, is_task)
        media = [a2a.part_media_type(part) for part in parts]
        return CheckResult(
            name, bool(parts) and all(m == value for m in media), f"observed {media}", PROTOCOL
        )
    return CheckResult(name, None, f"unknown assertion kind {kind!r}")


def _sandbox_check(transcript: Transcript, criteria: Criteria) -> CheckResult | None:
    if criteria.sandbox_verification is None:
        return None
    observed = transcript.sandbox_verification
    if observed is None:
        return CheckResult(
            "sandbox_state", None, "the Runner performed no sandbox-state verification", SEMANTIC
        )
    ok = observed.get("ok")
    detail = (
        f"{observed.get('url')} {observed.get('pointer')}: expected {observed.get('expected')!r}, "
        f"observed {observed.get('observed')!r}"
    )
    if observed.get("error"):
        detail += f"; error: {observed['error']}"
    return CheckResult("sandbox_state", ok if isinstance(ok, bool) else None, detail, SEMANTIC)


def judge_run(transcript: Transcript | None, criteria: Criteria) -> Judgement:
    """Layer 1 verdict for one run. Pure: no I/O, no model."""
    layer = JudgeLayer.DETERMINISTIC
    category = criteria.category or SEMANTIC
    if transcript is None:
        return Judgement(
            RunVerdict.INCONCLUSIVE,
            layer,
            [
                CheckResult(
                    "transcript_readable", None, "Suncly could not read the transcript", PROTOCOL
                )
            ],
            "inconclusive: the transcript could not be read (Suncly's own fault, OQ-A11)",
            category=category,
        )
    if transcript.outcome is RunOutcome.UNREACHABLE:
        return Judgement(
            RunVerdict.INCONCLUSIVE,
            layer,
            [
                CheckResult(
                    "response_received", None, transcript.failure or "no connection", OPERATIONAL
                )
            ],
            "inconclusive: the agent was unreachable, so there is no response to judge",
            category=category,
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
                    OPERATIONAL,
                )
            ],
            "fail: the agent did not finish in time",
            category=category,
        )
    if transcript.outcome is RunOutcome.PROTOCOL_ERROR or transcript.final_response is None:
        return Judgement(
            RunVerdict.FAIL,
            layer,
            [
                CheckResult(
                    "valid_schema", False, transcript.failure or "no usable A2A response", PROTOCOL
                )
            ],
            "fail: the response is not a valid A2A response",
            category=category,
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
            PROTOCOL,
        )
    )

    if is_task:
        state = transcript.final_task_state
        checks.append(
            CheckResult(
                "final_task_state",
                state == criteria.final_state,
                f"expected {criteria.final_state}, observed {state}",
                PROTOCOL,
            )
        )
    else:
        checks.append(
            CheckResult(
                "final_task_state",
                criteria.accept_direct_message,
                "the agent answered with a direct Message instead of a Task"
                + ("; accepted by the criteria" if criteria.accept_direct_message else ""),
                PROTOCOL,
            )
        )

    latency = transcript.latency_ms
    checks.append(
        CheckResult(
            "latency_limit",
            latency is not None and latency <= criteria.latency_limit_ms,
            f"{latency} ms against a limit of {criteria.latency_limit_ms} ms",
            OPERATIONAL,
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
                PROTOCOL,
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
                PROTOCOL,
            )
        )

    for pointer in criteria.required_fields:
        try:
            value = resolve_pointer(response, pointer)
            present = not _is_empty(value)
            detail = "present" if present else "present but empty"
        except KeyError:
            present, detail = False, "missing"
        checks.append(CheckResult(f"required_field {pointer}", present, detail, SEMANTIC))

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
                PROTOCOL,
            )
        )

    text = response_text(response, is_task)
    for assertion in criteria.assertions:
        checks.append(evaluate_assertion(assertion, response, text, is_task))

    sandbox = _sandbox_check(transcript, criteria)
    if sandbox is not None:
        checks.append(sandbox)

    if criteria.negative and criteria.final_state == a2a.TASK_STATE_COMPLETED:
        # A negative case that still expects completion must assert the refusal in its text.
        checks.append(
            CheckResult(
                "negative_case_asserted",
                bool(criteria.assertions),
                "a negative case needs at least one assertion that shows the refusal",
                SECURITY,
            )
        )

    for name in criteria.model_checks:
        checks.append(
            CheckResult(f"model_check {name}", None, "needs Layer 2 (the model judge)", SEMANTIC)
        )
    if criteria.rubric is not None:
        checks.append(
            CheckResult(
                f"rubric {criteria.rubric.get('id')}",
                None,
                "needs Layer 2 (the model judge)",
                SEMANTIC,
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
    return Judgement(verdict, layer, checks, summary, category=category)


def apply_model_judgement(judgement: Judgement, model: ModelJudgement) -> Judgement:
    """Fold a Layer 2 result into the Layer 1 judgement. A model failure stays inconclusive."""
    checks = [
        check
        for check in judgement.checks
        if not (check.passed is None and check.name.startswith(("model_check", "rubric")))
    ]
    checks.append(
        CheckResult(
            "model_judge",
            True
            if model.verdict is RunVerdict.PASS
            else False
            if model.verdict is RunVerdict.FAIL
            else None,
            model.rationale[:500],
            SEMANTIC,
        )
    )
    verdict = _verdict_from(checks)
    if verdict is RunVerdict.FAIL:
        summary = f"fail: {', '.join(c.name for c in checks if c.passed is False)}"
    elif verdict is RunVerdict.INCONCLUSIVE:
        summary = f"inconclusive: {model.rationale[:160]}"
    else:
        summary = "pass: every Layer 1 check passed and the model judge agreed"
    return Judgement(verdict, JudgeLayer.MODEL, checks, summary, model, judgement.category)


class ModelJudgePort(Protocol):
    """What ``JudgeService`` needs from Layer 2; ``core/model_judge.py`` implements it."""

    def judge(
        self, transcript: Transcript, criteria: Criteria, test_case: TestCase
    ) -> ModelJudgement: ...


class JudgeService:
    """Judges a transcript and writes the run to the Evidence store (schema §4, step 5).

    The stored evidence document holds the transcript and the judgement. Its
    hash is what the attestation signature covers (schema §11).
    """

    def __init__(
        self,
        store: EvidenceStore,
        transcripts: TranscriptStorage,
        clock: Clock,
        ids: IdGenerator,
        model_judge: ModelJudgePort | None = None,
    ) -> None:
        self._store = store
        self._transcripts = transcripts
        self._clock = clock
        self._ids = ids
        self._model_judge = model_judge

    @staticmethod
    def transcript_key(attestation_id: UUID, test_case_id: UUID, attempt: int) -> str:
        return f"{attestation_id}/{test_case_id}-{attempt}.json"

    @staticmethod
    def evidence_document(transcript: Transcript, judgement: Judgement) -> JsonObject:
        return {
            "transcript": transcript.model_dump(mode="json"),
            "judgement": judgement.to_json(),
        }

    def judge(self, transcript: Transcript, criteria: Criteria, test_case: TestCase) -> Judgement:
        """Layer 1, then Layer 2 when the criteria need it and Layer 1 did not already fail."""
        judgement = judge_run(transcript, criteria)
        if not criteria.needs_model_judge or judgement.verdict is RunVerdict.FAIL:
            return judgement
        if self._model_judge is None:
            return judgement
        model = self._model_judge.judge(transcript, criteria, test_case)
        return apply_model_judgement(judgement, model)

    def record(self, transcript: Transcript, test_case: TestCase) -> tuple[Run, Judgement]:
        """Judge, store the evidence document, then record the run. Never updates a run."""
        criteria = parse_criteria(test_case.criteria)
        judgement = self.judge(transcript, criteria, test_case)
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
