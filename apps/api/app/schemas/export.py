"""Schemas for export endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.common import EligibilityResult, EligibilitySummary
from app.schemas.parse import ParserIssue

PlanView = Literal["agency", "primary", "medicare", "all"]


class ExportWorkbookRequest(ApiModel):
    filename: str | None = None
    payer_name: str | None = None
    summary: EligibilitySummary
    results: list[EligibilityResult] = Field(default_factory=list)
    plan_view: PlanView = "agency"
    parser_issue_count: int = 0
    parser_issues: list[ParserIssue] = Field(default_factory=list)
