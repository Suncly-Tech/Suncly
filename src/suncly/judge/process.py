"""The judge subprocess entry point: ``python -m suncly.judge.process``.

Reads one ``JudgeJob`` as JSON from stdin, asks the configured model endpoint,
and writes one ``ModelResponse`` as JSON to stdout. The model key is read from
the environment here and nowhere else, and it is redacted from everything that
leaves this process. Network access is limited to the configured endpoint: a
request hook refuses any other scheme, host or port, redirects are not
followed, and the environment's proxy settings are ignored. HTTPS is required
except for loopback addresses.

The wire shape spoken to the endpoint is a placeholder until a real provider
adapter exists (docs/STAGE_4_BRIEF.md): ``POST <endpoint>`` with the JSON body
``{"model": <id>, "input": <prompt>}`` and ``Authorization: Bearer <key>``;
the answer is a JSON object with ``"model"`` (the id that answered) and
``"output"`` (the answer text). A real provider adapter replaces
``call_endpoint`` and nothing else.
"""

from __future__ import annotations

import ipaddress
import json
import sys
from collections.abc import Mapping
from typing import Any, TextIO
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from suncly.judge.job import JudgeJob
from suncly.judge.key import JUDGE_KEY_ENV_VAR, ModelKey, read_key
from suncly.ports.model_judge import ModelResponse

LOOPBACK_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})

#: Characters of an endpoint error body kept in the error text.
ERROR_BODY_CHARS = 200


class EndpointRefusedError(Exception):
    """The subprocess refused to talk to a URL other than the configured endpoint."""


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def require_https_or_loopback(url: str) -> None:
    """Refuse plain http anywhere but loopback, where test endpoints run."""
    parts = urlsplit(url)
    if parts.scheme == "https":
        return
    if parts.scheme == "http" and is_loopback_host(parts.hostname):
        return
    raise EndpointRefusedError(
        f"the model endpoint must use https; {url} uses {parts.scheme or 'no scheme'} "
        "(plain http is allowed only for loopback addresses)"
    )


def _origin(url: httpx.URL) -> tuple[str, str, int | None]:
    return url.scheme, (url.host or "").lower(), url.port


def endpoint_client(endpoint_url: str, timeout_s: float) -> httpx.Client:
    """A client that can only reach the configured endpoint's scheme, host and port."""
    require_https_or_loopback(endpoint_url)
    endpoint = _origin(httpx.URL(endpoint_url))

    def refuse_other_hosts(request: httpx.Request) -> None:
        if _origin(request.url) != endpoint:
            raise EndpointRefusedError(
                f"refused a request to {request.url.scheme}://{request.url.host}; the configured "
                f"endpoint is {endpoint[0]}://{endpoint[1]}"
            )

    return httpx.Client(
        follow_redirects=False,
        trust_env=False,
        timeout=httpx.Timeout(timeout_s, connect=min(timeout_s, 10.0)),
        event_hooks={"request": [refuse_other_hosts]},
    )


def call_endpoint(job: JudgeJob, key: ModelKey) -> ModelResponse:
    """Ask the endpoint once, in the placeholder wire shape described in the module docstring."""
    body = {"model": job.model, "input": job.prompt}
    with endpoint_client(job.endpoint, job.timeout_s) as client:
        try:
            response = client.post(
                job.endpoint,
                content=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    **key.headers(),
                },
            )
        except httpx.TimeoutException as exc:
            return ModelResponse(
                error=f"timeout: the model endpoint did not answer within {job.timeout_s:g}s "
                f"({type(exc).__name__})",
                timed_out=True,
            )
        except (httpx.HTTPError, OSError) as exc:
            return ModelResponse(error=f"the model endpoint could not be reached: {exc}")
    if response.status_code != 200:
        snippet = response.text[:ERROR_BODY_CHARS]
        return ModelResponse(
            error=f"the model endpoint answered HTTP {response.status_code}: {snippet}"
        )
    try:
        answer: Any = response.json()
    except ValueError:
        return ModelResponse(error="the model endpoint answered with a body that is not JSON")
    if not isinstance(answer, dict) or not isinstance(answer.get("output"), str):
        return ModelResponse(
            error='the model endpoint answered without a string "output"; the answer is unusable'
        )
    reported = answer.get("model")
    return ModelResponse(
        model=reported if isinstance(reported, str) else None, text=answer["output"]
    )


def redacted(response: ModelResponse, key: ModelKey) -> ModelResponse:
    """The same response with the key removed from every text field."""
    return ModelResponse(
        model=key.redact(response.model) if response.model is not None else None,
        text=key.redact(response.text) if response.text is not None else None,
        error=key.redact(response.error) if response.error is not None else None,
        timed_out=response.timed_out,
    )


def main(stdin: TextIO, stdout: TextIO, env: Mapping[str, str]) -> int:
    """Answer one job. Always writes a ``ModelResponse``; returns 0 when it did."""
    key = read_key(env)

    def emit(response: ModelResponse) -> int:
        stdout.write(redacted(response, key).model_dump_json())
        stdout.flush()
        return 0

    try:
        job = JudgeJob.model_validate_json(stdin.read())
    except ValidationError as exc:
        return emit(ModelResponse(error=f"invalid judge job: {exc.error_count()} error(s)"))
    if key.value is None:
        return emit(
            ModelResponse(
                error=f"no model key: {JUDGE_KEY_ENV_VAR} is not set for the judge subprocess"
            )
        )
    try:
        return emit(call_endpoint(job, key))
    except Exception as exc:  # the subprocess must always answer; the text is redacted too
        return emit(ModelResponse(error=f"{type(exc).__name__}: {exc}"))


if __name__ == "__main__":  # pragma: no cover - exercised through the subprocess adapter
    import io
    import os

    # The from-scratch environment sets no locale, so the streams are made UTF-8 explicitly.
    stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", write_through=True)
    sys.exit(main(stdin, stdout, os.environ))
