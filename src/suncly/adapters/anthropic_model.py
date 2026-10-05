"""The Anthropic adapter for the structured model port (the first provider).

Selected from the current official documentation: the Messages API with a
JSON-schema output format (``output_config.format``). The model id, output
limit and effort are pinned by ``ModelConfig``; every response's model
identity, usage and request id are returned for the evidence. The adapter
never passes tools and never sees a customer credential. Every failure mode
is an explicit ``StructuredResponse`` failure: a timeout, a connection or
API error, a refusal, a truncated answer, or an answer that does not
validate against the schema. None of them is ever a pass.

The API key is given to the constructor by the composition root; this module
reads no environment.
"""

from __future__ import annotations

import json
import time
from typing import Any

import jsonschema

from suncly.ports.model import (
    ModelFailureKind,
    ModelUsage,
    StructuredRequest,
    StructuredResponse,
)

#: Why ``anthropic`` is imported lazily: it is an optional extra of the package.
_IMPORT_HINT = "Install suncly[anthropic] to use the Anthropic provider."


class AnthropicStructuredClient:
    name = "anthropic"

    def __init__(self, api_key: str, max_retries: int = 1) -> None:
        if not api_key.strip():
            raise ValueError("the Anthropic adapter needs an API key")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - needs the optional extra
            raise RuntimeError(_IMPORT_HINT) from exc
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key, max_retries=max_retries)

    def complete(self, request: StructuredRequest) -> StructuredResponse:
        anthropic = self._anthropic
        config = request.config
        output_config: dict[str, Any] = {
            "format": {"type": "json_schema", "schema": request.schema_}
        }
        if config.effort:
            output_config["effort"] = config.effort
        params: dict[str, Any] = {
            "model": config.model,
            "max_tokens": config.max_output_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": request.user}],
            "output_config": output_config,
        }
        started = time.monotonic()
        try:
            response: Any = self._client.with_options(timeout=config.timeout_s).messages.create(
                **params
            )
        except anthropic.APITimeoutError as exc:
            return self._failure(ModelFailureKind.TIMEOUT, str(exc), config.identity, started)
        except anthropic.APIConnectionError as exc:
            return self._failure(ModelFailureKind.UNAVAILABLE, str(exc), config.identity, started)
        except anthropic.APIStatusError as exc:
            detail = f"HTTP {exc.status_code}: {type(exc).__name__}"
            return self._failure(ModelFailureKind.UNAVAILABLE, detail, config.identity, started)
        latency_ms = int((time.monotonic() - started) * 1000)
        usage = ModelUsage(
            input_tokens=int(getattr(response.usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(response.usage, "output_tokens", 0) or 0),
            cache_read_tokens=int(getattr(response.usage, "cache_read_input_tokens", 0) or 0),
            provider_request_id=getattr(response, "_request_id", None),
        )
        model = str(getattr(response, "model", config.model))
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            return StructuredResponse(
                failure=ModelFailureKind.REFUSAL,
                failure_detail=f"the model declined ({category or 'no category'})",
                model=model,
                usage=usage,
                latency_ms=latency_ms,
            )
        text = "".join(
            str(getattr(block, "text", ""))
            for block in getattr(response, "content", [])
            if getattr(block, "type", "") == "text"
        )
        if stop_reason == "max_tokens":
            return StructuredResponse(
                raw_text=text,
                failure=ModelFailureKind.TRUNCATED,
                failure_detail="the answer hit max_output_tokens",
                model=model,
                usage=usage,
                latency_ms=latency_ms,
            )
        try:
            parsed = json.loads(text)
            jsonschema.validate(parsed, request.schema_)
        except (ValueError, jsonschema.ValidationError) as exc:
            return StructuredResponse(
                raw_text=text,
                failure=ModelFailureKind.MALFORMED,
                failure_detail=f"{type(exc).__name__}: {str(exc)[:200]}",
                model=model,
                usage=usage,
                latency_ms=latency_ms,
            )
        if not isinstance(parsed, dict):
            return StructuredResponse(
                raw_text=text,
                failure=ModelFailureKind.MALFORMED,
                failure_detail="the answer is not a JSON object",
                model=model,
                usage=usage,
                latency_ms=latency_ms,
            )
        return StructuredResponse(
            parsed=parsed, raw_text=text, model=model, usage=usage, latency_ms=latency_ms
        )

    @staticmethod
    def _failure(
        kind: ModelFailureKind, detail: str, model: str, started: float
    ) -> StructuredResponse:
        return StructuredResponse(
            failure=kind,
            failure_detail=detail[:300],
            model=model,
            latency_ms=int((time.monotonic() - started) * 1000),
        )
