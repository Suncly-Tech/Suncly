"""Judge calibration against the human-labelled dataset (OQ-J: false approvals, false rejections).

The offline fake provider must reproduce every label, twice, so the dataset
itself is validated and CI needs no model. The same file measures a real
provider through ``calibrate_judge``; that run is reported, never asserted.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from suncly.adapters.fake_model import HeuristicJudgeClient
from suncly.core.judge import JudgeService
from suncly.core.model_calibration import calibrate_judge, load_calibration
from suncly.core.model_judge import ModelJudge
from suncly.domain.criteria import Criteria
from suncly.domain.models import RunVerdict, TestCase, TestCaseKind
from suncly.domain.transcript import RunOutcome
from suncly.ports.model import ModelConfig, ModelUsage, StructuredRequest, StructuredResponse
from tests.fakes import make_transcript, task_response

DATASET = Path(__file__).resolve().parents[1] / "calibration" / "judge_calibration.json"


def test_the_dataset_is_well_formed_and_covers_every_verdict_and_category() -> None:
    dataset = load_calibration(DATASET)
    assert dataset.format == "suncly-judge-calibration/1" and len(dataset.items) >= 10
    assert {item.label for item in dataset.items} == {
        RunVerdict.PASS,
        RunVerdict.FAIL,
        RunVerdict.INCONCLUSIVE,
    }
    assert {item.category for item in dataset.items} >= {"semantic", "security", "operational"}
    assert len({item.id for item in dataset.items}) == len(dataset.items)
    for item in dataset.items:
        Criteria.model_validate(item.criteria)


def test_the_offline_judge_reproduces_every_human_label_consistently() -> None:
    report = calibrate_judge(
        DATASET,
        lambda: ModelJudge(
            HeuristicJudgeClient(), ModelConfig(provider="fake", model="fake-model/1")
        ),
        repeats=2,
    )
    assert report.false_approvals == [] and report.false_rejections == [], report.to_json()
    assert report.inconsistent == [] and report.agreement == 1.0
    assert report.total == 12 and report.repeats == 2
    summary = report.to_json()
    assert summary["false_approval_rate"] == 0.0 and summary["false_rejection_rate"] == 0.0
    assert summary["judge"]["model"] == "fake-heuristic-judge/1", "the model that answered"


def test_a_lenient_judge_is_caught_as_false_approvals() -> None:
    """A judge that passes everything it can read must show up as false approvals, never hide."""

    class YesMan:
        name = "yes"

        def complete(self, request: StructuredRequest) -> StructuredResponse:
            user = request.user
            ids = [
                line.partition(": ")[0]
                for line in user.split("<<<STATEMENTS>>>")[-1].splitlines()
                if ": " in line
            ]
            parsed = {
                "statements": [{"id": i, "verdict": "pass", "rationale": "sure"} for i in ids],
                "overall_rationale": "sure",
            }
            return StructuredResponse(
                parsed=parsed,
                raw_text=json.dumps(parsed),
                model="yes/1",
                usage=ModelUsage(input_tokens=1, output_tokens=1),
                latency_ms=1,
            )

    report = calibrate_judge(
        DATASET,
        lambda: ModelJudge(YesMan(), ModelConfig(provider="fake", model="yes/1")),
        repeats=1,
    )
    assert {item for item, _ in report.false_approvals} >= {
        "capital-berlin-fail",
        "refund-policy-half-right-fail",
        "order-cancel-wrong-order-fail",
    }
    assert "prompt-leak-negative-fail" not in {item for item, _ in report.false_approvals}, (
        "the deterministic assertion fails before Layer 2 is asked"
    )
    assert report.agreement < 1.0


def test_the_judge_service_itself_agrees_with_the_dataset_through_layer_one_and_two(
    tmp_path: Path,
) -> None:
    from suncly.adapters.file_store import FileEvidenceStore
    from suncly.adapters.local_transcripts import LocalTranscriptStorage
    from tests.fakes import FakeClock, SeqIds

    dataset = load_calibration(DATASET)
    service = JudgeService(
        FileEvidenceStore(tmp_path / "store"),
        LocalTranscriptStorage(tmp_path / "transcripts"),
        FakeClock(),
        SeqIds(),
        model_judge=ModelJudge(
            HeuristicJudgeClient(), ModelConfig(provider="fake", model="fake-model/1")
        ),
    )
    for item in dataset.items:
        criteria = Criteria.model_validate(item.criteria)
        test_case = TestCase(
            id=uuid4(),
            contract_id=uuid4(),
            skill_id="s",
            input={"text": "q"},
            criteria=criteria.to_document(),
            kind=TestCaseKind.SKILL,
        )
        if item.response_text is None:
            transcript = make_transcript(
                final_response=None,
                outcome=RunOutcome.TIMEOUT,
                failure="timeout",
            )
        else:
            transcript = make_transcript(final_response=task_response(text=item.response_text))
        judgement = service.judge(transcript, criteria, test_case)
        assert judgement.verdict is item.label, (item.id, judgement.summary)
