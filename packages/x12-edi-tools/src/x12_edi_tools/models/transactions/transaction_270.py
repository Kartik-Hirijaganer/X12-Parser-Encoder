"""270 transaction model."""

from __future__ import annotations

from pydantic import Field

from x12_edi_tools.models.base import GenericSegment, X12BaseModel
from x12_edi_tools.models.loops import Loop2000A_270
from x12_edi_tools.models.segments import BHTSegment, SESegment, STSegment


class Transaction270(X12BaseModel):
    """Typed 270 eligibility inquiry transaction."""

    st: STSegment
    bht: BHTSegment
    loop_2000a: Loop2000A_270
    se: SESegment
    generic_segments: list[GenericSegment] = Field(default_factory=list)
