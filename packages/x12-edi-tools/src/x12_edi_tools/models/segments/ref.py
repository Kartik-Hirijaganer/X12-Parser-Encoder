"""REF reference identification segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class REFSegment(X12Segment):
    segment_id: ClassVar[str] = "REF"
    _element_map: ClassVar[ElementMap] = {
        1: "reference_identification_qualifier",
        2: "reference_identification",
        3: "description",
    }

    reference_identification_qualifier: str = Field(min_length=1)
    reference_identification: str = Field(min_length=1)
    description: str | None = None
