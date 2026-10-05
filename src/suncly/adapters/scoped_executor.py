"""Runs the Runner as a separate process with an explicit, minimal environment.

Unlike ``subprocess_executor.py`` (the CLI path, which lets the child inherit
the environment so the credential variable reaches it), this executor builds
the child's environment from scratch: the interpreter's path, the network
mode and nothing else. The one credential the job needs is resolved through
the ``SecretResolver`` right before the process starts and delivered on
stdin inside a ``RunEnvelope``, never through the environment, never on the
command line, never in the job. Nothing from the child's stderr is surfaced.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from pydantic import ValidationError

from suncly.domain.errors import RunnerError
from suncly.domain.tenancy import CredentialReference, DeploymentMode
from suncly.ports.run_executor import RunJob, RunResult
from suncly.ports.secrets import SecretResolver

#: Seconds the process may outlive the run timeout before it is killed.
GRACE_S = 10.0
#: Environment variables a Runner process needs to start at all.
INHERITED_FOR_START = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR", "PYTHONPATH", "VIRTUAL_ENV")


def minimal_environment(base: Mapping[str, str], network_mode: DeploymentMode) -> dict[str, str]:
    """The child's environment: what Python needs to start, plus the network mode."""
    env = {name: base[name] for name in INHERITED_FOR_START if name in base}
    env["SUNCLY_NETWORK_MODE"] = network_mode.value
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


class ScopedSubprocessRunExecutor:
    def __init__(
        self,
        secrets: SecretResolver,
        credential: CredentialReference,
        network_mode: DeploymentMode,
        base_environment: Mapping[str, str],
        python: str | None = None,
    ) -> None:
        self._secrets = secrets
        self._credential = credential
        self._network_mode = network_mode
        self._python = python or sys.executable
        self._env = minimal_environment(base_environment, network_mode)
        self._cached: str | None = None
        self._resolved = False

    def _authorization(self) -> str | None:
        if not self._resolved:
            self._cached = self._secrets.resolve(self._credential)
            self._resolved = True
        return self._cached

    def execute(self, job: RunJob) -> RunResult:
        try:
            authorization = self._authorization()
        except RunnerError as exc:
            return RunResult(crashed=True, error=f"credential unavailable: {exc.what}")
        envelope = {"job": job.model_dump(mode="json"), "authorization": authorization}
        import json

        command = [self._python, "-m", "suncly.runner.process"]
        try:
            completed = subprocess.run(
                command,
                input=json.dumps(envelope).encode("utf-8"),
                capture_output=True,
                timeout=job.timeout_s + GRACE_S,
                check=False,
                env=self._env,
                cwd=str(Path(os.getcwd())),
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
