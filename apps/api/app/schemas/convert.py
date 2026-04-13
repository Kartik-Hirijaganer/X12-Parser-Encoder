"""Schemas for template conversion endpoints."""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.common import Correction, PatientRecord, RowError, WarningMessage


class ConvertResponse(ApiModel):
    filename: str
    file_type: str
    record_count: int
    warnings: list[WarningMessage] = Field(default_factory=list)
    corrections: list[Correction] = Field(default_factory=list)
    patients: list[PatientRecord] = Field(default_factory=list)
    errors: list[RowError] = Field(default_factory=list)
