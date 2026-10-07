"""The judge subprocess entry point: ``python -m suncly.judge.process``.

Reads one ``JudgeJob`` as JSON from stdin, asks the configured model endpoint,
and writes one ``ModelResponse`` as JSON to stdout. The model key is read from
the environment here and nowhere else, and it is redacted from everything that
leaves this process. Network access is limited to the configured endpoint: a
request hook refuses any other scheme, host or port, redirects are not
followed, and the environment's proxy settings are ignored. HTTPS is required
except for loopback addresses.

The endpoint speaks the Anthropic Messages API, ``POST /v1/messages``. The
facts below were verified against the official documentation on 2026-10-07 and
are recorded in docs/IMPLEMENTATION_NOTES.md, section 4:

- Headers: ``Authorization: Bearer <key>`` (built by ``key.py``),
  ``anthropic-version: 2023-06-01`` and ``content-type: application/json``.
- Body: ``model`` (the pinned id, DR-004), ``max_tokens``, one ``user`` message
  carrying the prompt the core built, and ``output_config.format`` with a JSON
  schema that admits exactly the object the rubric asks for, ``answer`` and
  ``rationale``, and nothing else. ``temperature`` ``0`` is sent to the models
  that still accept sampling parameters (up to the 4.6 generation); the API
  rejects any non-default value on later models, which run with their default
  settings.
- Answer: a ``message`` object whose ``model`` names the model that answered
  (the core compares it with the pin) and whose text content block holds the
  JSON. Only ``stop_reason`` ``end_turn`` is a complete answer: a refusal, a
  truncated answer (``max_tokens``) or any other stop is an error, which the
  core records as ``inconclusive``, never ``pass``.

Another provider replaces ``build_request``, ``request_headers`` and
``read_answer``; nothing in the core changes.
"""

from __future__ import annotations

import ipaddress
import json
import re
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

#: Characters of an error body kept in the error text when it is not the API's JSON error.
ERROR_BODY_CHARS = 200

#: The API version header every request must carry.
ANTHROPIC_VERSION = "2023-06-01"

#: Ceiling on generated tokens per question. The answer is a short JSON object, but on models
#: whose thinking is always on the thinking counts against this ceiling too; reaching it is a
#: truncated answer and so no verdict.
MAX_OUTPUT_TOKENS = 4096

#: The last model generation that accepts non-default sampling parameters: from 4.7 on the API
#: answers HTTP 400 to a ``temperature`` other than 1.0, so no later model is ever added here.
LAST_GENERATION_WITH_SAMPLING = (4, 6)

#: Claude model ids: ``claude-<name>-<major>[-<minor>][-<YYYYMMDD>]``.
MODEL_ID_PATTERN = re.compile(r"claude-[a-z]+-(\d+)(?:-(\d+))?(?:-\d{8})?")

#: What the rubric asks for and nothing else (core/rubric.py, rule 4); the core checks the values.
ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": ["string", "integer"]},
        "rationale": {"type": "string"},
    },
    "required": ["answer", "rationale"],
    "additionalProperties": False,
}

#: The one stop reason that means the answer is complete.
STOP_COMPLETE = "end_turn"
STOP_REFUSAL = "refusal"
STOP_INCOMPLETE = frozenset({"max_tokens", "model_context_window_exceeded"})


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


# -- the Messages API ------------------------------------------------------------------------


def model_generation(model: str) -> tuple[int, int] | None:
    """``(major, minor)`` of a Claude model id; ``None`` for any id of another form."""
    match = MODEL_ID_PATTERN.fullmatch(model)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2) or 0)


def accepts_sampling(model: str) -> bool:
    """Whether the API accepts a ``temperature`` other than 1.0 for ``model``."""
    generation = model_generation(model)
    return generation is not None and generation <= LAST_GENERATION_WITH_SAMPLING


def build_request(job: JudgeJob) -> dict[str, Any]:
    """The request body for one question: the pinned model, the prompt, the strict answer shape."""
    body: dict[str, Any] = {
        "model": job.model,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "messages": [{"role": "user", "content": job.prompt}],
        "output_config": {"format": {"type": "json_schema", "schema": ANSWER_SCHEMA}},
    }
    if accepts_sampling(job.model):
        body["temperature"] = 0
    return body


def request_headers(key: ModelKey) -> dict[str, str]:
    return {
        "content-type": "application/json",
        "accept": "application/json",
        "anthropic-version": ANTHROPIC_VERSION,
        **key.headers(),
    }


def _error_text(response: httpx.Response) -> str:
    """The API's errors are ``{"type": "error", "error": {"type", "message"}, "request_id"}``."""
    status = response.status_code
    try:
        body: Any = response.json()
    except ValueError:
        body = None
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        kind = error.get("type") if isinstance(error.get("type"), str) else "error"
        request_id = body.get("request_id")
        suffix = f" (request {request_id})" if isinstance(request_id, str) else ""
        return f"the Messages API answered HTTP {status} {kind}: {error['message']}{suffix}"
    return f"the Messages API answered HTTP {status}: {response.text[:ERROR_BODY_CHARS]}"


def read_answer(response: httpx.Response) -> ModelResponse:
    """The model that answered and the text of a complete answer, or why there is none."""
    if response.status_code != 200:
        return ModelResponse(error=_error_text(response))
    try:
        message: Any = response.json()
    except ValueError:
        return ModelResponse(error="the Messages API answered with a body that is not JSON")
    if not isinstance(message, dict) or message.get("type") != "message":
        kind = message.get("type") if isinstance(message, dict) else type(message).__name__
        return ModelResponse(
            error=f"the Messages API answered with a {kind!r} object, not a message"
        )
    reported = message.get("model")
    model = reported if isinstance(reported, str) else None
    stop_reason = message.get("stop_reason")
    if stop_reason == STOP_REFUSAL:
        details = message.get("stop_details")
        category = details.get("category") if isinstance(details, dict) else None
        return ModelResponse(
            model=model,
            error=f"the model refused to answer (stop_reason {stop_reason!r}, "
            f"category {category!r})",
        )
    if stop_reason in STOP_INCOMPLETE:
        return ModelResponse(
            model=model,
            error=f"the answer is incomplete (stop_reason {stop_reason!r}; the ceiling is "
            f"{MAX_OUTPUT_TOKENS} output tokens)",
        )
    if stop_reason != STOP_COMPLETE:
        return ModelResponse(
            model=model,
            error=f"the model stopped before a complete answer (stop_reason {stop_reason!r})",
        )
    content = message.get("content")
    texts = [
        block["text"]
        for block in (content if isinstance(content, list) else [])
        if isinstance(block, dict)
        and block.get("type") == "text"
        and isinstance(block.get("text"), str)
    ]
    if not texts:
        return ModelResponse(model=model, error="the message carries no text block")
    return ModelResponse(model=model, text="".join(texts))


def call_endpoint(job: JudgeJob, key: ModelKey) -> ModelResponse:
    """Ask the Messages API once (module docstring)."""
    with endpoint_client(job.endpoint, job.timeout_s) as client:
        try:
            response = client.post(
                job.endpoint,
                content=json.dumps(build_request(job)).encode("utf-8"),
                headers=request_headers(key),
            )
        except httpx.TimeoutException as exc:
            return ModelResponse(
                error=f"timeout: the model endpoint did not answer within {job.timeout_s:g}s "
                f"({type(exc).__name__})",
                timed_out=True,
            )
        except (httpx.HTTPError, OSError) as exc:
            return ModelResponse(error=f"the model endpoint could not be reached: {exc}")
    return read_answer(response)


# -- the process -----------------------------------------------------------------------------


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
