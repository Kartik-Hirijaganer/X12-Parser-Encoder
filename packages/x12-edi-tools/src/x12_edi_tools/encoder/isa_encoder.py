"""Fixed-width ISA segment encoding."""

from __future__ import annotations

from typing import Final

from x12_edi_tools.common.delimiters import Delimiters
from x12_edi_tools.exceptions import X12EncodeError
from x12_edi_tools.models.segments import ISASegment

ISA_ELEMENT_WIDTHS: Final[tuple[int, ...]] = (
    2,
    10,
    2,
    10,
    2,
    15,
    2,
    15,
    6,
    4,
    1,
    5,
    9,
    1,
    1,
    1,
)
NUMERIC_ELEMENT_POSITIONS: Final[frozenset[int]] = frozenset({1, 3, 9, 10, 12, 13, 14})


def encode_isa(
    isa: ISASegment,
    *,
    delimiters: Delimiters,
) -> str:
    """Encode an ISA segment to its required 106-character wire format."""

    values = (
        isa.authorization_information_qualifier,
        isa.authorization_information,
        isa.security_information_qualifier,
        isa.security_information,
        isa.sender_id_qualifier,
        isa.sender_id,
        isa.receiver_id_qualifier,
        isa.receiver_id,
        isa.interchange_date,
        isa.interchange_time,
        delimiters.repetition,
        isa.control_version_number,
        isa.interchange_control_number,
        str(isa.acknowledgment_requested),
        str(isa.usage_indicator),
        delimiters.sub_element,
    )

    encoded = ["ISA"]
    for position, (value, width) in enumerate(
        zip(values, ISA_ELEMENT_WIDTHS, strict=True),
        start=1,
    ):
        encoded.append(delimiters.element)
        encoded.append(
            _pad_element(
                value,
                width=width,
                numeric=position in NUMERIC_ELEMENT_POSITIONS,
            )
        )
    encoded.append(delimiters.segment)

    isa_text = "".join(encoded)
    if len(isa_text) != 106:
        raise X12EncodeError(
            f"Encoded ISA segment must be exactly 106 characters, got {len(isa_text)}"
        )
    return isa_text


def _pad_element(value: str, *, width: int, numeric: bool) -> str:
    if len(value) > width:
        raise X12EncodeError(f"ISA element value '{value}' exceeds fixed width {width}")
    pad = "0" if numeric else " "
    return value.rjust(width, pad) if numeric else value.ljust(width, pad)
