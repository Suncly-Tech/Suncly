"""End to end: the website's sample data generator runs through the real code path.

``frontend/scripts/make-sample.py`` is the only producer of ``frontend/lib/sample``.
This test runs its ``main()`` into a temporary folder with three repetitions per
test case instead of five, and checks what the website relies on: three bundles
whose results verify, transcripts without the fake credential, and the three
stories ending as the script's docstring says: the baseline completed with a
flag, the regression completed with a flag, the budget stop failed with no
decision.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from suncly.core.verify import verify_result
from suncly.runner.credentials import CREDENTIAL_ENV_VAR
from tests.frontend_scripts import load_make_sample

pytestmark = pytest.mark.e2e

RUNS = 3
BUDGET_STOP = Decimal(5)
TEST_CASES = 4  # two order-status examples, one start-return, one refund-estimate
LABELS = ("1-baseline", "2-regression", "3-budget-stop")


def counts_by_skill(result: dict[str, Any]) -> dict[str, tuple[int, int, int]]:
    """``skill_id -> (pass, fail, inconclusive)``, summed over the skill's test cases."""
    totals: dict[str, list[int]] = {}
    for entry in result["results"]:
        row = totals.setdefault(entry["skill_id"], [0, 0, 0])
        row[0] += entry["pass_count"]
        row[1] += entry["fail_count"]
        row[2] += entry["inconclusive_count"]
    return {skill: (row[0], row[1], row[2]) for skill, row in totals.items()}


def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the script on the file store with default settings, whatever the shell holds.

    The script sets the fake credential itself; registering the variable with
    monkeypatch restores the environment afterwards.
    """
    monkeypatch.setenv(CREDENTIAL_ENV_VAR, "")
    for name in [key for key in os.environ if key.startswith("SUNCLY_") or key == "DATABASE_URL"]:
        monkeypatch.delenv(name)


def test_make_sample_writes_three_bundles_that_verify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_sample = load_make_sample()
    isolate_environment(monkeypatch)
    out_dir = tmp_path / "sample"

    code = make_sample.main(
        out_dir, home=tmp_path / "home", runs=RUNS, budget_stop=BUDGET_STOP, pause_s=0
    )

    assert code == 0
    assert sorted(path.name for path in out_dir.iterdir()) == [
        "harbor-1-baseline.json",
        "harbor-2-regression.json",
        "harbor-3-budget-stop.json",
        "harbor-contract.json",
    ]
    contract = json.loads((out_dir / "harbor-contract.json").read_text(encoding="utf-8"))
    assert contract["skills_without_test_case"] == ["cancel-order"]
    assert len(contract["test_cases"]) == TEST_CASES
    assert sorted({tc["skill_id"] for tc in contract["test_cases"]}) == [
        "order-status",
        "refund-estimate",
        "start-return",
    ]
    assert all(
        tc["criteria"]["required_fields"] == ["/artifacts/0/parts/0/text"]
        for tc in contract["test_cases"]
    )

    bundles = {
        label: json.loads((out_dir / f"harbor-{label}.json").read_text(encoding="utf-8"))
        for label in LABELS
    }
    secret = make_sample.FAKE_CREDENTIAL.split()[1]
    for label, bundle in bundles.items():
        assert bundle["sample"]["label"] == label
        assert bundle["sample"]["generated_by"] == "frontend/scripts/make-sample.py"
        transcripts = {stem: text.encode("utf-8") for stem, text in bundle["transcripts"].items()}
        assert verify_result(bundle["result"], transcripts).ok, label
        assert len(transcripts) == len(bundle["result"]["runs"]), label
        assert "## What was NOT tested" in bundle["report_md"]
        assert secret not in json.dumps(bundle), label

    baseline = bundles["1-baseline"]["result"]
    assert baseline["attestation"]["status"] == "completed"
    assert [decision["outcome"] for decision in baseline["decisions"]] == ["flag"]
    assert counts_by_skill(baseline) == {
        "order-status": (2 * RUNS, 0, 0),
        "start-return": (RUNS, 0, 0),
        "refund-estimate": (0, 0, RUNS),  # a model check: Layer 1 cannot decide it
    }

    regression = bundles["2-regression"]["result"]
    assert regression["attestation"]["status"] == "completed"
    assert [decision["outcome"] for decision in regression["decisions"]] == ["flag"]
    assert regression["card_version"]["card_hash"] == baseline["card_version"]["card_hash"]
    # Every third "shipped" query fails. The agent counts across both attestations, so
    # the regression sees calls RUNS + 1 to 2 * RUNS of that input.
    shipped_failures = sum(1 for call in range(RUNS + 1, 2 * RUNS + 1) if call % 3 == 0)
    assert shipped_failures >= 1
    assert counts_by_skill(regression) == {
        "order-status": (2 * RUNS - shipped_failures, shipped_failures, 0),
        "start-return": (0, RUNS, 0),  # stops at TASK_STATE_INPUT_REQUIRED
        "refund-estimate": (0, 0, RUNS),
    }

    budget_stop = bundles["3-budget-stop"]["result"]
    planned = TEST_CASES * RUNS
    never_executed = planned - int(BUDGET_STOP)
    assert budget_stop["attestation"]["status"] == "failed"
    assert budget_stop["decisions"] == []
    assert Decimal(str(budget_stop["attestation"]["cost_total"])) == BUDGET_STOP
    assert len(budget_stop["runs"]) == int(BUDGET_STOP)
    assert len(budget_stop["not_executed"]) == never_executed
    assert (
        f"{never_executed} run(s) of {planned} planned were never executed"
        in bundles["3-budget-stop"]["report_md"]
    )


def test_main_stops_with_exit_code_1_when_a_credential_leaks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The script's only failure path: a transcript that still holds the credential."""
    make_sample = load_make_sample()
    isolate_environment(monkeypatch)
    monkeypatch.setattr(make_sample, "credential_leaked", lambda _transcripts: True)
    out_dir = tmp_path / "sample"

    code = make_sample.main(
        out_dir, home=tmp_path / "home", runs=1, budget_stop=Decimal(2), pause_s=0
    )

    assert code == 1
    # It stops after the first bundle; the remaining two are never written.
    assert sorted(path.name for path in out_dir.iterdir()) == [
        "harbor-1-baseline.json",
        "harbor-contract.json",
    ]
