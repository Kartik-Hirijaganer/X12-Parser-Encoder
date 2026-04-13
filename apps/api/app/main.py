"""FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.metrics import render_metrics_response
from app.core.middleware import register_middleware
from app.routers import api_router

configure_logging()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    register_middleware(app)
    app.include_router(api_router)

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
        }

    if settings.metrics_enabled:

        @app.get(settings.metrics_path, include_in_schema=False)
        async def metrics() -> Response:
            return render_metrics_response()

    _register_frontend(app)
    return app


def _register_frontend(app: FastAPI) -> None:
    if not settings.frontend_enabled:
        return

    dist_dir = settings.frontend_dist_dir
    index_path = dist_dir / "index.html"
    assets_dir = dist_dir / "assets"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    async def frontend_index() -> FileResponse:
        return FileResponse(index_path)

    @app.get("/{requested_path:path}", include_in_schema=False)
    async def frontend_app(requested_path: str) -> FileResponse:
        if requested_path == "api" or requested_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        asset_path = _resolve_frontend_asset(dist_dir, requested_path)
        return FileResponse(asset_path or index_path)


def _resolve_frontend_asset(dist_dir: Path, requested_path: str) -> Path | None:
    normalized = requested_path.strip("/")
    if not normalized:
        return dist_dir / "index.html"

    candidate = (dist_dir / normalized).resolve()
    try:
        candidate.relative_to(dist_dir.resolve())
    except ValueError:
        return None

    if candidate.is_file():
        return candidate
    return None


app = create_app()
