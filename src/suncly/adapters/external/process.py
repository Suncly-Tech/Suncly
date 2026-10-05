"""Runs an external tool as a child process inside the Runner boundary.

The child gets the same minimal environment as the Runner process
(``adapters/scoped_executor.py``): what Python or Node need to start, the
network mode, and, only when the tool needs it to reach the sandbox, the
agent credential in one variable the tool is documented to read. Nothing
else from the worker's environment reaches the tool. Output is bounded,
the process is killed at the deadline, and whatever it wrote into its work
directory is read back by the adapter, never trusted as a verdict.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from suncly.adapters.scoped_executor import minimal_environment
from suncly.domain.tenancy import DeploymentMode
from suncly.runner.credentials import CREDENTIAL_ENV_VAR

#: Bytes of stdout/stderr kept per stream; the rest is dropped, never stored.
MAX_CAPTURED_BYTES = 200_000


def credential_environment(credential: str | None) -> dict[str, str]:
    """The one variable a tool may read the agent credential from (DR-003: the Runner's)."""
    return {CREDENTIAL_ENV_VAR: credential} if credential else {}


@dataclass(frozen=True)
class ToolProcessResult:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool
    failed_to_start: str | None = None

    @property
    def ran(self) -> bool:
        return self.failed_to_start is None and not self.timed_out


class ToolProcess:
    def __init__(
        self,
        base_environment: Mapping[str, str],
        network_mode: DeploymentMode,
        extra_environment: Mapping[str, str] | None = None,
    ) -> None:
        self._env = minimal_environment(base_environment, network_mode)
        self._env.update(extra_environment or {})

    def run(self, command: Sequence[str], cwd: Path, timeout_s: float) -> ToolProcessResult:
        try:
            completed = subprocess.run(
                list(command),
                cwd=str(cwd),
                env=self._env,
                capture_output=True,
                timeout=timeout_s,
                check=False,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired as exc:
            return ToolProcessResult(
                returncode=None,
                stdout=(exc.stdout or b"")[:MAX_CAPTURED_BYTES],
                stderr=(exc.stderr or b"")[:MAX_CAPTURED_BYTES],
                timed_out=True,
            )
        except OSError as exc:
            return ToolProcessResult(
                returncode=None, stdout=b"", stderr=b"", timed_out=False, failed_to_start=str(exc)
            )
        return ToolProcessResult(
            returncode=completed.returncode,
            stdout=completed.stdout[:MAX_CAPTURED_BYTES],
            stderr=completed.stderr[:MAX_CAPTURED_BYTES],
            timed_out=False,
        )
