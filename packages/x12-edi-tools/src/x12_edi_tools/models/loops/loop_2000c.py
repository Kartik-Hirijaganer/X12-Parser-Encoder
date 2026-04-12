"""2000C loop models."""

from __future__ import annotations

from pydantic import Field

from x12_edi_tools.models.base import X12BaseModel
from x12_edi_tools.models.loops.loop_2100c import Loop2100C_270, Loop2100C_271
from x12_edi_tools.models.loops.loop_2110c import Loop2110C_270, Loop2110C_271
from x12_edi_tools.models.segments import AAASegment, HLSegment, TRNSegment


class Loop2000C_270(X12BaseModel):
    """270 subscriber level loop."""

    hl: HLSegment
    trn: TRNSegment | None = None
    loop_2100c: Loop2100C_270
    loop_2110c: list[Loop2110C_270] = Field(default_factory=list)


class Loop2000C_271(X12BaseModel):
    """271 subscriber level loop."""

    hl: HLSegment
    trn: TRNSegment | None = None
    aaa_segments: list[AAASegment] = Field(default_factory=list)
    loop_2100c: Loop2100C_271
    loop_2110c: list[Loop2110C_271] = Field(default_factory=list)
