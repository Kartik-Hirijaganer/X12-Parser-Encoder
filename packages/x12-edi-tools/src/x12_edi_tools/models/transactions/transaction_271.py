"""271 transaction model."""

from __future__ import annotations

from x12_edi_tools.models.base import X12BaseModel
from x12_edi_tools.models.loops import Loop2000A_271
from x12_edi_tools.models.segments import BHTSegment, SESegment, STSegment


class Transaction271(X12BaseModel):
    """Typed 271 eligibility response transaction."""

    st: STSegment
    bht: BHTSegment
    loop_2000a: Loop2000A_271
    se: SESegment
