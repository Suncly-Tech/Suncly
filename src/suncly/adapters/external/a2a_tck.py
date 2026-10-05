"""The A2A Protocol TCK (``1.0.0.alpha2``, Apache-2.0) behind ``ExternalToolRunner``.

The TCK is a pytest suite the A2A project maintains. Suncly runs its entry
point against the sandbox's base URL and reads ``reports/compatibility.json``:
one entry per protocol requirement with its RFC 2119 level (MUST, SHOULD, MAY),
its status (PASS, FAIL, SKIPPED, NOT TESTED) and the per-transport results.
Every requirement becomes one ``ExternalCheck`` in the ``protocol`` category:

* PASS → passed; FAIL → failed;
* SKIPPED and NOT TESTED → undecided (``None``): a capability the agent does
  not declare, or a test that never ran, is never counted as a pass.

The TCK is installed from its pinned tag into the worker image; the adapter
reads the version from the checkout's ``pyproject.toml`` and refuses to run
any other.
"""

from __future__ import annotations

import json
import re
import sys
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

A2A_TCK_VERSION = "1.0.0.alpha2"
"""The git tag the adapter is written against."""
A2A_TCK_COMMIT = "29063fe95e903cddac5d8ff811ab94df1ad6ef86"
"""The commit that tag points at; the checkout must be exactly this."""
A2A_TCK_PYPROJECT_VERSION = "1.0.0"
"""What the tag's own pyproject.toml declares (the tag name is not in the file)."""
PIN_FILE = ".suncly-pin"
"""Written by the worker image next to the checkout after it removed ``.git``."""
A2A_TCK_SOURCE = "https://github.com/a2aproject/a2a-tck"
ADAPTER_VERSION = "suncly-a2a-tck-adapter/1"
TOOL = "a2a-tck"
REPORT_RELATIVE = Path("reports") / "compatibility.json"
_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.M)
_STATUS_TO_PASSED: dict[str, bool | None] = {
    "PASS": True,
    "FAIL": False,
    "SKIPPED": None,
    "NOT TESTED": None,
}


def normalize_tck_report(document: JsonObject, target_url: str) -> ExternalToolResult:
    """Turn ``compatibility.json`` into normalized checks, one per requirement."""
    requirements = document.get("per_requirement")
    if not isinstance(requirements, dict):
        return ExternalToolResult(
            tool=TOOL,
            tool_version=A2A_TCK_VERSION,
            adapter_version=ADAPTER_VERSION,
            target_url=target_url,
            checks=[],
            failure="the compatibility report has no per_requirement section",
        )
    checks: list[ExternalCheck] = []
    for requirement_id in sorted(requirements):
        entry = requirements[requirement_id]
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status") or "NOT TESTED").upper()
        passed = _STATUS_TO_PASSED.get(status)
        transports = entry.get("transports") if isinstance(entry.get("transports"), dict) else {}
        errors = entry.get("errors") if isinstance(entry.get("errors"), list) else []
        detail_parts = [f"status {status}"]
        if transports:
            detail_parts.append(
                "transports " + ", ".join(f"{k}={v}" for k, v in sorted(transports.items()))
            )
        if errors:
            detail_parts.append("first error: " + str(errors[0])[:300])
        checks.append(
            ExternalCheck(
                id=str(requirement_id),
                category=TestCategory.PROTOCOL,
                passed=passed,
                level=str(entry.get("level") or "").lower(),
                detail="; ".join(detail_parts)[:1000],
            )
        )
    return ExternalToolResult(
        tool=TOOL,
        tool_version=A2A_TCK_VERSION,
        adapter_version=ADAPTER_VERSION,
        target_url=target_url,
        checks=checks,
    )


def _base_url(target_url: str) -> str:
    """The TCK wants the host the card lives under, not the JSON-RPC path."""
    from urllib.parse import urlsplit

    parts = urlsplit(target_url)
    return f"{parts.scheme}://{parts.netloc}"


class A2ATckRunner:
    """Runs the pinned TCK checkout. ``command`` is injectable for tests."""

    tool = TOOL
    tool_version = A2A_TCK_VERSION

    def __init__(
        self,
        process: ToolProcess,
        checkout: Path,
        command: Sequence[str] | None = None,
        python: str | None = None,
    ) -> None:
        self._process = process
        self._checkout = checkout
        self._command = list(command) if command else [python or sys.executable, "run_tck.py"]

    def _checkout_version(self) -> str | None:
        pyproject = self._checkout / "pyproject.toml"
        if not pyproject.exists():
            return None
        match = _VERSION_RE.search(pyproject.read_text(encoding="utf-8", errors="replace"))
        return match.group(1) if match else None

    def _checkout_commit(self) -> str | None:
        """The commit of the checkout: from ``.git`` when present, else the image's pin file."""
        pin = self._checkout / PIN_FILE
        if pin.is_file():
            return pin.read_text(encoding="utf-8").strip() or None
        if (self._checkout / ".git").exists():
            result = self._process.run(
                ["git", "-C", str(self._checkout), "rev-parse", "HEAD"], self._checkout, 30.0
            )
            if result.ran and result.returncode == 0:
                return result.stdout.decode("utf-8", "replace").strip() or None
        return None

    def run(self, target_url: str, work_dir: str, timeout_s: float) -> ExternalToolResult:
        folder = Path(work_dir)
        folder.mkdir(parents=True, exist_ok=True)
        version = self._checkout_version()
        if version is None:
            return self._failure(target_url, f"no TCK checkout at {self._checkout}")
        if version != A2A_TCK_PYPROJECT_VERSION:
            return self._failure(
                target_url,
                f"the TCK checkout declares version {version}; the adapter is pinned to tag "
                f"{A2A_TCK_VERSION} ({A2A_TCK_PYPROJECT_VERSION} in its pyproject)",
            )
        commit = self._checkout_commit()
        if commit != A2A_TCK_COMMIT:
            return self._failure(
                target_url,
                f"the TCK checkout is at commit {commit or 'unknown'}; the adapter is pinned "
                f"to {A2A_TCK_COMMIT} (tag {A2A_TCK_VERSION})",
            )
        command = [*self._command, "--sut-host", _base_url(target_url), "--level", "must"]
        result = self._process.run(command, self._checkout, timeout_s)
        artifacts: list[ExternalArtifactData] = []
        if result.stderr:
            artifacts.append(
                ExternalArtifactData(
                    kind="stderr", filename="tck.stderr.txt", content=result.stderr
                )
            )
        if result.stdout:
            artifacts.append(
                ExternalArtifactData(
                    kind="stdout", filename="tck.stdout.txt", content=result.stdout
                )
            )
        if result.timed_out:
            return self._failure(
                target_url, f"the TCK did not finish within {timeout_s:.0f}s", artifacts
            )
        if not result.ran:
            return self._failure(
                target_url, f"the TCK could not start: {result.failed_to_start}", artifacts
            )
        report_path = self._checkout / REPORT_RELATIVE
        if not report_path.exists():
            return self._failure(
                target_url,
                f"the TCK exited with {result.returncode} and wrote no report",
                artifacts,
            )
        raw = report_path.read_bytes()
        artifacts.insert(
            0, ExternalArtifactData(kind="report", filename="compatibility.json", content=raw)
        )
        junit = self._checkout / "reports" / "junitreport.xml"
        if junit.exists():
            artifacts.append(
                ExternalArtifactData(
                    kind="junit", filename="junitreport.xml", content=junit.read_bytes()
                )
            )
        try:
            document: Any = json.loads(raw)
        except ValueError:
            return self._failure(target_url, "the compatibility report is not JSON", artifacts)
        normalized = normalize_tck_report(
            document if isinstance(document, dict) else {}, target_url
        )
        return normalized.model_copy(update={"artifacts": artifacts})

    @staticmethod
    def _failure(
        target_url: str, why: str, artifacts: list[ExternalArtifactData] | None = None
    ) -> ExternalToolResult:
        return ExternalToolResult(
            tool=TOOL,
            tool_version=A2A_TCK_VERSION,
            adapter_version=ADAPTER_VERSION,
            target_url=target_url,
            checks=[],
            artifacts=artifacts or [],
            failure=why,
        )
