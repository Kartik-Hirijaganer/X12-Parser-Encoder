"""Base model types for later parser and encoder phases."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class X12BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenericSegment(X12BaseModel):
    segment_id: str = Field(min_length=2)
    elements: list[str] = Field(default_factory=list)
