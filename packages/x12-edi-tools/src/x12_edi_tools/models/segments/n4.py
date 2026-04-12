"""N4 geographic location segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class N4Segment(X12Segment):
    segment_id: ClassVar[str] = "N4"
    _element_map: ClassVar[ElementMap] = {
        1: "city_name",
        2: "state_or_province_code",
        3: "postal_code",
        4: "country_code",
    }

    city_name: str = Field(min_length=1)
    state_or_province_code: str | None = None
    postal_code: str | None = None
    country_code: str | None = None
