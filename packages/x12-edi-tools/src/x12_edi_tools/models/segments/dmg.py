"""DMG demographic segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.enums import GenderCode
from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class DMGSegment(X12Segment):
    segment_id: ClassVar[str] = "DMG"
    _element_map: ClassVar[ElementMap] = {
        1: "date_time_period_format_qualifier",
        2: "date_time_period",
        3: "gender_code",
    }

    date_time_period_format_qualifier: str = Field(min_length=1)
    date_time_period: str = Field(min_length=1)
    gender_code: GenderCode | None = None
