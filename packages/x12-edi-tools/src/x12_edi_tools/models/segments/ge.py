"""GE functional group trailer segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class GESegment(X12Segment):
    segment_id: ClassVar[str] = "GE"
    _element_map: ClassVar[ElementMap] = {
        1: "number_of_transaction_sets_included",
        2: "group_control_number",
    }

    number_of_transaction_sets_included: int = Field(ge=1)
    group_control_number: str = Field(min_length=1)
