"""PER administrative communications contact segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class PERSegment(X12Segment):
    segment_id: ClassVar[str] = "PER"
    _element_map: ClassVar[ElementMap] = {
        1: "contact_function_code",
        2: "name",
        3: "communication_number_qualifier_1",
        4: "communication_number_1",
        5: "communication_number_qualifier_2",
        6: "communication_number_2",
        7: "communication_number_qualifier_3",
        8: "communication_number_3",
    }

    contact_function_code: str = Field(min_length=1)
    name: str | None = None
    communication_number_qualifier_1: str | None = None
    communication_number_1: str | None = None
    communication_number_qualifier_2: str | None = None
    communication_number_2: str | None = None
    communication_number_qualifier_3: str | None = None
    communication_number_3: str | None = None
