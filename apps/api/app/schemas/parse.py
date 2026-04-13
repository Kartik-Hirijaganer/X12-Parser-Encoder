"""Schemas for 271 parsing endpoints."""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.common import EligibilityResult, EligibilitySummary


class ParseResponse(ApiModel):
    filename: str
    transaction_count: int
    summary: EligibilitySummary
    payer_name: str | None = None
    results: list[EligibilityResult] = Field(default_factory=list)
