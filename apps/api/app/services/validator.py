"""X12 validation services."""

from __future__ import annotations

import string
from dataclasses import asdict

from fastapi import HTTPException, status
from x12_edi_tools import parse, validate
from x12_edi_tools.exceptions import TransactionParseError, X12ParseError
from x12_edi_tools.parser import ParseResult
from x12_edi_tools.parser.isa_parser import detect_delimiters

from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import observe_segment_count
from app.schemas.common import ValidationIssue
from app.schemas.validate import ValidateResponse, ValidationSummary
from app.services.validation_projector import project_patient_rows

_SAFE_DELIMITER_CHARS = set(string.punctuation)
logger = get_logger(__name__)


def validate_document(
    *,
    filename: str,
    raw_x12: str,
    profile: str = "dc_medicaid",
    correlation_id: str | None = None,
    metrics_path: str = "/api/v1/validate",
) -> ValidateResponse:
    """Validate a raw X12 payload and return API response data."""

    harden_x12_payload(raw_x12)
    parse_result = _parse_with_partial_collection(raw_x12, correlation_id=correlation_id)
    validation_result = validate(
        parse_result.interchange,
        levels={1, 2, 3, 4, 5},
        profile=profile,
        correlation_id=correlation_id,
    )

    issues = [ValidationIssue(**asdict(issue)) for issue in validation_result.issues]
    issues.extend(_parse_error_issue(error) for error in parse_result.errors)

    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    patients = project_patient_rows(parse_result.interchange, issues)
    summary = ValidationSummary(
        total_patients=len(patients),
        valid_patients=sum(1 for patient in patients if patient.status == "valid"),
        invalid_patients=sum(1 for patient in patients if patient.status == "invalid"),
    )
    observe_segment_count(
        path=metrics_path,
        operation="validated_segments",
        count=raw_x12.count(parse_result.interchange.delimiters.segment),
    )
    response = ValidateResponse(
        filename=filename,
        is_valid=error_count == 0,
        error_count=error_count,
        warning_count=warning_count,
        issues=issues,
        patients=patients,
        summary=summary,
    )
    logger.info(
        "validate_document_completed",
        extra={
            "correlation_id": correlation_id,
            "path": metrics_path,
            "issue_count": len(issues),
            "error_count": error_count,
            "warning_count": warning_count,
        },
    )
    return response


def harden_x12_payload(raw_x12: str) -> None:
    """Reject oversized or pathological X12 input before full parsing."""

    if len(raw_x12) > settings.max_x12_payload_characters:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"message": "Raw X12 payload exceeds the configured size limit."},
        )

    disallowed = [char for char in raw_x12 if ord(char) < 32 and char not in "\r\n\t"]
    if disallowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Raw X12 payload contains unsupported control characters."},
        )

    try:
        delimiters = detect_delimiters(raw_x12)
    except X12ParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(exc)},
        ) from exc

    for delimiter_name, delimiter in (
        ("element", delimiters.element),
        ("segment", delimiters.segment),
        ("sub-element", delimiters.sub_element),
        ("repetition", delimiters.repetition),
    ):
        if delimiter not in _SAFE_DELIMITER_CHARS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": f"Unsupported {delimiter_name} delimiter '{delimiter}'."},
            )

    segments = [segment for segment in raw_x12.split(delimiters.segment) if segment.strip()]
    if len(segments) > settings.max_segment_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Segment count exceeds the configured safety limit."},
        )

    for segment in segments:
        if segment.count(delimiters.element) + 1 > settings.max_elements_per_segment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Element count exceeds the configured safety limit."},
            )


def _parse_with_partial_collection(
    raw_x12: str,
    *,
    correlation_id: str | None,
) -> ParseResult:
    try:
        return parse(raw_x12, strict=False, on_error="collect", correlation_id=correlation_id)
    except X12ParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(exc)},
        ) from exc


def _parse_error_issue(error: TransactionParseError) -> ValidationIssue:
    return ValidationIssue(
        severity="error",
        level="parse",
        code=error.error,
        message=error.message,
        location=f"segment_position:{error.segment_position}",
        segment_id=error.segment_id,
        suggestion=error.suggestion,
        transaction_index=error.transaction_index,
        transaction_control_number=error.st_control_number,
    )
