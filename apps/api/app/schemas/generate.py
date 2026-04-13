"""Schemas for 270 generation endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.common import ApiSubmitterConfig, ArchiveEntry, ControlNumbers, RowError


class GenerateRequest(ApiModel):
    config: ApiSubmitterConfig
    patients: list[dict[str, Any]] = Field(min_length=1)
    profile: str = "dc_medicaid"


class GenerateResponse(ApiModel):
    x12_content: str | None = None
    zip_content_base64: str | None = None
    download_file_name: str | None = None
    batch_summary_text: str | None = None
    batch_summary_file_name: str | None = None
    transaction_count: int
    segment_count: int
    file_size_bytes: int
    split_count: int
    control_numbers: ControlNumbers
    archive_entries: list[ArchiveEntry] = Field(default_factory=list)
    manifest: dict[str, Any] | None = None
    errors: list[RowError] = Field(default_factory=list)
    partial: bool = False
