"""Tokenization for delimiter-aware X12 parsing."""

from __future__ import annotations

from x12_edi_tools.common.delimiters import Delimiters
from x12_edi_tools.common.types import SegmentToken
from x12_edi_tools.exceptions import X12ParseError


def tokenize(
    raw: str,
    delimiters: Delimiters,
    *,
    start_position: int = 0,
) -> list[SegmentToken]:
    """Split raw X12 content into positional segment tokens."""

    tokens: list[SegmentToken] = []
    cursor = 0
    raw_length = len(raw)

    while cursor < raw_length:
        while cursor < raw_length and raw[cursor].isspace():
            cursor += 1

        if cursor >= raw_length:
            break

        segment_start = cursor
        segment_end = raw.find(delimiters.segment, cursor)
        if segment_end == -1:
            raise X12ParseError(
                f"Segment starting at position {start_position + segment_start} is missing a "
                "segment terminator"
            )

        raw_segment = raw[segment_start:segment_end].rstrip("\r\n")
        cursor = segment_end + 1

        if not raw_segment:
            continue

        parts = raw_segment.split(delimiters.element)
        segment_id = parts[0]
        if not segment_id:
            raise X12ParseError(
                f"Encountered an empty segment identifier at position "
                f"{start_position + segment_start}"
            )

        tokens.append(
            SegmentToken(
                segment_id=segment_id,
                elements=tuple(parts[1:]),
                position=start_position + segment_start,
            )
        )

    return tokens
