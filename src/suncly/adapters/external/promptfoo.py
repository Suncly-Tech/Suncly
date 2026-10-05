"""Promptfoo (``0.123.1``, MIT) as a test pack runner behind ``ExternalToolRunner``.

The pack is a Promptfoo configuration the customer approved alongside the
contract: prompts (the inputs sent to the sandbox), the provider (an HTTP
provider pointing at the agent's JSON-RPC endpoint) and assertions. Suncly
runs ``promptfoo eval`` with the pack, keeps ``results.json`` byte for byte
and normalizes every result row into one ``ExternalCheck``:

* ``passed`` is ``gradingResult.pass`` (``success`` when there is no grading
  result); a row with an ``error`` is undecided, never a pass;
* the category comes from the test's ``metadata.category`` when it is one of
  Suncly's, else ``security`` for red-team plugins and ``semantic`` otherwise;
* ``level`` records the plugin or the assertion types, for the reader.

Promptfoo's own model-graded assertions would call a model provider from the
tool process; the worker image does not hand the tool any model key, so a
pack must use deterministic assertions (``contains``, ``equals``, ``regex``,
``javascript``, ``is-json`` ...). Model-graded rows surface as errors, hence
undecided.
"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from suncly.adapters.external.process import ToolProcess
from suncly.domain.policy import TestCategory
from suncly.ports.external_tools import (
    ExternalArtifactData,
    ExternalCheck,
    ExternalToolResult,
    JsonObject,
)

PROMPTFOO_VERSION = "0.123.1"
ADAPTER_VERSION = "suncly-promptfoo-adapter/1"
TOOL = "promptfoo"
RESULTS_FILE = "promptfoo-results.json"
_RED_TEAM = re.compile(r"(redteam|injection|jailbreak|pii|harmful|hijack|overreliance|rbac)", re.I)
_CATEGORIES = {c.value: c for c in TestCategory}


def _dict(value: Any) -> JsonObject:
    return dict(value) if isinstance(value, dict) else {}


def _category_of(result: JsonObject) -> TestCategory:
    test_case = _dict(result.get("testCase"))
    metadata = _dict(test_case.get("metadata"))
    declared = str(metadata.get("category") or _dict(result.get("metadata")).get("category") or "")
    if declared in _CATEGORIES:
        return _CATEGORIES[declared]
    plugin = str(metadata.get("pluginId") or metadata.get("plugin") or "")
    if _RED_TEAM.search(plugin) or _RED_TEAM.search(json.dumps(metadata)[:2000]):
        return TestCategory.SECURITY
    return TestCategory.SEMANTIC


def _assertion_types(result: JsonObject) -> str:
    test_case = _dict(result.get("testCase"))
    raw = test_case.get("assert")
    asserts: list[Any] = list(raw) if isinstance(raw, list) else []
    types = sorted({str(a.get("type")) for a in asserts if isinstance(a, dict) and a.get("type")})
    return ",".join(types)


def normalize_promptfoo_results(document: JsonObject, target_url: str) -> ExternalToolResult:
    """Turn a ``promptfoo eval -o results.json`` document into normalized checks."""
    results_section = document.get("results")
    if not isinstance(results_section, dict) or not isinstance(
        results_section.get("results"), list
    ):
        return ExternalToolResult(
            tool=TOOL,
            tool_version=PROMPTFOO_VERSION,
            adapter_version=ADAPTER_VERSION,
            target_url=target_url,
            checks=[],
            failure="the results document has no results list",
        )
    version = results_section.get("version")
    checks: list[ExternalCheck] = []
    for index, row in enumerate(results_section["results"]):
        if not isinstance(row, dict):
            continue
        test_case = _dict(row.get("testCase"))
        description = str(row.get("description") or test_case.get("description") or "")
        check_id = str(row.get("id") or f"row-{index}")
        grading = row.get("gradingResult")
        # promptfoo 0.123: failureReason 0 none, 1 a failed assertion, 2 a provider/grader error.
        # A failed assertion also fills ``error`` with the reason, so ``error`` alone never
        # decides: a row with a grading result is judged by it; an error row without one, or
        # one marked as an error, is undecided.
        errored = row.get("failureReason") == 2 or (
            bool(row.get("error")) and not isinstance(grading, dict)
        )
        if errored:
            passed: bool | None = None
            detail = f"error: {str(row.get('error') or 'no grading result')[:500]}"
        elif isinstance(grading, dict) and isinstance(grading.get("pass"), bool):
            passed = bool(grading["pass"])
            detail = str(grading.get("reason") or "")[:500]
        elif isinstance(row.get("success"), bool):
            passed = bool(row["success"])
            detail = "success flag only; no grading result"
        else:
            passed = None
            detail = "no grading result and no success flag"
        metadata = _dict(test_case.get("metadata"))
        level = str(metadata.get("pluginId") or metadata.get("plugin") or _assertion_types(row))
        checks.append(
            ExternalCheck(
                id=check_id,
                category=_category_of(row),
                passed=passed,
                level=level,
                detail=(description + (": " if description and detail else "") + detail)[:1000],
            )
        )
    failure = None
    if version not in (2, 3):
        failure = f"unsupported promptfoo results version {version!r}"
    return ExternalToolResult(
        tool=TOOL,
        tool_version=PROMPTFOO_VERSION,
        adapter_version=ADAPTER_VERSION,
        target_url=target_url,
        checks=checks,
        failure=failure,
    )


class PromptfooRunner:
    """Runs one approved pack. ``command`` is injectable so tests use a stand-in binary."""

    tool = TOOL
    tool_version = PROMPTFOO_VERSION

    def __init__(
        self,
        process: ToolProcess,
        pack_path: Path,
        command: Sequence[str] | None = None,
        version_command: Sequence[str] | None = None,
    ) -> None:
        self._process = process
        self._pack = pack_path
        self._command = list(command) if command else ["promptfoo"]
        self._version_command = list(version_command) if version_command else None

    @staticmethod
    def _runtime(work_dir: Path) -> dict[str, str]:
        """promptfoo's own knobs: no telemetry, no update check, its state inside the work dir."""
        return {
            "HOME": str(work_dir),
            "PROMPTFOO_CONFIG_DIR": str(work_dir / ".promptfoo"),
            "PROMPTFOO_DISABLE_TELEMETRY": "1",
            "PROMPTFOO_DISABLE_UPDATE": "1",
            "PROMPTFOO_DISABLE_SHARE_WARNING": "1",
        }

    def _installed_version(self, work_dir: Path) -> str | None:
        command = self._version_command or [*self._command, "--version"]
        if shutil.which(command[0]) is None and not Path(command[0]).exists():
            return None
        result = self._process.run(command, work_dir, 60.0, self._runtime(work_dir))
        if not result.ran or result.returncode != 0:
            return None
        return result.stdout.decode("utf-8", "replace").strip().splitlines()[-1].strip()

    def run(self, target_url: str, work_dir: str, timeout_s: float) -> ExternalToolResult:
        folder = Path(work_dir)
        folder.mkdir(parents=True, exist_ok=True)
        installed = self._installed_version(folder)
        if installed is None:
            return self._failure(target_url, "promptfoo is not installed in the worker image")
        if installed != PROMPTFOO_VERSION:
            return self._failure(
                target_url,
                f"promptfoo {installed} is installed; the adapter is pinned to {PROMPTFOO_VERSION}",
            )
        if not self._pack.exists():
            return self._failure(target_url, f"the pack {self._pack} does not exist")
        output = folder / RESULTS_FILE
        command = [
            *self._command,
            "eval",
            "--config",
            str(self._pack),
            "--output",
            str(output),
            "--no-cache",
            "--no-progress-bar",
            "--var",
            f"target_url={target_url}",
        ]
        result = self._process.run(command, folder, timeout_s, self._runtime(folder))
        artifacts: list[ExternalArtifactData] = []
        if result.stderr:
            artifacts.append(
                ExternalArtifactData(
                    kind="stderr", filename="promptfoo.stderr.txt", content=result.stderr
                )
            )
        if result.timed_out:
            return self._failure(
                target_url, f"promptfoo did not finish within {timeout_s:.0f}s", artifacts
            )
        if not result.ran:
            return self._failure(
                target_url, f"promptfoo could not start: {result.failed_to_start}", artifacts
            )
        if not output.exists():
            return self._failure(
                target_url,
                f"promptfoo exited with {result.returncode} and wrote no results",
                artifacts,
            )
        raw = output.read_bytes()
        artifacts.insert(
            0, ExternalArtifactData(kind="results", filename=RESULTS_FILE, content=raw)
        )
        try:
            document: Any = json.loads(raw)
        except ValueError:
            return self._failure(target_url, "the results file is not JSON", artifacts)
        normalized = normalize_promptfoo_results(
            document if isinstance(document, dict) else {}, target_url
        )
        return normalized.model_copy(update={"artifacts": artifacts})

    @staticmethod
    def _failure(
        target_url: str, why: str, artifacts: list[ExternalArtifactData] | None = None
    ) -> ExternalToolResult:
        return ExternalToolResult(
            tool=TOOL,
            tool_version=PROMPTFOO_VERSION,
            adapter_version=ADAPTER_VERSION,
            target_url=target_url,
            checks=[],
            artifacts=artifacts or [],
            failure=why,
        )
