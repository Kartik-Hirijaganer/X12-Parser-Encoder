"""2100B loop models."""

from __future__ import annotations

from pydantic import Field

from x12_edi_tools.models.base import X12BaseModel
from x12_edi_tools.models.segments import (
    N3Segment,
    N4Segment,
    NM1Segment,
    PERSegment,
    PRVSegment,
    REFSegment,
)


class Loop2100B_270(X12BaseModel):
    """270 information receiver name loop."""

    nm1: NM1Segment
    prv: PRVSegment | None = None
    per: PERSegment | None = None
    n3: N3Segment | None = None
    n4: N4Segment | None = None
    ref_segments: list[REFSegment] = Field(default_factory=list)


class Loop2100B_271(X12BaseModel):
    """271 information receiver name loop."""

    nm1: NM1Segment
    per: PERSegment | None = None
    n3: N3Segment | None = None
    n4: N4Segment | None = None
    ref_segments: list[REFSegment] = Field(default_factory=list)
