"""2000A loop models."""

from __future__ import annotations

from pydantic import Field

from x12_edi_tools.models.base import X12BaseModel
from x12_edi_tools.models.loops.loop_2000b import Loop2000B_270, Loop2000B_271
from x12_edi_tools.models.loops.loop_2100a import Loop2100A_270, Loop2100A_271
from x12_edi_tools.models.segments import AAASegment, HLSegment


class Loop2000A_270(X12BaseModel):
    """270 information source level loop."""

    hl: HLSegment
    loop_2100a: Loop2100A_270 | None = None
    loop_2000b: list[Loop2000B_270] = Field(default_factory=list)


class Loop2000A_271(X12BaseModel):
    """271 information source level loop."""

    hl: HLSegment
    aaa_segments: list[AAASegment] = Field(default_factory=list)
    loop_2100a: Loop2100A_271 | None = None
    loop_2000b: list[Loop2000B_271] = Field(default_factory=list)
