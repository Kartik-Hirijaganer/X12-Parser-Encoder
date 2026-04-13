"""Schemas for end-to-end pipeline endpoints."""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.common import RowError, ValidationIssue, WarningMessage


class PipelineValidationResult(ApiModel):
    is_valid: bool
    error_count: int
    warning_count: int
    issues: list[ValidationIssue] = Field(default_factory=list)


class PipelineResponse(ApiModel):
    x12_content: str | None = None
    validation_result: PipelineValidationResult
    transaction_count: int
    segment_count: int
    warnings: list[WarningMessage] = Field(default_factory=list)
    errors: list[RowError] = Field(default_factory=list)
    partial: bool = False
