"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import register_middleware

configure_logging()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    register_middleware(app)

    @app.get("/healthz")
    async def healthcheck() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": "0.1.0",
        }

    return app


app = create_app()
