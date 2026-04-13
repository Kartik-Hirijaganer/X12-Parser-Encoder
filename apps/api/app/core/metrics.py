"""Prometheus metrics helpers for API observability."""

from __future__ import annotations

from typing import Final

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

_REQUEST_LATENCY_BUCKETS: Final[tuple[float, ...]] = (
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.0,
    3.0,
    5.0,
    8.0,
    13.0,
)
_UPLOAD_SIZE_BUCKETS: Final[tuple[float, ...]] = (
    1024,
    10 * 1024,
    100 * 1024,
    512 * 1024,
    1024 * 1024,
    2 * 1024 * 1024,
    5 * 1024 * 1024,
    10 * 1024 * 1024,
)
_COUNT_BUCKETS: Final[tuple[float, ...]] = (
    1,
    5,
    10,
    25,
    50,
    100,
    250,
    500,
    1000,
    2500,
    5000,
    10000,
    20000,
)

REQUEST_LATENCY_SECONDS = Histogram(
    "x12_api_request_latency_seconds",
    "End-to-end request latency in seconds by method, route, and status code.",
    labelnames=("method", "path", "status_code"),
    buckets=_REQUEST_LATENCY_BUCKETS,
)
REQUESTS_TOTAL = Counter(
    "x12_api_requests_total",
    "Total API requests by method, route, and status code.",
    labelnames=("method", "path", "status_code"),
)
REQUEST_ERRORS_TOTAL = Counter(
    "x12_api_request_errors_total",
    "Total API error responses by method, route, and normalized error code.",
    labelnames=("method", "path", "error_code"),
)
IN_FLIGHT_REQUESTS = Gauge(
    "x12_api_in_flight_requests",
    "Current number of in-flight API requests.",
)
UPLOAD_SIZE_BYTES = Histogram(
    "x12_api_upload_size_bytes",
    "Uploaded file sizes in bytes by route and file type.",
    labelnames=("path", "file_type"),
    buckets=_UPLOAD_SIZE_BUCKETS,
)
RECORD_COUNT = Histogram(
    "x12_api_record_count",
    "Record or row counts observed during request processing.",
    labelnames=("path", "operation"),
    buckets=_COUNT_BUCKETS,
)
SEGMENT_COUNT = Histogram(
    "x12_api_segment_count",
    "X12 segment counts observed during request processing.",
    labelnames=("path", "operation"),
    buckets=_COUNT_BUCKETS,
)


def metric_path_for_request(request: Request) -> str:
    """Return a low-cardinality route label for a request."""

    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path
    return request.url.path


def record_request(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_seconds: float,
    error_code: str | None = None,
) -> None:
    """Record request counters and latency histograms."""

    status_label = str(status_code)
    REQUESTS_TOTAL.labels(method=method, path=path, status_code=status_label).inc()
    REQUEST_LATENCY_SECONDS.labels(
        method=method,
        path=path,
        status_code=status_label,
    ).observe(duration_seconds)
    if status_code >= 400:
        REQUEST_ERRORS_TOTAL.labels(
            method=method,
            path=path,
            error_code=error_code or f"http_{status_code}",
        ).inc()


def observe_upload_size(*, path: str, file_type: str, byte_size: int) -> None:
    """Record uploaded payload sizes without logging filenames."""

    UPLOAD_SIZE_BYTES.labels(path=path, file_type=file_type or "unknown").observe(byte_size)


def observe_record_count(*, path: str, operation: str, count: int) -> None:
    """Record row or record counts for endpoint-level observability."""

    RECORD_COUNT.labels(path=path, operation=operation).observe(count)


def observe_segment_count(*, path: str, operation: str, count: int) -> None:
    """Record X12 segment counts for endpoint-level observability."""

    SEGMENT_COUNT.labels(path=path, operation=operation).observe(count)


def render_metrics_response() -> Response:
    """Return the current Prometheus exposition payload."""

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def metrics_available() -> bool:
    """Return whether the registry can be rendered successfully."""

    return bool(generate_latest())
