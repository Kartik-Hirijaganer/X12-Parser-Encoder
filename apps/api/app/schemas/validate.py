"""Schemas for validation endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.common import ValidationIssue


class ValidationSummary(ApiModel):
    total_patients: int
    valid_patients: int
    invalid_patients: int


class PatientValidationRow(ApiModel):
    index: int
    transaction_control_number: str | None
    member_name: str
    member_id: str | None
    service_date: str | None
    status: Literal["valid", "invalid"]
    error_count: int
    warning_count: int
    issues: list[ValidationIssue] = Field(default_factory=list)


class ValidateResponse(ApiModel):
    filename: str
    is_valid: bool
    error_count: int
    warning_count: int
    issues: list[ValidationIssue] = Field(default_factory=list)
    patients: list[PatientValidationRow] = Field(default_factory=list)
    summary: ValidationSummary | None = None
