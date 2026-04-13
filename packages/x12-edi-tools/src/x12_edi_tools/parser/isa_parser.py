"""ISA-specific parsing and delimiter detection."""

from __future__ import annotations

from pydantic import ValidationError

from x12_edi_tools.common.delimiters import Delimiters
from x12_edi_tools.exceptions import X12ParseError
from x12_edi_tools.models.segments import ISASegment

ISA_SEGMENT_LENGTH = 106
ISA_ELEMENT_WIDTHS = (2, 10, 2, 10, 2, 15, 2, 15, 6, 4, 1, 5, 9, 1, 1, 1)


def detect_delimiters(raw: str) -> Delimiters:
    """Extract the X12 delimiters from the fixed-width ISA segment."""

    if len(raw) < ISA_SEGMENT_LENGTH:
        raise X12ParseError("Input is too short to contain a complete ISA segment")
    if not raw.startswith("ISA"):
        raise X12ParseError("Input must start with an ISA segment")

    try:
        return Delimiters(
            element=raw[3],
            repetition=raw[82],
            sub_element=raw[104],
            segment=raw[105],
        )
    except ValueError as exc:
        raise X12ParseError(f"Invalid ISA delimiters: {exc}") from exc


def parse_isa_segment(raw: str) -> tuple[ISASegment, Delimiters, int]:
    """Parse the ISA segment positionally and return the segment plus delimiters."""

    delimiters = detect_delimiters(raw)
    isa_text = raw[:ISA_SEGMENT_LENGTH]
    cursor = 4
    elements: list[str] = []

    for index, width in enumerate(ISA_ELEMENT_WIDTHS):
        element_end = cursor + width
        elements.append(isa_text[cursor:element_end])
        cursor = element_end

        expected_separator = (
            delimiters.segment if index == len(ISA_ELEMENT_WIDTHS) - 1 else delimiters.element
        )
        actual_separator = isa_text[cursor]
        if actual_separator != expected_separator:
            raise X12ParseError(
                "ISA segment is malformed at field "
                f"{index + 1}: expected '{expected_separator}', found '{actual_separator}'"
            )
        cursor += 1

    try:
        return ISASegment.from_elements(elements), delimiters, cursor
    except ValidationError as exc:
        raise X12ParseError(f"ISA segment validation failed: {exc}") from exc
