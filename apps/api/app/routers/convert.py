"""Template conversion endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.core.metrics import observe_record_count
from app.schemas.common import ApiSubmitterConfig
from app.schemas.convert import ConvertResponse
from app.services.patients import (
    normalize_patient_rows,
    parse_tabular_bytes,
    validate_template_headers,
)
from app.services.uploads import parse_model_json, read_upload_file

router = APIRouter(tags=["convert"])


@router.post("/convert", response_model=ConvertResponse)
async def convert_upload(
    request: Request,
    file: Annotated[UploadFile, File()],
    config: Annotated[str | None, Form()] = None,
) -> ConvertResponse:
    """Convert a canonical spreadsheet or delimited file into normalized patient JSON."""

    submitter_config = parse_model_json(config, ApiSubmitterConfig)
    uploaded = await read_upload_file(
        request,
        file,
        allowed_extensions={".csv", ".tsv", ".txt", ".xlsx"},
    )
    headers, rows = parse_tabular_bytes(uploaded.content, uploaded.extension)
    if not headers and not rows:
        return ConvertResponse(
            filename=uploaded.filename,
            file_type=uploaded.extension.lstrip("."),
            record_count=0,
        )

    header_warnings = validate_template_headers(headers)
    normalized = normalize_patient_rows(
        rows,
        default_service_type_code=(
            submitter_config.default_service_type_code if submitter_config else "30"
        ),
        default_service_date=submitter_config.default_service_date if submitter_config else None,
        row_offset=2,
    )
    observe_record_count(
        path=request.url.path,
        operation="normalized_patients",
        count=len(normalized.patients),
    )
    return ConvertResponse(
        filename=uploaded.filename,
        file_type=uploaded.extension.lstrip("."),
        record_count=len(normalized.patients),
        warnings=[*header_warnings, *normalized.warnings],
        corrections=normalized.corrections,
        patients=normalized.patients,
        errors=normalized.errors,
    )
