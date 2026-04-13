from __future__ import annotations

import json
import logging
import re

import pytest
from fastapi.testclient import TestClient

from tests.helpers import build_xlsx_bytes, fixture_text


def test_metrics_endpoint_exposes_prometheus_series(client: TestClient) -> None:
    health = client.get("/api/v1/health")
    metrics = client.get("/metrics")

    assert health.status_code == 200
    assert metrics.status_code == 200
    assert metrics.headers["content-type"].startswith("text/plain")
    body = metrics.text
    assert "x12_api_requests_total" in body
    assert "x12_api_request_latency_seconds" in body
    assert re.search(
        r'x12_api_requests_total\{method="GET",path="/api/v1/health",status_code="200"\}\s+',
        body,
    )


def test_upload_and_record_metrics_are_recorded(
    client: TestClient,
    config_payload: dict[str, object],
) -> None:
    workbook = build_xlsx_bytes(
        [
            "last_name",
            "first_name",
            "date_of_birth",
            "gender",
            "member_id",
            "service_type_code",
            "service_date",
        ],
        [["SMITH", "JOHN", "19850115", "M", "12345678", "30", "20260412"]],
    )

    response = client.post(
        "/api/v1/convert",
        files={
            "file": (
                "patients.xlsx",
                workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"config": json.dumps(config_payload)},
    )
    metrics = client.get("/metrics")

    assert response.status_code == 200
    assert metrics.status_code == 200
    body = metrics.text
    assert "x12_api_upload_size_bytes_count" in body
    assert 'path="/api/v1/convert"' in body
    assert 'file_type="xlsx"' in body
    assert "x12_api_record_count_count" in body
    assert 'operation="normalized_patients"' in body


def test_api_request_propagates_correlation_id_into_library_logs(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    correlation_id = "trace-phase8-001"

    response = client.post(
        "/api/v1/validate",
        headers={"X-Correlation-ID": correlation_id},
        files={
            "file": (
                "valid.x12",
                fixture_text("270_realtime_single.x12").encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == correlation_id
    assert any(
        record.name.startswith("x12_edi_tools.")
        and getattr(record, "correlation_id", None) == correlation_id
        for record in caplog.records
    )
