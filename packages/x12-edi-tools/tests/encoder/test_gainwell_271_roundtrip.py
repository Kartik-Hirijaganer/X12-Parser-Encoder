from __future__ import annotations

from pathlib import Path

import pytest

from x12_edi_tools import encode, parse
from x12_edi_tools.exceptions import X12EncodeError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_gainwell_271_redacted_fixture_round_trips_through_encode() -> None:
    parsed = parse(read_fixture("gainwell_271_redacted.edi"))

    encoded = encode(parsed.interchange)
    reparsed = parse(encoded)

    assert reparsed.interchange == parsed.interchange


def test_encode_rejects_unknown_eb01_even_though_inbound_parsing_is_tolerant() -> None:
    interchange = parse(read_fixture("271_active_response.x12")).interchange
    eb_segment = (
        interchange.functional_groups[0]
        .transactions[0]
        .loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2110c[0]
        .eb_segments[0]
    )
    eb_segment.eligibility_or_benefit_information = "Z9"

    with pytest.raises(X12EncodeError, match="EB01"):
        encode(interchange)


def test_encode_rejects_unknown_nm101_even_though_inbound_parsing_is_tolerant() -> None:
    interchange = parse(read_fixture("271_active_response.x12")).interchange
    subscriber_nm1 = (
        interchange.functional_groups[0]
        .transactions[0]
        .loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2100c.nm1
    )
    subscriber_nm1.entity_identifier_code = "ZZ"

    with pytest.raises(X12EncodeError, match="NM101"):
        encode(interchange)


def test_encode_rejects_unknown_eb03_service_type_codes() -> None:
    interchange = parse(read_fixture("271_active_response.x12")).interchange
    eb_segment = (
        interchange.functional_groups[0]
        .transactions[0]
        .loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2110c[0]
        .eb_segments[0]
    )
    eb_segment.service_type_codes = ["30", "ZZ"]
    eb_segment.service_type_code = "30"

    with pytest.raises(X12EncodeError, match="EB03"):
        encode(interchange)
