"""Runs the judge subprocess (OQ-A1, decided 2026-10-07: the key lives only there).

The job goes in on stdin, the answer comes back on stdout. The child's
environment is built from scratch: it holds the one key variable, forwarded by
name from this process's environment without being parsed or stored, plus
what the operating system needs to start Python. Nothing else (the agent
credential, ``DATABASE_URL``, proxies) reaches the child, and nothing from the
child's stderr is surfaced.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping

from pydantic import ValidationError

from suncly.judge.job import JudgeJob
from suncly.judge.key import JUDGE_KEY_ENV_VAR
from suncly.ports.model_judge import ModelRequest, ModelResponse

#: Seconds the process may outlive the model timeout before it is killed.
GRACE_S = 10.0

#: Variables Python itself needs to start on some platforms (Windows: SYSTEMROOT).
PLATFORM_PASSTHROUGH = ("SYSTEMROOT",)


def child_environment(parent_env: Mapping[str, str]) -> dict[str, str]:
    """The from-scratch environment of the judge subprocess."""
    return {
        name: parent_env[name]
        for name in (JUDGE_KEY_ENV_VAR, *PLATFORM_PASSTHROUGH)
        if name in parent_env
    }


class SubprocessModelJudge:
    def __init__(
        self, endpoint: str, parent_env: Mapping[str, str], python: str | None = None
    ) -> None:
        self._endpoint = endpoint
        self._parent_env = parent_env
        self._python = python or sys.executable

    def ask(self, request: ModelRequest) -> ModelResponse:
        job = JudgeJob(
            endpoint=self._endpoint,
            model=request.model,
            prompt=request.prompt,
            timeout_s=request.timeout_s,
        )
        command = [self._python, "-m", "suncly.judge.process"]
        try:
            completed = subprocess.run(
                command,
                input=job.model_dump_json().encode("utf-8"),
                capture_output=True,
                timeout=request.timeout_s + GRACE_S,
                env=child_environment(self._parent_env),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ModelResponse(
                error=f"the judge process did not finish within {request.timeout_s + GRACE_S:.0f}s "
                "and was killed",
                timed_out=True,
            )
        except OSError as exc:
            return ModelResponse(error=f"the judge process could not start: {exc}")
        if not completed.stdout.strip():
            return ModelResponse(
                error=f"the judge process exited with code {completed.returncode} and no answer"
            )
        try:
            return ModelResponse.model_validate_json(completed.stdout)
        except ValidationError:
            return ModelResponse(
                error=f"the judge process exited with code {completed.returncode} and an "
                "unreadable answer"
            )
