"""Middleware registration."""

from __future__ import annotations

from hmac import compare_digest
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.formparsers import MultiPartParser
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import IN_FLIGHT_REQUESTS, metric_path_for_request, record_request

logger = get_logger(__name__)

_ORIGIN_SECRET_HEADER = "X-Origin-Verify"


class OriginSecretMiddleware(BaseHTTPMiddleware):
    """Reject direct Lambda Function URL requests that bypass CloudFront."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if settings.deployment_target != "lambda" or not settings.origin_secret_enabled:
            return await call_next(request)

        provided_secret = request.headers.get(_ORIGIN_SECRET_HEADER)
        allowed_secrets = [
            secret for secret in (settings.origin_secret, settings.origin_secret_previous) if secret
        ]
        secret_matches = provided_secret is not None and any(
            compare_digest(provided_secret, secret) for secret in allowed_secrets
        )
        if secret_matches:
            return await call_next(request)

        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        started_at = perf_counter()
        response = JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Forbidden."},
        )
        response.headers["X-Correlation-ID"] = correlation_id
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration_ms / 1000,
            error_code="origin_secret_invalid",
        )
        logger.warning(
            "origin_secret_rejected",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "origin_secret_configured": bool(allowed_secrets),
            },
        )
        return response


def register_middleware(app: FastAPI) -> None:
    """Register cross-cutting request middleware."""

    MultiPartParser.spool_max_size = settings.max_upload_size_bytes
    MultiPartParser.max_part_size = settings.max_upload_size_bytes

    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Correlation-ID"],
        )

    @app.middleware("http")
    async def correlation_and_policy_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        request.state.correlation_id = correlation_id
        request.state.upload_audit = []
        started_at = perf_counter()
        response: Response

        IN_FLIGHT_REQUESTS.inc()

        try:
            if settings.auth_boundary_enabled and not settings.is_development:
                trusted_identity = request.headers.get(settings.trusted_identity_header)
                if not trusted_identity:
                    return _finalize_response(
                        request=request,
                        response=JSONResponse(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            content={
                                "detail": (
                                    "Authentication boundary is enabled and the trusted identity "
                                    "header is missing."
                                )
                            },
                        ),
                        started_at=started_at,
                        correlation_id=correlation_id,
                    )

            content_length = request.headers.get("content-length")
            if content_length is not None and content_length.isdigit():
                if int(content_length) > settings.max_upload_size_bytes:
                    size_limit_message = (
                        f"Uploaded payload exceeds the {settings.max_upload_size_bytes} byte limit."
                    )
                    response = JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": size_limit_message},
                    )
                    return _finalize_response(
                        request=request,
                        response=response,
                        started_at=started_at,
                        correlation_id=correlation_id,
                    )

            response = await call_next(request)
        finally:
            IN_FLIGHT_REQUESTS.dec()

        return _finalize_response(
            request=request,
            response=response,
            started_at=started_at,
            correlation_id=correlation_id,
        )

    if settings.deployment_target == "lambda" and settings.origin_secret_enabled:
        app.add_middleware(OriginSecretMiddleware)


def _finalize_response(
    *,
    request: Request,
    response: Response,
    started_at: float,
    correlation_id: str,
) -> Response:
    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    response.headers["X-Correlation-ID"] = correlation_id
    request_path = metric_path_for_request(request)
    error_code = getattr(request.state, "error_code", None)
    record_request(
        method=request.method,
        path=request_path,
        status_code=response.status_code,
        duration_seconds=duration_ms / 1000,
        error_code=error_code,
    )

    logger.info(
        "request_complete",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request_path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "uploads": getattr(request.state, "upload_audit", []),
        },
    )
    return response
