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

from pydantic import ValidationError

from suncly.ports.run_executor import RunJob, RunResult
from suncly.runner.credentials import read_credentials
from suncly.runner.http_transport import HttpxJsonRpcTransport
from suncly.runner.protocol import execute_run
from suncly.runner.redaction import Redactor, redact_transcript


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def main(stdin: TextIO, stdout: TextIO, env: Mapping[str, str]) -> int:
    """Run one job. Always writes a ``RunResult``; returns 0 when it did."""
    credentials = read_credentials(env)
    redactor = Redactor(credentials.secrets())

    def emit(result: RunResult) -> int:
        stdout.write(result.model_dump_json())
        stdout.flush()
        return 0

    try:
        job = RunJob.model_validate_json(stdin.read())
    except ValidationError as exc:
        return emit(RunResult(crashed=True, error=f"invalid run job: {exc.error_count()} error(s)"))
    if not job.sandbox_declared:
        return emit(
            RunResult(
                crashed=True,
                error="refused: the target is not declared a sandbox or dry-run endpoint (DR-006)",
            )
        )
    try:
        transport = HttpxJsonRpcTransport(
            job.target_url, job.protocol_version, credentials.headers()
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
