from __future__ import annotations

import json
import logging
import tempfile

import pytest
from app.core import middleware as middleware_module
from app.core.config import settings
from fastapi.testclient import TestClient

from tests.helpers import build_xlsx_bytes


def test_pipeline_happy_path_and_invalid_rows(
    client: TestClient,
    config_payload: dict[str, object],
) -> None:
    valid_workbook = build_xlsx_bytes(
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
    invalid_workbook = build_xlsx_bytes(
        [
            "last_name",
            "first_name",
            "date_of_birth",
            "gender",
            "member_id",
            "service_type_code",
            "service_date",
        ],
        [["SMITH", "JOHN", "bad-date", "M", "12345678", "30", "20260412"]],
    )

    success = client.post(
        "/api/v1/pipeline",
        files={
            "file": (
                "patients.xlsx",
                valid_workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"config": json.dumps(config_payload)},
    )
    failure = client.post(
        "/api/v1/pipeline",
        files={
            "file": (
                "patients.xlsx",
                invalid_workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"config": json.dumps(config_payload)},
    )

    assert success.status_code == 200
    assert success.json()["x12_content"].startswith("ISA*")
    assert success.json()["validation_result"]["is_valid"] is True
    assert failure.status_code == 200
    assert failure.json()["x12_content"] is None
    assert failure.json()["errors"]


def test_auth_boundary_and_rate_limit_production_only(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    middleware_module._request_windows.clear()
    monkeypatch.setattr(settings, "auth_boundary_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "environment", "production")

    unauthorized = client.get("/api/v1/health")
    assert unauthorized.status_code == 401

    headers = {settings.trusted_identity_header: "user-1"}
    for _ in range(settings.requests_per_minute):
        response = client.get("/api/v1/health", headers=headers)
        assert response.status_code == 200

    rate_limited = client.get("/api/v1/health", headers=headers)
    assert rate_limited.status_code == 429


def test_logs_are_phi_safe_and_no_temp_files_created(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    config_payload: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
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
        [["Smith", "John", "01/15/1985", "M", "12345678", "", "20260412"]],
    )
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    caplog.set_level(logging.INFO)

    response = client.post(
        "/api/v1/convert",
        files={
            "file": (
                "john_smith_12345678.xlsx",
                workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"config": json.dumps(config_payload)},
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"]
    assert "john_smith_12345678.xlsx" not in caplog.text
    assert "Smith" not in caplog.text
    assert "12345678" not in caplog.text
    assert list(tmp_path.iterdir()) == []


def test_pathological_input_is_rejected_before_full_parse(client: TestClient) -> None:
    pathological = (
        "ISA*00*          *00*          *ZZ*ACMEHOMEHLTH   "
        "*ZZ*DCMEDICAID     *260412*1200*^*00501*000000001*0*T*:~"
        "GS*HS*ACMEHOMEHLTH*DCMEDICAID*20260412*1200*1*X*005010X279A1~"
        + ("REF*" + "*".join(str(index) for index in range(200)) + "~")
    )
    response = client.post(
        "/api/v1/validate",
        files={"file": ("pathological.x12", pathological.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 400
