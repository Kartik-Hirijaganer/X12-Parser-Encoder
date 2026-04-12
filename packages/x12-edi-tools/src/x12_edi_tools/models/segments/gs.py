"""GS functional group header segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class GSSegment(X12Segment):
    segment_id: ClassVar[str] = "GS"
    _element_map: ClassVar[ElementMap] = {
        1: "functional_identifier_code",
        2: "application_sender_code",
        3: "application_receiver_code",
        4: "date",
        5: "time",
        6: "group_control_number",
        7: "responsible_agency_code",
        8: "version_release_industry_identifier_code",
    }

    functional_identifier_code: str = Field(min_length=2, max_length=2)
    application_sender_code: str = Field(min_length=1)
    application_receiver_code: str = Field(min_length=1)
    date: str = Field(min_length=8, max_length=8)
    time: str = Field(min_length=4, max_length=8)
    group_control_number: str = Field(min_length=1)
    responsible_agency_code: str = Field(min_length=1, max_length=2)
    version_release_industry_identifier_code: str = Field(min_length=1)
