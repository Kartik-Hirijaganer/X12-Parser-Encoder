"""Schemas for 271 parsing endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.common import EligibilityResult, EligibilitySummary


class ParserIssue(ApiModel):
    transaction_index: int | None = None
    transaction_control_number: str | None = None
    segment_id: str | None = None
    location: str | None = None
    message: str
    severity: Literal["error", "warning"] = "error"


class ParseResponse(ApiModel):
    filename: str
    source_transaction_count: int
    parsed_result_count: int
    parser_issue_count: int
    parser_issues: list[ParserIssue] = Field(default_factory=list)
    transaction_count: int
    summary: EligibilitySummary
    payer_name: str | None = None
    results: list[EligibilityResult] = Field(default_factory=list)
