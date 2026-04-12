"""DTP date or time reference segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class DTPSegment(X12Segment):
    segment_id: ClassVar[str] = "DTP"
    _element_map: ClassVar[ElementMap] = {
        1: "date_time_qualifier",
        2: "date_time_period_format_qualifier",
        3: "date_time_period",
    }

    date_time_qualifier: str = Field(min_length=1)
    date_time_period_format_qualifier: str = Field(min_length=1)
    date_time_period: str = Field(min_length=1)
