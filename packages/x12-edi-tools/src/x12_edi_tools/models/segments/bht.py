"""BHT beginning of hierarchical transaction segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class BHTSegment(X12Segment):
    segment_id: ClassVar[str] = "BHT"
    _element_map: ClassVar[ElementMap] = {
        1: "hierarchical_structure_code",
        2: "transaction_set_purpose_code",
        3: "reference_identification",
        4: "date",
        5: "time",
    }

    hierarchical_structure_code: str = Field(min_length=4, max_length=4)
    transaction_set_purpose_code: str = Field(min_length=2, max_length=2)
    reference_identification: str = Field(min_length=1)
    date: str = Field(min_length=8, max_length=8)
    time: str = Field(min_length=4, max_length=8)
