"""2100C loop models."""

from __future__ import annotations

from pydantic import Field

from x12_edi_tools.models.base import X12BaseModel
from x12_edi_tools.models.segments import (
    AAASegment,
    DMGSegment,
    DTPSegment,
    N3Segment,
    N4Segment,
    NM1Segment,
    REFSegment,
)


class Loop2100C_270(X12BaseModel):
    """270 subscriber name loop."""

    nm1: NM1Segment
    dmg: DMGSegment | None = None
    ref_segments: list[REFSegment] = Field(default_factory=list)
    dtp_segments: list[DTPSegment] = Field(default_factory=list)


class Loop2100C_271(X12BaseModel):
    """271 subscriber name loop."""

    nm1: NM1Segment
    dmg: DMGSegment | None = None
    n3: N3Segment | None = None
    n4: N4Segment | None = None
    aaa_segments: list[AAASegment] = Field(default_factory=list)
    ref_segments: list[REFSegment] = Field(default_factory=list)
