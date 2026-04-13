"""270 generation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.generate import GenerateRequest, GenerateResponse
from app.services.generator import generate_270_response

router = APIRouter(tags=["generate"])


@router.post("/generate", response_model=GenerateResponse)
async def generate_270(request: Request, payload: GenerateRequest) -> GenerateResponse:
    """Generate one or more X12 270 payloads from patient JSON and config."""

    return generate_270_response(
        config=payload.config.to_library_model(),
        patients=payload.patients,
        profile_name=payload.profile,
        correlation_id=request.state.correlation_id,
        metrics_path=request.url.path,
    )
