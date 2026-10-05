"""Judge calibration against a human-labelled dataset (``tests/calibration/*.json``).

Every item is a transcript a reviewer labelled ``pass``, ``fail`` or
``inconclusive`` under approved criteria. ``calibrate_judge`` runs the same
Layer 1 + Layer 2 path the Evidence pipeline uses and reports, per item and
in aggregate, false approvals (the judge passed what a human failed), false
rejections (the judge failed what a human passed) and inconsistency (the same
item judged differently across repeats). Pure apart from the judge port.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from suncly.core.judge import ModelJudgePort, apply_model_judgement, judge_run
from suncly.domain.criteria import Criteria
from suncly.domain.errors import ConfigError
from suncly.domain.models import JsonObject, RunVerdict, TestCase, TestCaseKind
from suncly.domain.transcript import Exchange, RunOutcome, Transcript

CALIBRATION_FORMAT = "suncly-judge-calibration/1"


@dataclass(frozen=True)
class CalibrationItem:
    id: str
    category: str
    criteria: JsonObject
    response_text: str | None
    label: RunVerdict
    note: str = ""


@dataclass(frozen=True)
class CalibrationDataset:
    format: str
    description: str
    labelled_by: tuple[str, ...]
    labelled_on: str
    items: tuple[CalibrationItem, ...]


def load_calibration(path: Path) -> CalibrationDataset:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError("The calibration dataset cannot be read.", f"{exc}") from exc
    if not isinstance(raw, dict) or raw.get("format") != CALIBRATION_FORMAT:
        raise ConfigError(
            "The calibration dataset has an unknown format.",
            f"Expected format {CALIBRATION_FORMAT!r}.",
        )
    items: list[CalibrationItem] = []
    for entry in raw.get("items") or []:
        if not isinstance(entry, dict):
            raise ConfigError("Every calibration item must be an object.")
        try:
            Criteria.model_validate(entry["criteria"])
            items.append(
                CalibrationItem(
                    id=str(entry["id"]),
                    category=str(entry.get("category") or "semantic"),
                    criteria=dict(entry["criteria"]),
                    response_text=entry.get("response_text"),
                    label=RunVerdict(str(entry["label"])),
                    note=str(entry.get("note") or ""),
                )
            )
        except (KeyError, ValueError) as exc:
            raise ConfigError(
                "A calibration item is malformed.", f"item {entry.get('id')!r}: {exc}"
            ) from exc
    if len({item.id for item in items}) != len(items):
        raise ConfigError("Calibration item ids must be unique.")
    return CalibrationDataset(
        format=str(raw["format"]),
        description=str(raw.get("description") or ""),
        labelled_by=tuple(str(x) for x in raw.get("labelled_by") or []),
        labelled_on=str(raw.get("labelled_on") or ""),
        items=tuple(items),
    )


def transcript_for_text(text: str | None, now: datetime | None = None) -> Transcript:
    """A minimal A2A transcript carrying one text answer, or a timed-out run for ``None``."""
    started = now or datetime.now(UTC)
    finished = started + timedelta(milliseconds=50)
    if text is None:
        return Transcript(
            attestation_id=UUID(int=0),
            test_case_id=UUID(int=0),
            attempt=1,
            target_url="https://calibration.invalid/rpc",
            protocol_binding="JSONRPC",
            protocol_version="1.0",
            started_at=started,
            finished_at=finished,
            latency_ms=None,
            cost=Decimal(0),
            outcome=RunOutcome.TIMEOUT,
            failure="no response within the run timeout",
        )
    response: JsonObject = {
        "id": "task-calibration",
        "contextId": "ctx-calibration",
        "status": {"state": "TASK_STATE_COMPLETED", "timestamp": finished.isoformat()},
        "artifacts": [{"artifactId": "a-1", "parts": [{"text": text, "mediaType": "text/plain"}]}],
    }
    return Transcript(
        attestation_id=UUID(int=0),
        test_case_id=UUID(int=0),
        attempt=1,
        target_url="https://calibration.invalid/rpc",
        protocol_binding="JSONRPC",
        protocol_version="1.0",
        started_at=started,
        finished_at=finished,
        latency_ms=50,
        cost=Decimal(0),
        outcome=RunOutcome.RESPONDED_TASK,
        task_id="task-calibration",
        final_task_state="TASK_STATE_COMPLETED",
        final_response=response,
        exchanges=[
            Exchange(
                direction="request",
                at=started,
                method="SendMessage",
                url="https://calibration.invalid/rpc",
                body={},
            )
        ],
    )


@dataclass
class CalibrationReport:
    dataset: str
    total: int
    repeats: int
    judge: JsonObject
    verdicts: dict[str, list[RunVerdict]] = field(default_factory=dict)
    labels: dict[str, RunVerdict] = field(default_factory=dict)
    false_approvals: list[tuple[str, RunVerdict]] = field(default_factory=list)
    false_rejections: list[tuple[str, RunVerdict]] = field(default_factory=list)
    undecided: list[str] = field(default_factory=list)
    inconsistent: list[str] = field(default_factory=list)

    @property
    def agreement(self) -> float:
        judged = sum(len(v) for v in self.verdicts.values())
        if not judged:
            return 0.0
        agreed = sum(
            1
            for item_id, verdicts in self.verdicts.items()
            for verdict in verdicts
            if verdict is self.labels[item_id]
        )
        return agreed / judged

    def to_json(self) -> JsonObject:
        decided = [i for i, label in self.labels.items() if label is not RunVerdict.INCONCLUSIVE]
        return {
            "dataset": self.dataset,
            "total": self.total,
            "repeats": self.repeats,
            "judge": self.judge,
            "agreement": round(self.agreement, 4),
            "false_approval_rate": round(len(self.false_approvals) / max(len(decided), 1), 4),
            "false_rejection_rate": round(len(self.false_rejections) / max(len(decided), 1), 4),
            "false_approvals": [[i, v.value] for i, v in self.false_approvals],
            "false_rejections": [[i, v.value] for i, v in self.false_rejections],
            "undecided": list(self.undecided),
            "inconsistent": list(self.inconsistent),
            "verdicts": {
                i: [v.value for v in verdicts] for i, verdicts in sorted(self.verdicts.items())
            },
        }


def judge_item(item: CalibrationItem, judge: ModelJudgePort) -> tuple[RunVerdict, JsonObject]:
    """Layer 1, then Layer 2 when the criteria need it and Layer 1 did not already fail."""
    criteria = Criteria.model_validate(item.criteria)
    transcript = transcript_for_text(item.response_text)
    judgement = judge_run(transcript, criteria)
    model_info: JsonObject = {}
    if criteria.needs_model_judge and judgement.verdict is not RunVerdict.FAIL:
        model_judgement = judge.judge(
            transcript,
            criteria,
            TestCase(
                id=uuid4(),
                contract_id=uuid4(),
                skill_id="calibration",
                input={"text": "calibration"},
                criteria=criteria.to_document(),
                kind=TestCaseKind.SKILL,
            ),
        )
        judgement = apply_model_judgement(judgement, model_judgement)
        model_info = {"model": model_judgement.model, "parameters": model_judgement.parameters}
    return judgement.verdict, model_info


def calibrate_judge(
    path: Path, judge_factory: Callable[[], ModelJudgePort], repeats: int = 1
) -> CalibrationReport:
    dataset = load_calibration(path)
    report = CalibrationReport(
        dataset=str(path), total=len(dataset.items), repeats=max(repeats, 1), judge={}
    )
    for item in dataset.items:
        report.labels[item.id] = item.label
        verdicts: list[RunVerdict] = []
        for _ in range(report.repeats):
            verdict, info = judge_item(item, judge_factory())
            verdicts.append(verdict)
            if info and not report.judge:
                report.judge = info
        report.verdicts[item.id] = verdicts
        for verdict in verdicts:
            if verdict is RunVerdict.PASS and item.label is not RunVerdict.PASS:
                report.false_approvals.append((item.id, verdict))
            elif verdict is RunVerdict.FAIL and item.label is RunVerdict.PASS:
                report.false_rejections.append((item.id, verdict))
            elif verdict is RunVerdict.INCONCLUSIVE and item.label is not RunVerdict.INCONCLUSIVE:
                report.undecided.append(item.id)
        if len(set(verdicts)) > 1:
            report.inconsistent.append(item.id)
    return report


def summarize_for_humans(report: CalibrationReport) -> list[str]:
    summary = report.to_json()
    judge = report.judge or "n/a"
    lines = [
        f"{report.total} labelled item(s), {report.repeats} repeat(s), judge {judge}",
        (
            f"agreement {summary['agreement']:.0%}; false approvals "
            f"{len(report.false_approvals)}, false rejections {len(report.false_rejections)}, "
            f"undecided {len(report.undecided)}, inconsistent {len(report.inconsistent)}"
        ),
    ]
    for item_id, verdict in report.false_approvals:
        lines.append(f"  false approval: {item_id} judged {verdict.value}")
    for item_id, verdict in report.false_rejections:
        lines.append(f"  false rejection: {item_id} judged {verdict.value}")
    for item_id in report.inconsistent:
        lines.append(f"  inconsistent: {item_id} -> {[v.value for v in report.verdicts[item_id]]}")
    return lines
