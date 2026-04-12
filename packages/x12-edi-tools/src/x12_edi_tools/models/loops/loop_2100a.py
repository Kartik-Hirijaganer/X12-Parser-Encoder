"""2100A loop models."""

from __future__ import annotations

from pydantic import Field

from x12_edi_tools.models.base import X12BaseModel
from x12_edi_tools.models.segments import AAASegment, NM1Segment, REFSegment


class Loop2100A_270(X12BaseModel):
    """270 information source name loop."""

    nm1: NM1Segment
    ref_segments: list[REFSegment] = Field(default_factory=list)


class Loop2100A_271(X12BaseModel):
    """271 information source name loop."""

    nm1: NM1Segment
    aaa_segments: list[AAASegment] = Field(default_factory=list)
    ref_segments: list[REFSegment] = Field(default_factory=list)
