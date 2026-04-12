"""N3 address information segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class N3Segment(X12Segment):
    segment_id: ClassVar[str] = "N3"
    _element_map: ClassVar[ElementMap] = {
        1: "address_information_1",
        2: "address_information_2",
    }

    address_information_1: str = Field(min_length=1)
    address_information_2: str | None = None
