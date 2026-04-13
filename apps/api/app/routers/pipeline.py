"""End-to-end pipeline endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from pydantic import ValidationError

from app.schemas.common import ApiSubmitterConfig
from app.schemas.generate import GenerateRequest
from app.schemas.pipeline import PipelineResponse, PipelineValidationResult
from app.services.generator import generate_270_response
from app.services.patients import (
    normalize_patient_rows,
    parse_tabular_bytes,
    validate_template_headers,
)
from app.services.uploads import parse_model_json, read_upload_file
from app.services.validator import validate_document

router = APIRouter(tags=["pipeline"])


@router.post("/pipeline", response_model=PipelineResponse)
async def pipeline(
    request: Request,
    file: Annotated[UploadFile | None, File()] = None,
    config: Annotated[str | None, Form()] = None,
    profile: Annotated[str | None, Form()] = None,
) -> PipelineResponse:
    """Run convert -> generate -> validate in a single request."""

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await _json_payload(request)
    else:
        if file is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "A file upload is required for multipart pipeline requests."},
            )
        config_payload = parse_model_json(config, ApiSubmitterConfig)
        if config_payload is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "config is required for pipeline requests."},
            )
        uploaded = await read_upload_file(
            request,
            file,
            allowed_extensions={".csv", ".tsv", ".txt", ".xlsx"},
        )
        headers, rows = parse_tabular_bytes(uploaded.content, uploaded.extension)
        if headers or rows:
            header_warnings = validate_template_headers(headers)
        else:
            header_warnings = []
        normalized = normalize_patient_rows(
            rows,
            default_service_type_code=config_payload.default_service_type_code,
            default_service_date=config_payload.default_service_date,
            row_offset=2,
        )
        if not normalized.patients:
            return PipelineResponse(
                x12_content=None,
                validation_result=PipelineValidationResult(
                    is_valid=False,
                    error_count=0,
                    warning_count=0,
                    issues=[],
                ),
                transaction_count=0,
                segment_count=0,
                warnings=[*header_warnings, *normalized.warnings],
                errors=normalized.errors,
                partial=False,
            )
        payload = GenerateRequest(
            config=config_payload,
            patients=[patient.model_dump() for patient in normalized.patients],
            profile=profile or "dc_medicaid",
        )
        extra_warnings = header_warnings + normalized.warnings
        extra_errors = normalized.errors

    generated = generate_270_response(
        config=payload.config.to_library_model(),
        patients=payload.patients,
        profile_name=payload.profile,
        correlation_id=request.state.correlation_id,
        metrics_path=request.url.path,
    )
    validation_result = PipelineValidationResult(
        is_valid=False,
        error_count=0,
        warning_count=0,
        issues=[],
    )

    all_errors = list(locals().get("extra_errors", [])) + generated.errors
    warnings = list(locals().get("extra_warnings", []))

    if generated.x12_content:
        validated = validate_document(
            filename="generated.x12",
            raw_x12=generated.x12_content,
            correlation_id=request.state.correlation_id,
            metrics_path=request.url.path,
        )
        validation_result = PipelineValidationResult(
            is_valid=validated.is_valid,
            error_count=validated.error_count,
            warning_count=validated.warning_count,
            issues=validated.issues,
        )
        x12_content = generated.x12_content if validated.is_valid else None
    else:
        x12_content = None
        if generated.split_count > 1:
            warnings.append(
                {
                    "message": (
                        "Pipeline generation split into multiple interchanges. "
                        "Use /generate for ZIP output."
                    )
                }
            )

    return PipelineResponse(
        x12_content=x12_content,
        validation_result=validation_result,
        transaction_count=generated.transaction_count,
        segment_count=generated.segment_count,
        warnings=warnings,
        errors=all_errors,
        partial=generated.partial or bool(all_errors),
    )


async def _json_payload(request: Request) -> GenerateRequest:
    try:
        raw_payload = await request.json()
        return GenerateRequest.model_validate(raw_payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc
