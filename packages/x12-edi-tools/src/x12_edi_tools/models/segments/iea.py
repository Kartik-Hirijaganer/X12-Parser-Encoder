"""IEA interchange trailer segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class IEASegment(X12Segment):
    segment_id: ClassVar[str] = "IEA"
    _element_map: ClassVar[ElementMap] = {
        1: "number_of_included_functional_groups",
        2: "interchange_control_number",
    }

    number_of_included_functional_groups: int = Field(ge=1)
    interchange_control_number: str = Field(min_length=9, max_length=9)
