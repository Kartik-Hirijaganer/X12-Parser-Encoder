from __future__ import annotations

from app.core.config import settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_cors_preflight_allows_configured_origin(monkeypatch) -> None:
    origin = (
        "http://x12-parser-encoder-web-306980977180-us-east-2.s3-website.us-east-2.amazonaws.com"
    )

    monkeypatch.setattr(settings, "cors_allowed_origins", [origin])
    monkeypatch.setattr(settings, "serve_frontend", False)

    with TestClient(create_app()) as client:
        preflight_response = client.options(
            "/api/v1/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        response = client.get("/api/v1/health", headers={"Origin": origin})

    assert preflight_response.status_code == 200
    assert preflight_response.headers["access-control-allow-origin"] == origin
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "X-Correlation-ID" in response.headers["access-control-expose-headers"]
