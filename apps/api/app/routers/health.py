"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.health import HealthResponse
from app.services.health import deep_health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Run the deep phase-5 health check."""

    return deep_health(correlation_id=request.state.correlation_id)
