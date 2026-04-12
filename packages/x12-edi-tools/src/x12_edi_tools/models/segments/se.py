"""SE transaction set trailer segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class SESegment(X12Segment):
    segment_id: ClassVar[str] = "SE"
    _element_map: ClassVar[ElementMap] = {
        1: "number_of_included_segments",
        2: "transaction_set_control_number",
    }

    number_of_included_segments: int = Field(ge=1)
    transaction_set_control_number: str = Field(min_length=1)
