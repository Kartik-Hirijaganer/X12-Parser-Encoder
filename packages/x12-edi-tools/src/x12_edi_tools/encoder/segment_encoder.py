"""Generic X12 segment encoding helpers."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from enum import Enum
from typing import Protocol

from x12_edi_tools.common.delimiters import Delimiters
from x12_edi_tools.models.base import GenericSegment, X12Segment
from x12_edi_tools.models.segments import EBSegment


class SegmentLike(Protocol):
    """Minimal protocol for segment encoding."""

    segment_id: str

    def to_elements(self) -> Sequence[object]:
        """Return positional element values for encoding."""


def encode_segment(
    segment: X12Segment | GenericSegment | SegmentLike,
    *,
    delimiters: Delimiters,
) -> str:
    """Encode a non-ISA segment using the supplied delimiters."""

    rendered_elements = [
        _render_element(value, delimiters=delimiters) for value in segment.to_elements()
    ]
    if (
        isinstance(segment, EBSegment)
        and len(rendered_elements) >= 3
        and segment.service_type_codes
    ):
        rendered_elements[2] = delimiters.repetition.join(segment.service_type_codes)
    while rendered_elements and rendered_elements[-1] == "":
        rendered_elements.pop()

    segment_text = delimiters.element.join((segment.segment_id, *rendered_elements))
    return f"{segment_text}{delimiters.segment}"


def _render_element(value: object, *, delimiters: Delimiters) -> str:
    if value is None:
        return ""
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return delimiters.sub_element.join(
            _render_element(component, delimiters=delimiters) for component in value
        )
    return str(value)
