"""External evaluation tools (the A2A TCK, a Promptfoo test pack) behind one port.

A tool run produces normalized evidence: one ``ExternalCheck`` per check the
tool performed, in Suncly's categories, plus the source artifacts the tool
wrote, kept byte for byte. The tool's version is recorded with the evidence.
Tools run inside the Runner boundary, so credentials and the target host rule
apply to them as to any run.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from suncly.domain.policy import TestCategory

JsonObject = dict[str, Any]


class ExternalCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    category: TestCategory
    passed: bool | None
    """``None`` when the tool could not decide (skipped, errored): never a pass."""
    level: str = ""
    """RFC 2119 level for the TCK (must, should, may) or the plugin for Promptfoo."""
    detail: str = ""


class ExternalArtifactData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    filename: str
    content: bytes


class ExternalToolResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool: str
    tool_version: str
    adapter_version: str
    target_url: str
    checks: list[ExternalCheck]
    artifacts: list[ExternalArtifactData] = Field(default_factory=list)
    failure: str | None = None
    """Set when the tool could not run at all; every check is then absent, not passed."""

    def counts(self) -> dict[str, int]:
        return {
            "passed": sum(1 for c in self.checks if c.passed is True),
            "failed": sum(1 for c in self.checks if c.passed is False),
            "undecided": sum(1 for c in self.checks if c.passed is None),
        }


class ExternalToolRunner(Protocol):
    tool: str
    tool_version: str

    def run(self, target_url: str, work_dir: str, timeout_s: float) -> ExternalToolResult: ...
