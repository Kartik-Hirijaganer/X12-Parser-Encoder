"""API error-envelope helpers."""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from app.core.logging import get_logger
from app.schemas.base import to_camel

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register boundary handlers that keep API errors in one envelope."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(
            request=request,
            status_code=exc.status_code,
            detail=exc.detail,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details={"errors": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.headers.get("X-Correlation-ID") or getattr(
            request.state, "correlation_id", None
        )
        logger.exception(
            "unhandled_api_exception",
            extra={
                "correlation_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        return error_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            message="Internal server error.",
        )


def error_response(
    *,
    request: Request,
    status_code: int,
    detail: Any = None,
    code: str | None = None,
    message: str | None = None,
    details: dict[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build a JSON error response using the standard Aegis envelope."""

    request_id = request.headers.get("X-Correlation-ID") or getattr(
        request.state, "correlation_id", None
    )
    if not request_id:
        request_id = str(uuid4())
        request.state.correlation_id = request_id

    payload = error_payload(
        status_code=status_code,
        request_id=request_id,
        detail=detail,
        code=code,
        message=message,
        details=details,
    )
    request.state.error_code = str(payload["code"]).lower()
    response = JSONResponse(status_code=status_code, content=payload, headers=headers)
    response.headers["X-Correlation-ID"] = request_id
    return response


def error_payload(
    *,
    status_code: int,
    request_id: str,
    detail: Any = None,
    code: str | None = None,
    message: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Shape an arbitrary FastAPI error detail into the public envelope."""

    detail = jsonable_encoder(detail)
    details = jsonable_encoder(details) if details is not None else None
    resolved_code = code or _status_code_name(status_code)
    resolved_message = message
    resolved_details: dict[str, Any] = details.copy() if details else {}

    if detail is not None and not resolved_details:
        if isinstance(detail, dict):
            detail_message = detail.get("message")
            if resolved_message is None and isinstance(detail_message, str):
                resolved_message = detail_message
            resolved_details = {
                str(key): value for key, value in detail.items() if key != "message"
            }
        elif isinstance(detail, list):
            resolved_details = {"errors": detail}
        elif resolved_message is None:
            resolved_message = str(detail)

    if resolved_message is None:
        resolved_message = _status_reason(status_code)

    return {
        "code": resolved_code,
        "message": resolved_message,
        "details": _camelize_keys(resolved_details),
        "requestId": request_id,
    }


def _camelize_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            to_camel(str(key)) if "_" in str(key) else str(key): _camelize_keys(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_camelize_keys(item) for item in value]
    return value


def _status_code_name(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase.upper().replace(" ", "_").replace("-", "_")
    except ValueError:
        return "ERROR"


def _status_reason(status_code: int) -> str:
    try:
        return f"{HTTPStatus(status_code).phrase}."
    except ValueError:
        return "Request failed."
