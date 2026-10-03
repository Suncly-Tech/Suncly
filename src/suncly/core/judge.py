"""The Judge, Layer 1 (schema §2): deterministic checks only.

Checks: valid schema, final task state, required fields and the latency limit,
plus the card's declared output modes. The verdict is ``pass``, ``fail`` or
``inconclusive``; ``inconclusive`` is never counted as a pass. A criterion
Layer 1 cannot decide (``model_checks``) gives ``inconclusive``, because Layer 2
does not exist yet (stage 4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import jsonschema

from suncly.domain import a2a
from suncly.domain.canonical import canonical_json
from suncly.domain.criteria import Criteria, parse_criteria
from suncly.domain.errors import StoreError
from suncly.domain.models import JsonObject, JudgeLayer, Run, RunVerdict, TestCase
from suncly.domain.transcript import RunOutcome, Transcript
from suncly.ports.clock import Clock, IdGenerator
from suncly.ports.store import EvidenceStore
from suncly.ports.transcripts import TranscriptStorage


@dataclass(frozen=True)
class CheckResult:
    """One Layer 1 check. ``passed`` is ``None`` when Layer 1 cannot decide it."""

    name: str
    passed: bool | None
    detail: str

    def to_json(self) -> JsonObject:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class Judgement:
    verdict: RunVerdict
    judge_layer: JudgeLayer
    checks: list[CheckResult] = field(default_factory=list)
    summary: str = ""

    def to_json(self) -> JsonObject:
        return {
            "verdict": self.verdict.value,
            "judge_layer": self.judge_layer.value,
            "summary": self.summary,
            "checks": [check.to_json() for check in self.checks],
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

    for name in criteria.model_checks:
        checks.append(
            CheckResult(f"model_check {name}", None, "needs Layer 2, which arrives in stage 4")
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
    ) -> None:
        self._store = store
        self._transcripts = transcripts
        self._clock = clock
        self._ids = ids

    @staticmethod
    def transcript_key(attestation_id: UUID, test_case_id: UUID, attempt: int) -> str:
        return f"{attestation_id}/{test_case_id}-{attempt}.json"

    @staticmethod
    def evidence_document(transcript: Transcript, judgement: Judgement) -> JsonObject:
        return {
            "transcript": transcript.model_dump(mode="json"),
            "judgement": judgement.to_json(),
        }

    def record(self, transcript: Transcript, test_case: TestCase) -> tuple[Run, Judgement]:
        """Judge, store the evidence document, then record the run. Never updates a run."""
        criteria = parse_criteria(test_case.criteria)
        judgement = judge_run(transcript, criteria)
        document = self.evidence_document(transcript, judgement)
        data = canonical_json(document)
        key = self.transcript_key(transcript.attestation_id, test_case.id, transcript.attempt)
        try:
            transcript_ref = self._transcripts.put(key, data)
        except StoreError:
            # The document for this run key was written by an earlier attempt that then
            # failed to record its run; the run key keeps the result unique (DR-001).
            transcript_ref = key
        run = Run(
            id=self._ids.new_id(),
            attestation_id=transcript.attestation_id,
            test_case_id=test_case.id,
            attempt=transcript.attempt,
            verdict=judgement.verdict,
            judge_layer=judgement.judge_layer,
            rationale=None,
            latency_ms=transcript.latency_ms,
            cost=transcript.cost,
            transcript_ref=transcript_ref,
            started_at=transcript.started_at,
            finished_at=transcript.finished_at,
        )
        self._store.add_run(run)
        return run, judgement
