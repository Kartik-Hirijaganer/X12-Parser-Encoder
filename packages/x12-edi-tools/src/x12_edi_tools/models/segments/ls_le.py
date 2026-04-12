"""Loop start/end segments."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class LSSegment(X12Segment):
    segment_id: ClassVar[str] = "LS"
    _element_map: ClassVar[ElementMap] = {
        1: "loop_identifier_code",
    }

    loop_identifier_code: str = Field(min_length=1)


class LESegment(X12Segment):
    segment_id: ClassVar[str] = "LE"
    _element_map: ClassVar[ElementMap] = {
        1: "loop_identifier_code",
    }

    loop_identifier_code: str = Field(min_length=1)
