"""Schemas for 270 generation endpoints."""

from __future__ import annotations

from typing import Any, Self

from pydantic import Field, model_validator
from pydantic_core import PydanticCustomError

from app.schemas.base import ApiModel
from app.schemas.common import (
    CONTROL_NUMBER_REQUIRED_MESSAGE,
    ApiSubmitterConfig,
    ArchiveEntry,
    ControlNumbers,
    RowError,
)


class GenerateRequest(ApiModel):
    config: ApiSubmitterConfig
    patients: list[dict[str, Any]] = Field(min_length=1)
    profile: str = "dc_medicaid"

    @model_validator(mode="after")
    def require_control_number_starts(self) -> Self:
        if (
            self.config.isa_control_number_start is None
            or self.config.gs_control_number_start is None
        ):
            raise PydanticCustomError(
                "control_number_starts_required",
                CONTROL_NUMBER_REQUIRED_MESSAGE,
            )
        return self


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
