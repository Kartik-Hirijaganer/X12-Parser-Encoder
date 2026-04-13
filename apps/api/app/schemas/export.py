"""Schemas for export endpoints."""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.common import EligibilityResult, EligibilitySummary


class ExportWorkbookRequest(ApiModel):
    filename: str | None = None
    payer_name: str | None = None
    summary: EligibilitySummary
    results: list[EligibilityResult] = Field(default_factory=list)
