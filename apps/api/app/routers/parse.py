"""271 parsing endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile

from app.schemas.parse import ParseResponse
from app.services.parser import parse_271_document
from app.services.uploads import decode_text_payload, read_upload_file

router = APIRouter(tags=["parse"])


@router.post("/parse", response_model=ParseResponse)
async def parse_271(
    request: Request,
    file: Annotated[UploadFile, File()],
) -> ParseResponse:
    """Parse a raw 271 file into dashboard-friendly JSON."""

    uploaded = await read_upload_file(
        request,
        file,
        allowed_extensions={".edi", ".txt", ".x12"},
    )
    return parse_271_document(
        filename=uploaded.filename,
        raw_x12=decode_text_payload(uploaded.content),
        correlation_id=request.state.correlation_id,
        metrics_path=request.url.path,
    )
