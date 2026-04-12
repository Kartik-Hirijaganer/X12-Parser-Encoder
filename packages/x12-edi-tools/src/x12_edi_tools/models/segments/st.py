"""ST transaction set header segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class STSegment(X12Segment):
    segment_id: ClassVar[str] = "ST"
    _element_map: ClassVar[ElementMap] = {
        1: "transaction_set_identifier_code",
        2: "transaction_set_control_number",
        3: "implementation_convention_reference",
    }

    transaction_set_identifier_code: str = Field(min_length=3, max_length=3)
    transaction_set_control_number: str = Field(min_length=1)
    implementation_convention_reference: str | None = None
