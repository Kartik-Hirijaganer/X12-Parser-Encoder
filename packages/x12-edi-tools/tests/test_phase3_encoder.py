from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from test_phase1_models import build_interchange, build_isa_segment
from x12_edi_tools import Delimiters, SubmitterConfig, encode, parse
from x12_edi_tools.encoder import encode_isa, encode_segment
from x12_edi_tools.models.base import GenericSegment

FIXTURES = Path(__file__).parent / "fixtures"
VALID_ROUNDTRIP_FIXTURES = [
    "270_batch_multi.x12",
    "270_custom_delimiters.x12",
    "270_realtime_single.x12",
    "271_active_response.x12",
    "271_ls_le_wrapper.x12",
    "271_multiple_eb_segments.x12",
    "271_rejected_subscriber.x12",
]


class _CompositeSegment:
    segment_id = "EB"

    def to_elements(self) -> Sequence[object]:
        return ["1", "", "", "", "", "", "", "", "", "", "", "", ("HC", "99213")]


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def build_submitter_config(**overrides: int) -> SubmitterConfig:
    return SubmitterConfig(
        organization_name="ACME HOME HEALTH",
        provider_npi="1234567893",
        trading_partner_id="ACMETP01",
        payer_name="DC MEDICAID",
        payer_id="DCMEDICAID",
        interchange_receiver_id="DCMEDICAID",
        **overrides,
    )


def test_encode_isa_returns_fixed_width_segment_with_padding() -> None:
    isa = build_isa_segment().model_copy(
        update={
            "sender_id": "ACME",
            "receiver_id": "DCMED",
            "interchange_control_number": "12",
        }
    )

    encoded = encode_isa(isa, delimiters=Delimiters())

    assert len(encoded) == 106
    assert encoded[35:50] == "ACME           "
    assert encoded[54:69] == "DCMED          "
    assert "*000000012*" in encoded


def test_encode_segment_trims_trailing_empty_elements() -> None:
    segment = GenericSegment(segment_id="REF", raw_elements=["EJ", "12345", "", ""])

    encoded = encode_segment(segment, delimiters=Delimiters())

    assert encoded == "REF*EJ*12345~"


def test_encode_segment_supports_composite_elements() -> None:
    encoded = encode_segment(_CompositeSegment(), delimiters=Delimiters())

    assert encoded == "EB*1************HC:99213~"


def test_encode_preserves_single_interchange_control_numbers_for_roundtrip_stability() -> None:
    parsed = parse(read_fixture("270_custom_delimiters.x12"))

    encoded = encode(parsed.interchange)
    reparsed = parse(encoded)

    assert reparsed.interchange == parsed.interchange
    assert "000000006" in encoded
    assert "|6|" in encoded


@pytest.mark.parametrize("fixture_name", VALID_ROUNDTRIP_FIXTURES)
def test_parse_encode_parse_roundtrip_matches_models(fixture_name: str) -> None:
    raw = read_fixture(fixture_name)

    parsed = parse(raw)
    encoded = encode(parsed.interchange)
    reparsed = parse(encoded)

    assert reparsed.interchange == parsed.interchange


@pytest.mark.parametrize("fixture_name", VALID_ROUNDTRIP_FIXTURES)
def test_encode_parse_encode_roundtrip_is_idempotent(fixture_name: str) -> None:
    initial = encode(parse(read_fixture(fixture_name)).interchange)
    reparsed = parse(initial)

    assert encode(reparsed.interchange) == initial


def test_roundtrip_on_unknown_segments_preserves_original_transaction_position() -> None:
    raw = (
        read_fixture("270_realtime_single.x12")
        .replace("DMG*D8*19900101*F~", "III*X*Y~DMG*D8*19900101*F~")
        .replace("SE*13*0001~", "SE*14*0001~")
    )

    parsed = parse(raw, strict=False)
    encoded = encode(parsed.interchange)
    reparsed = parse(encoded, strict=False)

    assert "NM1*IL*1*DOE*PATIENT****MI*000123450~III*X*Y~DMG*D8*19900101*F~" in encoded
    assert reparsed.interchange == parsed.interchange


def test_encode_recomputes_transaction_group_and_interchange_counts() -> None:
    interchange = build_interchange().model_copy(
        update={
            "iea": build_interchange().iea.model_copy(
                update={"number_of_included_functional_groups": 99}
            )
        }
    )
    group = interchange.functional_groups[0]
    interchange.functional_groups[0] = group.model_copy(
        update={
            "ge": group.ge.model_copy(update={"number_of_transaction_sets_included": 99}),
            "transactions": [
                group.transactions[0],
                group.transactions[0].model_copy(
                    update={
                        "st": group.transactions[0].st.model_copy(
                            update={"transaction_set_control_number": "0099"}
                        )
                    }
                ),
            ],
        }
    )

    encoded = encode(interchange, config=build_submitter_config())
    reparsed = parse(encoded)
    rendered_group = reparsed.interchange.functional_groups[0]

    assert rendered_group.transactions[0].se.number_of_included_segments == 13
    assert rendered_group.transactions[1].se.number_of_included_segments == 13
    assert rendered_group.ge.number_of_transaction_sets_included == 2
    assert reparsed.interchange.iea.number_of_included_functional_groups == 1


def test_encode_accepts_custom_delimiters() -> None:
    parsed = parse(read_fixture("270_realtime_single.x12"))
    custom_delimiters = Delimiters(element="|", segment="!", sub_element=":", repetition="~")

    encoded = encode(parsed.interchange, delimiters=custom_delimiters)
    reparsed = parse(encoded)

    assert encoded.startswith("ISA|")
    assert "!" in encoded
    assert reparsed.interchange.delimiters == custom_delimiters


def test_encode_regenerates_sequential_control_numbers_for_split_output() -> None:
    interchanges = [
        parse(read_fixture("270_realtime_single.x12")).interchange,
        parse(read_fixture("271_active_response.x12")).interchange,
    ]

    encoded = encode(interchanges)

    assert isinstance(encoded, list)
    assert len(encoded) == 2
    first = parse(encoded[0]).interchange
    second = parse(encoded[1]).interchange
    assert first.isa.interchange_control_number == "000000001"
    assert second.isa.interchange_control_number == "000000002"
    assert first.functional_groups[0].gs.group_control_number == "1"
    assert second.functional_groups[0].gs.group_control_number == "2"
    assert first.functional_groups[0].transactions[0].st.transaction_set_control_number == "0001"
    assert second.functional_groups[0].transactions[0].st.transaction_set_control_number == "0002"


def test_encode_uses_configured_control_number_starts_when_provided() -> None:
    encoded = encode(
        build_interchange(),
        config=build_submitter_config(
            isa_control_number_start=9,
            gs_control_number_start=40,
            st_control_number_start=99,
        ),
    )
    reparsed = parse(encoded)

    assert reparsed.interchange.isa.interchange_control_number == "000000009"
    assert reparsed.interchange.functional_groups[0].gs.group_control_number == "40"
    assert (
        reparsed.interchange.functional_groups[0].transactions[0].st.transaction_set_control_number
        == "0099"
    )
