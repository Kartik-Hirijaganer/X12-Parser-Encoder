"""Delimiter primitives for X12 interchange handling."""

from pydantic import BaseModel, Field


class Delimiters(BaseModel):
    element_separator: str = Field(default="*", min_length=1, max_length=1)
    repetition_separator: str = Field(default="^", min_length=1, max_length=1)
    component_separator: str = Field(default=":", min_length=1, max_length=1)
    segment_terminator: str = Field(default="~", min_length=1, max_length=1)
