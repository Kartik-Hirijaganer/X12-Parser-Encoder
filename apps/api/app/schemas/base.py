"""Shared API schema helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Strict base model for API contracts."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
