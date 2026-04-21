from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from x12_edi_tools import ParseResult, encode, parse
from x12_edi_tools.common.types import SegmentToken
from x12_edi_tools.exceptions import X12ParseError
from x12_edi_tools.models import GenericSegment, NM1Segment
from x12_edi_tools.parser.isa_parser import detect_delimiters
from x12_edi_tools.parser.segment_parser import parse_segment
from x12_edi_tools.parser.tokenizer import tokenize

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def first_270_subscriber_loop(raw: str):
    transaction = parse(raw).interchange.functional_groups[0].transactions[0]
    return transaction.loop_2000a.loop_2000b[0].loop_2000c[0]


def test_detect_delimiters_extracts_standard_isa_values() -> None:
    delimiters = detect_delimiters(read_fixture("270_realtime_single.x12"))

    assert delimiters.element == "*"
    assert delimiters.segment == "~"
    assert delimiters.sub_element == ":"
    assert delimiters.repetition == "^"


def test_detect_delimiters_supports_custom_pipe_fixture() -> None:
    delimiters = detect_delimiters(read_fixture("270_custom_delimiters.x12"))

    assert delimiters.element == "|"
    assert delimiters.segment == "!"
    assert delimiters.sub_element == ":"
    assert delimiters.repetition == "~"


def test_detect_delimiters_rejects_short_or_non_isa_input() -> None:
    with pytest.raises(X12ParseError):
        detect_delimiters("ISA*TOO*SHORT")

    with pytest.raises(X12ParseError):
        detect_delimiters("GS*HS*NOT*AN*ISA")


def test_tokenize_splits_segments_strips_newlines_and_preserves_trailing_elements() -> None:
    tokens = tokenize(
        "GS*HS*ONE~\nREF*EJ*123**~\nSE*2*0001~",
        detect_delimiters(read_fixture("270_realtime_single.x12")),
    )

    assert [token.segment_id for token in tokens] == ["GS", "REF", "SE"]
    assert tokens[1].elements == ("EJ", "123", "", "")
    assert tokens[1].position > tokens[0].position


def test_parse_segment_dispatches_nm1_and_handles_unknown_segments_by_mode() -> None:
    nm1_token = SegmentToken(
        segment_id="NM1",
        elements=("PR", "2", "DC MEDICAID", "", "", "", "", "PI", "DCMEDICAID"),
        position=10,
    )
    parsed_nm1 = parse_segment(nm1_token)

    assert isinstance(parsed_nm1, NM1Segment)
    assert parsed_nm1.entity_identifier_code == "PR"

    unknown_token = SegmentToken(segment_id="III", elements=("X", "Y"), position=42)
    with pytest.raises(X12ParseError):
        parse_segment(unknown_token)

    parsed_unknown = parse_segment(unknown_token, strict=False)
    assert isinstance(parsed_unknown, GenericSegment)
    assert parsed_unknown.segment_id == "III"
    assert parsed_unknown.raw_elements == ["X", "Y"]


@pytest.mark.parametrize("mode", ["raise", "skip", "collect"])
def test_parse_returns_parse_result_in_all_error_modes(mode: str) -> None:
    result = parse(read_fixture("270_realtime_single.x12"), on_error=mode)  # type: ignore[arg-type]

    assert isinstance(result, ParseResult)
    assert result.errors == []


def test_parse_270_single_returns_expected_envelope_and_subscriber_fields() -> None:
    result = parse(read_fixture("270_realtime_single.x12"))

    transaction = result.interchange.functional_groups[0].transactions[0]
    subscriber = transaction.loop_2000a.loop_2000b[0].loop_2000c[0].loop_2100c.nm1

    assert result.interchange.isa.receiver_id.strip() == "DCMEDICAID"
    assert subscriber.last_name == "DOE"
    assert subscriber.first_name == "PATIENT"


def test_parse_270_routes_pre_eq_dtp_to_2100c_subscriber_date() -> None:
    raw = read_fixture("270_realtime_single.x12")

    subscriber_loop = first_270_subscriber_loop(raw)
    encoded = encode(parse(raw).interchange)

    assert subscriber_loop.loop_2100c.dtp_segments[0].date_time_qualifier == "291"
    assert subscriber_loop.loop_2110c[0].dtp_segments == []
    assert "DMG*D8*19900101*F~DTP*291*D8*20260412~EQ*30~" in encoded


def test_parse_270_preserves_post_eq_dtp_in_2110c_for_archived_files() -> None:
    raw = read_fixture("270_realtime_single.x12").replace(
        "DTP*291*D8*20260412~\nEQ*30~",
        "EQ*30~\nDTP*291*D8*20260412~",
    )

    subscriber_loop = first_270_subscriber_loop(raw)
    encoded = encode(parse(raw).interchange)

    assert subscriber_loop.loop_2100c.dtp_segments == []
    assert subscriber_loop.loop_2110c[0].dtp_segments[0].date_time_qualifier == "291"
    assert "EQ*30~DTP*291*D8*20260412~" in encoded


def test_parse_270_batch_multi_preserves_multiple_transaction_sets() -> None:
    result = parse(read_fixture("270_batch_multi.x12"))

    transactions = result.interchange.functional_groups[0].transactions
    assert len(transactions) == 2
    assert transactions[0].st.transaction_set_control_number == "0001"
    assert transactions[1].st.transaction_set_control_number == "0002"


def test_parse_271_active_response_extracts_active_eb_segment() -> None:
    result = parse(read_fixture("271_active_response.x12"))

    eligibility_loop = (
        result.interchange.functional_groups[0]
        .transactions[0]
        .loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2110c[0]
    )

    assert eligibility_loop.eb_segments[0].eligibility_or_benefit_information == "1"


def test_parse_271_rejected_subscriber_extracts_aaa_reason_code() -> None:
    result = parse(read_fixture("271_rejected_subscriber.x12"))

    subscriber_loop = (
        result.interchange.functional_groups[0]
        .transactions[0]
        .loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2100c
    )

    assert subscriber_loop.aaa_segments[0].reject_reason_code == "72"


def test_parse_271_multiple_eb_segments_keeps_all_ebs_in_2110c() -> None:
    result = parse(read_fixture("271_multiple_eb_segments.x12"))

    eligibility_loop = (
        result.interchange.functional_groups[0]
        .transactions[0]
        .loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2110c[0]
    )

    assert len(eligibility_loop.eb_segments) == 2
    assert eligibility_loop.eb_segments[1].monetary_amount == Decimal("5.00")


def test_parse_custom_delimiters_fixture_round_trips_through_parser() -> None:
    result = parse(read_fixture("270_custom_delimiters.x12"))

    subscriber = (
        result.interchange.functional_groups[0]
        .transactions[0]
        .loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2100c.nm1
    )

    assert result.interchange.delimiters.element == "|"
    assert result.interchange.delimiters.segment == "!"
    assert subscriber.first_name == "CUSTOM"


def test_parse_garbled_input_raises_x12_parse_error() -> None:
    with pytest.raises(X12ParseError):
        parse("not actually x12")


def test_loop_builder_builds_hierarchy_and_handles_ls_le_wrappers() -> None:
    result = parse(read_fixture("271_ls_le_wrapper.x12"))

    transaction = result.interchange.functional_groups[0].transactions[0]
    information_source = transaction.loop_2000a
    information_receiver = information_source.loop_2000b[0]
    subscriber = information_receiver.loop_2000c[0]
    eligibility = subscriber.loop_2110c[0]

    assert information_source.hl.hierarchical_level_code == "20"
    assert information_receiver.hl.hierarchical_level_code == "21"
    assert subscriber.hl.hierarchical_level_code == "22"
    assert eligibility.ls_segment is not None
    assert eligibility.ls_segment.loop_identifier_code == "2120"
    assert eligibility.le_segment is not None
    assert eligibility.le_segment.loop_identifier_code == "2120"
    assert eligibility.ref_segments[0].reference_identification == "PLAN123"


def test_parse_collect_mode_keeps_valid_transactions_and_reports_error_metadata() -> None:
    result = parse(read_fixture("batch_with_one_bad_transaction.x12"), on_error="collect")

    transactions = result.interchange.functional_groups[0].transactions
    assert len(transactions) == 2
    assert len(result.errors) == 1
    assert result.errors[0].transaction_index == 1
    assert result.errors[0].st_control_number == "0002"
    assert result.errors[0].segment_id == "NM1"
    assert result.errors[0].error == "segment_validation_error"
    assert "NM1*IL*9*DOE*BROKEN" in result.errors[0].raw_segment


def test_parse_skip_mode_discards_invalid_transactions_without_collecting_errors() -> None:
    result = parse(read_fixture("batch_with_one_bad_transaction.x12"), on_error="skip")

    transactions = result.interchange.functional_groups[0].transactions
    assert len(transactions) == 2
    assert [transaction.st.transaction_set_control_number for transaction in transactions] == [
        "0001",
        "0003",
    ]
    assert result.errors == []


def test_lenient_parse_preserves_unknown_segments_and_surfaces_warnings() -> None:
    raw = read_fixture("270_realtime_single.x12").replace(
        "SE*13*0001~",
        "III*X*Y~SE*13*0001~",
    )

    with pytest.raises(X12ParseError):
        parse(raw)

    result = parse(raw, strict=False)
    transaction = result.interchange.functional_groups[0].transactions[0]

    assert transaction.generic_segments[0].segment_id == "III"
    assert transaction.generic_segments[0].raw_elements == ["X", "Y"]
    assert result.warnings
    assert "III" in result.warnings[0]
