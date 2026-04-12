"""AAA request validation segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import field_validator

from x12_edi_tools.common.enums import AAARejectReasonCode
from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class AAASegment(X12Segment):
    segment_id: ClassVar[str] = "AAA"
    _element_map: ClassVar[ElementMap] = {
        1: "response_code",
        2: "agency_qualifier_code",
        3: "reject_reason_code",
        4: "follow_up_action_code",
    }

    response_code: str
    agency_qualifier_code: str | None = None
    reject_reason_code: AAARejectReasonCode
    follow_up_action_code: str | None = None

    @field_validator("response_code")
    @classmethod
    def validate_response_code(cls, value: str) -> str:
        if value not in {"Y", "N"}:
            raise ValueError("response_code must be 'Y' or 'N'")
        return value
