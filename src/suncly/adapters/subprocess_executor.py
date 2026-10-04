"""Runs the Runner as a separate process (schema §2: its own process, isolated).

The job goes in on stdin, the result comes back on stdout. The child inherits
the environment, which is how the credential reaches it; this process never
reads that variable (DR-003). Nothing from the child's stderr is surfaced, so
nothing but the redacted result ever leaves the Runner.
"""

from __future__ import annotations

import subprocess
import sys

from pydantic import ValidationError

from suncly.ports.run_executor import RunJob, RunResult

#: Seconds the process may outlive the run timeout before it is killed.
GRACE_S = 10.0


class SubprocessRunExecutor:
    def __init__(self, python: str | None = None) -> None:
        self._python = python or sys.executable

    def execute(self, job: RunJob) -> RunResult:
        command = [self._python, "-m", "suncly.runner.process"]
        try:
            completed = subprocess.run(
                command,
                input=job.model_dump_json().encode("utf-8"),
                capture_output=True,
                timeout=job.timeout_s + GRACE_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                crashed=True,
                error=f"the Runner process did not finish within {job.timeout_s + GRACE_S:.0f}s "
                "and was killed",
            )
        except OSError as exc:
            return RunResult(crashed=True, error=f"the Runner process could not start: {exc}")
        if not completed.stdout.strip():
            return RunResult(
                crashed=True,
                error=f"the Runner process exited with code {completed.returncode} and no result",
            )
        try:
            return RunResult.model_validate_json(completed.stdout)
        except ValidationError:
            return RunResult(
                crashed=True,
                error=f"the Runner process exited with code {completed.returncode} and an "
                "unreadable result",
            )
