"""TRN trace segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class TRNSegment(X12Segment):
    segment_id: ClassVar[str] = "TRN"
    _element_map: ClassVar[ElementMap] = {
        1: "trace_type_code",
        2: "reference_identification_1",
        3: "originating_company_identifier",
        4: "reference_identification_2",
    }

    trace_type_code: str = Field(min_length=1)
    reference_identification_1: str = Field(min_length=1)
    originating_company_identifier: str | None = None
    reference_identification_2: str | None = None
