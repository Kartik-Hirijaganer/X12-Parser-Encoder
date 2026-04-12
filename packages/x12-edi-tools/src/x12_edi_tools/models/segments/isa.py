"""ISA envelope segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field, field_validator

from x12_edi_tools.common.enums import AcknowledgmentRequested, UsageIndicator
from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class ISASegment(X12Segment):
    """Fixed-width ISA segment with strict element widths."""

    segment_id: ClassVar[str] = "ISA"
    _element_map: ClassVar[ElementMap] = {
        1: "authorization_information_qualifier",
        2: "authorization_information",
        3: "security_information_qualifier",
        4: "security_information",
        5: "sender_id_qualifier",
        6: "sender_id",
        7: "receiver_id_qualifier",
        8: "receiver_id",
        9: "interchange_date",
        10: "interchange_time",
        11: "repetition_separator",
        12: "control_version_number",
        13: "interchange_control_number",
        14: "acknowledgment_requested",
        15: "usage_indicator",
        16: "component_element_separator",
    }

    authorization_information_qualifier: str = Field(min_length=2, max_length=2)
    authorization_information: str = Field(min_length=10, max_length=10)
    security_information_qualifier: str = Field(min_length=2, max_length=2)
    security_information: str = Field(min_length=10, max_length=10)
    sender_id_qualifier: str = Field(min_length=2, max_length=2)
    sender_id: str = Field(min_length=15, max_length=15)
    receiver_id_qualifier: str = Field(min_length=2, max_length=2)
    receiver_id: str = Field(min_length=15, max_length=15)
    interchange_date: str = Field(min_length=6, max_length=6)
    interchange_time: str = Field(min_length=4, max_length=4)
    repetition_separator: str = Field(min_length=1, max_length=1)
    control_version_number: str = Field(min_length=5, max_length=5)
    interchange_control_number: str = Field(min_length=9, max_length=9)
    acknowledgment_requested: AcknowledgmentRequested
    usage_indicator: UsageIndicator
    component_element_separator: str = Field(min_length=1, max_length=1)

    @field_validator("interchange_date", "interchange_time", "interchange_control_number")
    @classmethod
    def validate_numeric_elements(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("ISA numeric elements must contain only digits")
        return value
