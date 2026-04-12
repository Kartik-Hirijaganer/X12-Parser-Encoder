"""2000B loop models."""

from __future__ import annotations

from pydantic import Field

from x12_edi_tools.models.base import X12BaseModel
from x12_edi_tools.models.loops.loop_2000c import Loop2000C_270, Loop2000C_271
from x12_edi_tools.models.loops.loop_2100b import Loop2100B_270, Loop2100B_271
from x12_edi_tools.models.segments import AAASegment, HLSegment


class Loop2000B_270(X12BaseModel):
    """270 information receiver level loop."""

    hl: HLSegment
    loop_2100b: Loop2100B_270 | None = None
    loop_2000c: list[Loop2000C_270] = Field(default_factory=list)


class Loop2000B_271(X12BaseModel):
    """271 information receiver level loop."""

    hl: HLSegment
    aaa_segments: list[AAASegment] = Field(default_factory=list)
    loop_2100b: Loop2100B_271 | None = None
    loop_2000c: list[Loop2000C_271] = Field(default_factory=list)
