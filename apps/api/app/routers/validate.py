"""Validation endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.schemas.validate import ValidateResponse
from app.services.uploads import decode_text_payload, read_upload_file
from app.services.validator import validate_document

router = APIRouter(tags=["validate"])


@router.post("/validate", response_model=ValidateResponse)
async def validate_x12(
    request: Request,
    file: Annotated[UploadFile, File()],
    profile: Annotated[str, Form()] = "dc_medicaid",
) -> ValidateResponse:
    """Validate a raw X12 file against generic SNIP rules and payer rules."""

    uploaded = await read_upload_file(
        request,
        file,
        allowed_extensions={".edi", ".txt", ".x12"},
    )
    return validate_document(
        filename=uploaded.filename,
        raw_x12=decode_text_payload(uploaded.content),
        profile=profile,
        correlation_id=request.state.correlation_id,
        metrics_path=request.url.path,
    )
