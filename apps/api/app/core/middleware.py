"""Middleware registration."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Hashable
from threading import Lock
from time import perf_counter, time
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.formparsers import MultiPartParser
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import IN_FLIGHT_REQUESTS, metric_path_for_request, record_request

logger = get_logger(__name__)

_UPLOAD_PATHS = {
    f"{settings.api_v1_prefix}/convert",
    f"{settings.api_v1_prefix}/parse",
    f"{settings.api_v1_prefix}/pipeline",
    f"{settings.api_v1_prefix}/validate",
}
_rate_limit_lock = Lock()
_request_windows: dict[Hashable, deque[float]] = defaultdict(deque)
_in_flight_lock = Lock()
_in_flight_uploads: dict[Hashable, int] = defaultdict(int)


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

        user_key = _request_key(request)
        upload_slot_acquired = False
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

            if settings.rate_limit_enabled and not settings.is_development:
                retry_after = _check_rate_limit(user_key)
                if retry_after is not None:
                    response = JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Rate limit exceeded."},
                        headers={"Retry-After": str(retry_after)},
                    )
                    return _finalize_response(
                        request=request,
                        response=response,
                        started_at=started_at,
                        correlation_id=correlation_id,
                    )

            if request.url.path in _UPLOAD_PATHS and not settings.is_development:
                if not _acquire_upload_slot(user_key):
                    response = JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Too many simultaneous upload requests."},
                    )
                    return _finalize_response(
                        request=request,
                        response=response,
                        started_at=started_at,
                        correlation_id=correlation_id,
                    )
                upload_slot_acquired = True

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
            if upload_slot_acquired:
                _release_upload_slot(user_key)
            IN_FLIGHT_REQUESTS.dec()

        return _finalize_response(
            request=request,
            response=response,
            started_at=started_at,
            correlation_id=correlation_id,
        )


def _request_key(request: Request) -> str:
    trusted_identity = request.headers.get(settings.trusted_identity_header)
    if trusted_identity:
        return trusted_identity
    if request.client and request.client.host:
        return request.client.host
    return "anonymous"


def _check_rate_limit(key: Hashable) -> int | None:
    now = time()
    with _rate_limit_lock:
        window = _request_windows[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= settings.requests_per_minute:
            retry_after = max(1, int(60 - (now - window[0])))
            return retry_after
        window.append(now)
    return None


def _acquire_upload_slot(key: Hashable) -> bool:
    with _in_flight_lock:
        if _in_flight_uploads[key] >= settings.concurrent_upload_limit:
            return False
        _in_flight_uploads[key] += 1
    return True


def _release_upload_slot(key: Hashable) -> None:
    with _in_flight_lock:
        current = _in_flight_uploads.get(key, 0)
        if current <= 1:
            _in_flight_uploads.pop(key, None)
            return
        _in_flight_uploads[key] = current - 1


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
