"""2110C loop models."""

from __future__ import annotations

from pydantic import Field

from x12_edi_tools.models.base import X12BaseModel
from x12_edi_tools.models.loops.loop_2120c_271 import Loop2120C_271
from x12_edi_tools.models.segments import (
    AAASegment,
    DTPSegment,
    EBSegment,
    EQSegment,
    LESegment,
    LSSegment,
    REFSegment,
)


class Loop2110C_270(X12BaseModel):
    """270 subscriber eligibility inquiry loop."""

    eq_segments: list[EQSegment] = Field(default_factory=list)
    dtp_segments: list[DTPSegment] = Field(default_factory=list)
    ref_segments: list[REFSegment] = Field(default_factory=list)


class Loop2110C_271(X12BaseModel):
    """271 subscriber eligibility response loop."""

    eb_segments: list[EBSegment] = Field(default_factory=list)
    aaa_segments: list[AAASegment] = Field(default_factory=list)
    ref_segments: list[REFSegment] = Field(default_factory=list)
    dtp_segments: list[DTPSegment] = Field(default_factory=list)
    loop_2120c: list[Loop2120C_271] = Field(default_factory=list)
    ls_segment: LSSegment | None = None
    le_segment: LESegment | None = None
