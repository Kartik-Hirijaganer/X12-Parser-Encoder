"""Schemas for validation endpoints."""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.common import ValidationIssue


class ValidateResponse(ApiModel):
    filename: str
    is_valid: bool
    error_count: int
    warning_count: int
    issues: list[ValidationIssue] = Field(default_factory=list)
