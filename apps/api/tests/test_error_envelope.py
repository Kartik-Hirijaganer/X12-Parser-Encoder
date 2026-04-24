from __future__ import annotations

from app.core.errors import register_exception_handlers
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def _client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/http-error")
    def http_error() -> None:
        raise HTTPException(
            status_code=400,
            detail={"message": "Bad upload.", "missing_columns": ["last_name"]},
        )

    @app.post("/validation-error")
    def validation_error(payload: dict[str, str]) -> dict[str, str]:
        return payload

    @app.get("/unhandled-error")
    def unhandled_error() -> None:
        raise RuntimeError("boom")

    return TestClient(app, raise_server_exceptions=False)


def test_http_exception_uses_public_error_envelope() -> None:
    response = _client().get("/http-error", headers={"X-Correlation-ID": "req-123"})

    assert response.status_code == 400
    assert response.json() == {
        "code": "BAD_REQUEST",
        "message": "Bad upload.",
        "details": {"missingColumns": ["last_name"]},
        "requestId": "req-123",
    }
    assert response.headers["X-Correlation-ID"] == "req-123"


def test_request_validation_error_uses_public_error_envelope() -> None:
    response = _client().post("/validation-error", json=["not", "an", "object"])

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["message"] == "Request validation failed."
    assert payload["details"]["errors"]
    assert payload["requestId"]


def test_unhandled_exception_uses_public_error_envelope() -> None:
    response = _client().get("/unhandled-error")

    assert response.status_code == 500
    payload = response.json()
    assert payload["code"] == "INTERNAL_SERVER_ERROR"
    assert payload["message"] == "Internal server error."
    assert payload["details"] == {}
    assert payload["requestId"]
