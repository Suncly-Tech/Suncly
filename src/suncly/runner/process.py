"""The Runner process entry point: ``python -m suncly.runner.process``.

Reads one ``RunJob`` as JSON from stdin, executes it, redacts the transcript,
and writes one ``RunResult`` as JSON to stdout. Credentials are read from the
environment here and nowhere else (DR-003). Nothing is ever logged.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TextIO

from pydantic import BaseModel, ConfigDict, ValidationError

from suncly.domain.network import NetworkPolicy
from suncly.domain.tenancy import DeploymentMode
from suncly.ports.run_executor import RunJob, RunResult
from suncly.runner.credentials import Credentials, read_credentials
from suncly.runner.http_transport import HttpxJsonRpcTransport
from suncly.runner.protocol import execute_run
from suncly.runner.redaction import Redactor, redact_transcript

#: The deployment's network mode; ``local`` only on a developer machine (docs/ARCHITECTURE.md).
NETWORK_MODE_ENV_VAR = "SUNCLY_NETWORK_MODE"


def network_policy_from(env: Mapping[str, str]) -> NetworkPolicy:
    raw = env.get(NETWORK_MODE_ENV_VAR, "").strip().lower() or DeploymentMode.LOCAL.value
    try:
        mode = DeploymentMode(raw)
    except ValueError:
        mode = DeploymentMode.PUBLIC  # an unknown value never widens what the Runner may reach
    return NetworkPolicy.for_mode(mode)


class RunEnvelope(BaseModel):
    """What a scoped executor writes to stdin: the job, plus the one credential it needs.

    The credential is delivered this way (never through an inherited
    environment) by ``adapters/scoped_executor.py``. A bare ``RunJob`` on
    stdin is still accepted for the CLI path, where the credential comes from
    the environment variable read in ``runner/credentials.py``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    job: RunJob
    authorization: str | None = None


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def main(stdin: TextIO, stdout: TextIO, env: Mapping[str, str]) -> int:
    """Run one job. Always writes a ``RunResult``; returns 0 when it did."""
    credentials = read_credentials(env)
    policy = network_policy_from(env)

    def emit(result: RunResult) -> int:
        stdout.write(result.model_dump_json())
        stdout.flush()
        return 0

    raw = stdin.read()
    try:
        envelope = RunEnvelope.model_validate_json(raw)
        job = envelope.job
        if envelope.authorization:
            credentials = Credentials(authorization=envelope.authorization.strip() or None)
    except ValidationError:
        try:
            job = RunJob.model_validate_json(raw)
        except ValidationError as exc:
            redactor = Redactor(credentials.secrets())
            return emit(
                RunResult(crashed=True, error=f"invalid run job: {exc.error_count()} error(s)")
            )
    redactor = Redactor(credentials.secrets())
    if not job.sandbox_declared:
        return emit(
            RunResult(
                crashed=True,
                error="refused: the target is not declared a sandbox or dry-run endpoint (DR-006)",
            )
        )
    try:
        transport = HttpxJsonRpcTransport(
            job.target_url, job.protocol_version, credentials.headers(), policy=policy
        )
        try:
            transcript = execute_run(job, transport, _SystemClock(), time.sleep, time.monotonic)
        finally:
            transport.close()
    except Exception as exc:  # the Runner must always answer; the error text is redacted too
        message = redactor.redact_text(f"{type(exc).__name__}: {exc}")
        return emit(RunResult(crashed=True, error=message))
    try:
        redacted = redact_transcript(transcript, redactor)
    except Exception as exc:  # redaction failed: withhold the transcript (OQ-A11)
        return emit(
            RunResult(
                withheld=True, error=f"redaction failed: {type(exc).__name__}; transcript withheld"
            )
        )
    return emit(RunResult(transcript=redacted))


if __name__ == "__main__":  # pragma: no cover - exercised through the subprocess executor
    import os

    sys.exit(main(sys.stdin, sys.stdout, os.environ))
