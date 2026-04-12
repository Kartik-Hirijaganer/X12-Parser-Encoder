"""PRV provider information segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class PRVSegment(X12Segment):
    segment_id: ClassVar[str] = "PRV"
    _element_map: ClassVar[ElementMap] = {
        1: "provider_code",
        2: "reference_identification_qualifier",
        3: "reference_identification",
    }

    provider_code: str = Field(min_length=1)
    reference_identification_qualifier: str = Field(min_length=1)
    reference_identification: str = Field(min_length=1)
