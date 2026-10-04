"""The defaults of ``make-sample.py``'s ``main()`` are what ``frontend/lib/sample`` encodes.

The committed sample bundles were generated with the defaults. If a default
changed, the next regeneration would disagree with the committed data and with
the script's own docstring, so this ties the two together without running the
pipeline.
"""

from __future__ import annotations

import inspect
import json
from decimal import Decimal
from typing import Any

from tests.frontend_scripts import REPO_ROOT, load_make_sample

make_sample = load_make_sample()
SAMPLE_DIR = REPO_ROOT / "frontend" / "lib" / "sample"
DEFAULTS: dict[str, Any] = {
    name: parameter.default
    for name, parameter in inspect.signature(make_sample.main).parameters.items()
}


def result_of(label: str) -> dict[str, Any]:
    bundle = json.loads((SAMPLE_DIR / f"harbor-{label}.json").read_text(encoding="utf-8"))
    assert bundle["sample"]["label"] == label
    assert bundle["sample"]["generated_by"] == "frontend/scripts/make-sample.py"
    return dict(bundle["result"])


def test_main_writes_to_the_committed_sample_folder_by_default() -> None:
    assert DEFAULTS["out_dir"] == make_sample.OUT_DIR == SAMPLE_DIR
    assert DEFAULTS["home"] is None
    assert DEFAULTS["pause_s"] == 1.5


def test_default_runs_and_budget_match_the_committed_bundles() -> None:
    contract = json.loads((SAMPLE_DIR / "harbor-contract.json").read_text(encoding="utf-8"))
    assert DEFAULTS["runs"] == 5
    planned = len(contract["test_cases"]) * DEFAULTS["runs"]
    for label in ("1-baseline", "2-regression"):
        result = result_of(label)
        assert result["planned_runs"] == planned, label
        assert len(result["runs"]) == planned, label
        assert result["attestation"]["status"] == "completed", label

    budget_stop = result_of("3-budget-stop")
    assert DEFAULTS["budget_stop"] == Decimal(7)
    assert Decimal(str(budget_stop["attestation"]["budget_limit"])) == DEFAULTS["budget_stop"]
    assert budget_stop["attestation"]["status"] == "failed"
    assert len(budget_stop["runs"]) == int(DEFAULTS["budget_stop"])
    assert len(budget_stop["not_executed"]) == planned - int(DEFAULTS["budget_stop"])
