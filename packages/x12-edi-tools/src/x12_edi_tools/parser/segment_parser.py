"""Segment registry and token-to-model parsing."""

from __future__ import annotations

from typing import TypeAlias

from pydantic import ValidationError

from x12_edi_tools.common.types import SegmentToken
from x12_edi_tools.models.base import GenericSegment, X12Segment
from x12_edi_tools.models.segments import (
    AAASegment,
    BHTSegment,
    DMGSegment,
    DTPSegment,
    EBSegment,
    EQSegment,
    GESegment,
    GSSegment,
    HLSegment,
    IEASegment,
    LESegment,
    LSSegment,
    N3Segment,
    N4Segment,
    NM1Segment,
    PERSegment,
    PRVSegment,
    REFSegment,
    SESegment,
    STSegment,
    TRNSegment,
)
from x12_edi_tools.parser._exceptions import ParserComponentError

ParsedSegment: TypeAlias = X12Segment | GenericSegment
SegmentModelType: TypeAlias = type[X12Segment]

SEGMENT_REGISTRY: dict[str, SegmentModelType] = {
    "AAA": AAASegment,
    "BHT": BHTSegment,
    "DMG": DMGSegment,
    "DTP": DTPSegment,
    "EB": EBSegment,
    "EQ": EQSegment,
    "GE": GESegment,
    "GS": GSSegment,
    "HL": HLSegment,
    "IEA": IEASegment,
    "LE": LESegment,
    "LS": LSSegment,
    "N3": N3Segment,
    "N4": N4Segment,
    "NM1": NM1Segment,
    "PER": PERSegment,
    "PRV": PRVSegment,
    "REF": REFSegment,
    "SE": SESegment,
    "ST": STSegment,
    "TRN": TRNSegment,
}


def render_raw_segment(token: SegmentToken, *, element_separator: str) -> str:
    """Reconstruct the raw segment text from its tokenized representation."""

    if not token.elements:
        return token.segment_id
    return element_separator.join((token.segment_id, *token.elements))


def parse_segment(
    token: SegmentToken,
    *,
    strict: bool = True,
    element_separator: str = "*",
) -> ParsedSegment:
    """Parse one token into its typed segment model."""

    segment_model = SEGMENT_REGISTRY.get(token.segment_id)
    raw_segment = render_raw_segment(token, element_separator=element_separator)

    if segment_model is None:
        if strict:
            raise ParserComponentError(
                f"Unknown segment ID '{token.segment_id}'",
                error="unknown_segment",
                segment_position=token.position,
                segment_id=token.segment_id,
                raw_segment=raw_segment,
                suggestion=(
                    "Retry with strict=False to preserve unsupported segments as GenericSegment"
                ),
            )
        try:
            return GenericSegment(segment_id=token.segment_id, raw_elements=list(token.elements))
        except ValidationError as exc:
            raise ParserComponentError(
                f"Unsupported segment '{token.segment_id}' is not well formed: {exc}",
                error="malformed_unknown_segment",
                segment_position=token.position,
                segment_id=token.segment_id,
                raw_segment=raw_segment,
                suggestion="Check the segment identifier and element formatting",
            ) from exc

    try:
        return segment_model.from_elements(token.elements)
    except ValidationError as exc:
        raise ParserComponentError(
            f"Segment {token.segment_id} failed validation: {exc}",
            error="segment_validation_error",
            segment_position=token.position,
            segment_id=token.segment_id,
            raw_segment=raw_segment,
            suggestion="Check required elements and code values for this segment",
        ) from exc
