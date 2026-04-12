"""Middleware registration."""

from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def correlation_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = str(uuid4())
        request.state.correlation_id = correlation_id
        started_at = perf_counter()

        response = await call_next(request)

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        response.headers["X-Correlation-ID"] = correlation_id
        logger.info(
            "request_complete method=%s path=%s status_code=%s duration_ms=%s correlation_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            correlation_id,
        )
        return response
