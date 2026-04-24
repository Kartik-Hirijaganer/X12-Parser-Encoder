from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

import pytest
from app.core.config import REPO_ROOT, AppSettings, settings
from app.main import create_app
from fastapi.testclient import TestClient

from tests.helpers import fixture_text

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SHARED_NAMES_PATH = REPO_ROOT / "infra" / "shared" / "names.json"
TERRAFORM_EXAMPLE_MAIN_PATH = (
    REPO_ROOT / "infra" / "terraform" / "environments" / "example" / "main.tf"
)


def test_lambda_handler_import_and_health_round_trip() -> None:
    from app.lambda_handler import handler

    event = _load_event("function_url_health.json")
    response = handler(event, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["status"] == "ok"


def test_lambda_handler_accepts_base64_multipart_upload() -> None:
    from app.lambda_handler import handler

    shared_names = _load_shared_names()
    body, content_type = _multipart_file_body(
        field_name="file",
        filename="valid.x12",
        content=fixture_text("270_realtime_single.x12").encode("utf-8"),
        content_type="text/plain",
    )
    event = _function_url_event(
        method="POST",
        path=f"{shared_names['api_prefix']}/validate",
        headers={
            "content-type": content_type,
            "content-length": str(len(body)),
            "x-origin-verify": "current-secret",
        },
        body=base64.b64encode(body).decode("ascii"),
        is_base64_encoded=True,
    )

    response = handler(event, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["isValid"] is True


def test_origin_secret_middleware_rejects_missing_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_lambda_settings(monkeypatch)

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health", headers={"X-Correlation-ID": "test-request-id"})

    assert response.status_code == 403
    assert response.headers["X-Correlation-ID"] == "test-request-id"
    assert response.json() == {
        "code": "FORBIDDEN",
        "message": "Forbidden.",
        "details": {},
        "requestId": "test-request-id",
    }


def test_origin_secret_middleware_accepts_current_or_previous_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_lambda_settings(monkeypatch)

    with TestClient(create_app()) as client:
        current = client.get("/api/v1/health", headers={"X-Origin-Verify": "current-secret"})
        previous = client.get("/api/v1/health", headers={"X-Origin-Verify": "previous-secret"})

    assert current.status_code == 200
    assert previous.status_code == 200


def test_lambda_logging_is_phi_safe(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configure_lambda_settings(monkeypatch)
    caplog.set_level(logging.INFO)
    body, content_type = _multipart_file_body(
        field_name="file",
        filename="john_smith_12345678.x12",
        content=fixture_text("270_realtime_single.x12").encode("utf-8"),
        content_type="text/plain",
    )

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/validate",
            headers={
                "Content-Type": content_type,
                "X-Origin-Verify": "current-secret",
            },
            content=body,
        )

    captured_output = capsys.readouterr().out
    captured_logs = caplog.text

    assert response.status_code == 200
    assert "CloudWatchMetrics" in captured_output
    assert "RequestCount" in captured_output
    assert "john_smith_12345678.x12" not in captured_logs
    assert "john_smith_12345678.x12" not in captured_output
    assert "12345678" not in captured_logs
    assert "12345678" not in captured_output
    assert "ISA*" not in captured_logs
    assert "ISA*" not in captured_output


def test_lambda_app_does_not_mount_frontend_or_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>frontend</html>", encoding="utf-8")
    _configure_lambda_settings(monkeypatch)
    monkeypatch.setattr(settings, "frontend_dist_dir", dist_dir)
    monkeypatch.setattr(settings, "serve_frontend", True)
    monkeypatch.setattr(settings, "origin_secret_enabled", False)

    with TestClient(create_app()) as client:
        frontend = client.get("/")
        metrics = client.get(settings.metrics_path)
        health = client.get("/api/v1/health")

    assert frontend.status_code == 404
    assert metrics.status_code == 404
    assert health.status_code == 200


def test_shared_names_contract_matches_api_settings_and_terraform() -> None:
    shared_names = _load_shared_names()
    env_prefix = AppSettings.model_config["env_prefix"]
    app_env_fields = [
        "deployment_target",
        "origin_secret_enabled",
        "origin_secret",
        "origin_secret_previous",
        "environment",
        "serve_frontend",
        "metrics_enabled",
    ]

    assert shared_names["api_prefix"] == settings.api_v1_prefix
    assert shared_names["env_var_names"] == [
        f"{env_prefix}{field_name.upper()}" for field_name in app_env_fields
    ]

    terraform_main = TERRAFORM_EXAMPLE_MAIN_PATH.read_text(encoding="utf-8")
    assert "../../../shared/names.json" in terraform_main
    assert "zipmap(local.names.env_var_names, local.lambda_contract_environment_values)" in (
        terraform_main
    )
    for env_var_name in shared_names["env_var_names"]:
        assert env_var_name not in terraform_main


def _configure_lambda_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "deployment_target", "lambda")
    monkeypatch.setattr(settings, "origin_secret_enabled", True)
    monkeypatch.setattr(settings, "origin_secret", "current-secret")
    monkeypatch.setattr(settings, "origin_secret_previous", "previous-secret")


def _load_event(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _load_shared_names() -> dict[str, Any]:
    return json.loads(SHARED_NAMES_PATH.read_text(encoding="utf-8"))


def _function_url_event(
    *,
    method: str,
    path: str,
    headers: dict[str, str],
    body: str,
    is_base64_encoded: bool,
) -> dict[str, Any]:
    event = _load_event("function_url_health.json")
    event["rawPath"] = path
    event["headers"] = {
        **event["headers"],
        **headers,
    }
    event["requestContext"]["http"]["method"] = method
    event["requestContext"]["http"]["path"] = path
    event["body"] = body
    event["isBase64Encoded"] = is_base64_encoded
    return event


def _multipart_file_body(
    *,
    field_name: str,
    filename: str,
    content: bytes,
    content_type: str,
) -> tuple[bytes, str]:
    boundary = "----x12-lambda-boundary"
    body = b"\r\n".join(
        [
            f"--{boundary}".encode("ascii"),
            (f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"').encode(
                "ascii"
            ),
            f"Content-Type: {content_type}".encode("ascii"),
            b"",
            content,
            f"--{boundary}--".encode("ascii"),
            b"",
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"
