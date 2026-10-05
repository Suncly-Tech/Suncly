"""Offline model providers for CI and local development. No network, no cost.

``ScriptedModelClient`` answers from a list of prepared responses, so tests
can drive every path of the judge and the drafter: valid answers, refusals,
timeouts, malformed output, unavailable providers.

``HeuristicJudgeClient`` is a deterministic stand-in that judges rubric
statements by keyword overlap. It exists so the hosted workflow can be
exercised end to end without a paid provider; its verdicts are labelled with
provider ``fake`` and are never mistaken for a real model's.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable

import jsonschema

from suncly.domain.models import JsonObject
from suncly.ports.model import (
    ModelFailureKind,
    ModelUsage,
    StructuredRequest,
    StructuredResponse,
)

ScriptEntry = JsonObject | ModelFailureKind | Callable[[StructuredRequest], StructuredResponse]


class ScriptedModelClient:
    name = "fake"

    def __init__(self, script: Iterable[ScriptEntry], model: str = "fake-model/1") -> None:
        self._script = list(script)
        self._model = model
        self.requests: list[StructuredRequest] = []

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        self.requests.append(request)
        if not self._script:
            return StructuredResponse(
                failure=ModelFailureKind.UNAVAILABLE,
                failure_detail="the scripted client has no answer left",
                model=self._model,
            )
        entry = self._script.pop(0)
        if callable(entry):
            return entry(request)
        if isinstance(entry, ModelFailureKind):
            return StructuredResponse(
                failure=entry, failure_detail=f"scripted {entry.value}", model=self._model
            )
        try:
            jsonschema.validate(entry, request.schema_)
        except jsonschema.ValidationError as exc:
            return StructuredResponse(
                raw_text=json.dumps(entry),
                failure=ModelFailureKind.MALFORMED,
                failure_detail=exc.message,
                model=self._model,
            )
        return StructuredResponse(
            parsed=entry,
            raw_text=json.dumps(entry),
            model=self._model,
            usage=ModelUsage(
                input_tokens=len(request.user) // 4, output_tokens=len(json.dumps(entry)) // 4
            ),
            latency_ms=1,
        )


_BLOCK = re.compile(r"<<<AGENT RESPONSE TEXT>>>\n(.*?)\n<<<END AGENT RESPONSE TEXT>>>", re.S)
_STATEMENTS = re.compile(r"<<<RUBRIC STATEMENTS>>>\n(.*?)\n<<<END RUBRIC STATEMENTS>>>", re.S)


class HeuristicJudgeClient:
    """Judges a statement ``pass`` when its quoted words appear in the response text.

    A statement like ``the answer names "Paris"`` passes when ``paris`` occurs in
    the response; a statement with no quoted words is ``cannot_decide``.
    Deterministic, offline, and obviously not a model.
    """

    name = "fake"

    def __init__(self) -> None:
        self.requests: list[StructuredRequest] = []

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        self.requests.append(request)
        if request.purpose != "judge":
            return StructuredResponse(
                failure=ModelFailureKind.MISCONFIGURED,
                failure_detail="the heuristic client only judges",
                model="fake-heuristic-judge/1",
            )
        text_match = _BLOCK.search(request.user)
        statements_match = _STATEMENTS.search(request.user)
        text = (text_match.group(1) if text_match else "").lower()
        statements: list[JsonObject] = []
        for line in (statements_match.group(1) if statements_match else "").splitlines():
            statement_id, _, statement = line.partition(": ")
            quoted = re.findall(r'"([^"]+)"', statement)
            if not quoted:
                verdict, rationale = "cannot_decide", "the statement quotes nothing to look for"
            elif all(word.lower() in text for word in quoted):
                verdict, rationale = "pass", f"found {quoted} in the response"
            else:
                verdict, rationale = "fail", f"did not find all of {quoted} in the response"
            statements.append({"id": statement_id, "verdict": verdict, "rationale": rationale})
        parsed: JsonObject = {
            "statements": statements,
            "overall_rationale": "heuristic keyword judgement (offline fake provider)",
        }
        return StructuredResponse(
            parsed=parsed,
            raw_text=json.dumps(parsed),
            model="fake-heuristic-judge/1",
            usage=ModelUsage(input_tokens=len(request.user) // 4, output_tokens=64),
            latency_ms=1,
        )
