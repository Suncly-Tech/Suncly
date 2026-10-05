"""One error envelope for every HTTP response (docs/API.md: Errors).

Every error is ``{"error": {"code", "message", "detail", "next_step", "request_id"}}``.
Suncly's own error classes map to status codes here; FastAPI's request
validation errors are rewrapped so clients see one shape. Nothing in an
envelope ever carries a credential or a stack trace.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from suncly.domain.errors import (
    AuthenticationError,
    AuthorizationError,
    BillingError,
    CardError,
    ConflictError,
    ContractError,
    NotFoundError,
    QuotaError,
    RefusedError,
    SunclyError,
    ValidationFailedError,
)

STATUS_BY_ERROR: list[tuple[type[SunclyError], int, str]] = [
    (AuthenticationError, 401, "unauthenticated"),
    (AuthorizationError, 403, "forbidden"),
    (NotFoundError, 404, "not_found"),
    (ConflictError, 409, "conflict"),
    (QuotaError, 402, "quota_exceeded"),
    (ValidationFailedError, 422, "validation_failed"),
    (ContractError, 422, "contract_invalid"),
    (CardError, 422, "card_unusable"),
    (RefusedError, 422, "refused"),
    (BillingError, 502, "billing_provider"),
]


def envelope(
    code: str, message: str, detail: str = "", next_step: str = "", request_id: str | None = None
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
            "next_step": next_step,
            "request_id": request_id,
        }
    }


def request_id_of(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str):
        return existing
    generated = request.headers.get("x-request-id") or uuid.uuid4().hex
    request.state.request_id = generated
    return generated


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SunclyError)
    async def suncly_error(request: Request, exc: SunclyError) -> JSONResponse:
        status, code = 500, "internal_error"
        for cls, candidate_status, candidate_code in STATUS_BY_ERROR:
            if isinstance(exc, cls):
                status, code = candidate_status, candidate_code
                break
        return JSONResponse(
            status_code=status,
            content=envelope(code, exc.what, exc.why, exc.next_step, request_id_of(request)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in error.get('loc', [])[1:]) or '<body>'}: {error.get('msg')}"
            for error in exc.errors()[:8]
        )
        return JSONResponse(
            status_code=422,
            content=envelope(
                "validation_failed",
                "The request does not match the API contract.",
                problems,
                "See the OpenAPI document at /openapi.json.",
                request_id_of(request),
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=envelope(
                "internal_error",
                "Suncly hit an internal error.",
                type(exc).__name__,
                "Retry with the request id in a support request.",
                request_id_of(request),
            ),
        )
