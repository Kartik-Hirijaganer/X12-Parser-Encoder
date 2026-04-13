from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_single_container_app_serves_frontend_and_api(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)

    (dist_dir / "index.html").write_text(
        "<!doctype html><html><body><div id='root'>HomePage</div></body></html>",
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text("console.log('frontend-ok')", encoding="utf-8")

    monkeypatch.setattr(settings, "frontend_dist_dir", dist_dir)
    monkeypatch.setattr(settings, "serve_frontend", True)

    with TestClient(create_app()) as client:
        root_response = client.get("/")
        assert root_response.status_code == 200
        assert "HomePage" in root_response.text

        route_response = client.get("/dashboard")
        assert route_response.status_code == 200
        assert "HomePage" in route_response.text

        asset_response = client.get("/assets/app.js")
        assert asset_response.status_code == 200
        assert "frontend-ok" in asset_response.text

        api_response = client.get("/api/v1/health")
        assert api_response.status_code == 200
        assert api_response.json()["status"] == "ok"
