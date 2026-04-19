from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import ClassVar

import pytest
from pydantic import ValidationError

from test_phase1_models import build_interchange, build_isa_segment
from x12_edi_tools import (
    Delimiters,
    EligibilityResult,
    EligibilityResultSet,
    EligibilitySegment,
    ImportResult,
    PatientRecord,
    X12ParseError,
)
from x12_edi_tools.common.enums import (
    AAARejectReasonCode,
    EntityIdentifierCode,
    HierarchicalLevelCode,
)
from x12_edi_tools.common.types import ElementMap, SegmentToken
from x12_edi_tools.convenience import (
    _coerce_patients,
    _decimal_string,
    _enum_value,
    _load_raw_x12,
    _map_aaa_segments,
    _map_benefit_entities,
    _normalize_date,
    _normalize_rows,
    _overall_status,
    _parse_delimited,
    _parse_flexible_date,
    _parse_xlsx,
    _project_subscriber_loop,
    _provider_per_segment,
    _provider_prv_segment,
    _resolve_input_path,
    read_271,
)
from x12_edi_tools.encoder.segment_encoder import _render_element
from x12_edi_tools.models import (
    AAASegment,
    BHTSegment,
    DMGSegment,
    DTPSegment,
    EBSegment,
    EQSegment,
    FunctionalGroup,
    GenericSegment,
    GSSegment,
    HLSegment,
    Interchange,
    ISASegment,
    LESegment,
    Loop2000A_270,
    Loop2000A_271,
    Loop2000B_270,
    Loop2000B_271,
    Loop2000C_270,
    Loop2000C_271,
    Loop2100A_270,
    Loop2100B_270,
    Loop2100C_270,
    Loop2110C_271,
    LSSegment,
    N3Segment,
    N4Segment,
    NM1Segment,
    PERSegment,
    PRVSegment,
    REFSegment,
    SESegment,
    STSegment,
    Transaction270,
    TRNSegment,
    X12Segment,
)
from x12_edi_tools.parser import isa_parser, x12_parser
from x12_edi_tools.parser._exceptions import ParserComponentError
from x12_edi_tools.parser.isa_parser import detect_delimiters, parse_isa_segment
from x12_edi_tools.parser.loop_builder import (
    _append_270_ref,
    _append_271_aaa,
    _append_271_ref,
    _build_270_hierarchy,
    _build_271_hierarchy,
    _Loop2000A270State,
    _Loop2000A271State,
    _Loop2000B270State,
    _Loop2000B271State,
    _Loop2000C270State,
    _Loop2000C271State,
    _Loop2100A270State,
    _Loop2100A271State,
    _Loop2100B270State,
    _Loop2100B271State,
    _Loop2100C270State,
    _Loop2100C271State,
    _Loop2110C270State,
    _Loop2110C271State,
    build_transaction,
)
from x12_edi_tools.parser.segment_parser import parse_segment, render_raw_segment
from x12_edi_tools.parser.tokenizer import tokenize
from x12_edi_tools.payers.dc_medicaid.profile import DCMedicaidProfile
from x12_edi_tools.validator.base import TransactionContext
from x12_edi_tools.validator.snip2 import (
    _validate_270_structure,
    _validate_271_structure,
    _validate_transaction_required_content,
    validate_snip2,
)
from x12_edi_tools.validator.snip4 import (
    _validate_dtp_formats,
    _validate_hl_structure,
)
from x12_edi_tools.validator.snip5 import validate_snip5

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def issue_codes(issues: list[object]) -> set[str]:
    return {issue.code for issue in issues}


def pair(segment: X12Segment | GenericSegment, position: int) -> tuple[object, SegmentToken]:
    return (
        segment,
        SegmentToken(segment.segment_id, tuple(segment.to_elements()), position),
    )


def test_import_result_and_result_set_sequence_helpers_cover_dunder_paths() -> None:
    patient = PatientRecord(
        last_name="SMITH",
        first_name="JOHN",
        date_of_birth="19850115",
        gender="M",
        member_id="12345678",
        service_type_code="30",
        service_date="20260415",
    )
    imported = ImportResult(patients=[patient])
    assert imported
    assert len(imported) == 1
    assert list(imported) == [patient]
    assert imported[0] is patient

    result_set = EligibilityResultSet(
        payer_name="DC MEDICAID",
        transaction_count=1,
        results=[
            EligibilityResult(member_name="A", member_id="1", overall_status="active"),
            EligibilityResult(member_name="B", member_id="2", overall_status="inactive"),
            EligibilityResult(member_name="C", member_id="3", overall_status="error"),
            EligibilityResult(member_name="D", member_id="4", overall_status="unknown"),
        ],
    )
    assert len(result_set) == 4
    assert [result.member_name for result in result_set] == ["A", "B", "C", "D"]
    assert result_set[1].overall_status == "inactive"
    assert result_set.summary == {
        "total": 4,
        "active": 1,
        "inactive": 1,
        "error": 1,
        "unknown": 1,
    }


def test_convenience_resolve_input_path_and_load_raw_x12_cover_file_branches(
    tmp_path: Path,
) -> None:
    payload_path = tmp_path / "response.x12"
    payload_path.write_text(read_fixture("271_active_response.x12"), encoding="utf-8")

    with pytest.raises(Exception, match="not a file"):
        _resolve_input_path(tmp_path)

    assert _load_raw_x12(str(payload_path)).startswith("ISA")
    assert _load_raw_x12("ST*270") == "ST*270"


def test_convenience_tabular_parsers_cover_empty_rows_and_txt_sniffing() -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        ["last_name", "first_name", "date_of_birth", "gender", "member_id", "service_date"]
    )
    sheet.append([None, None, None, None, None, None])
    sheet.append(["SMITH", "JOHN", "19850115", "M", "12345678", "20260415"])
    empty_workbook = Workbook()

    workbook_bytes = Path(FIXTURES / "workbook.xlsx")
    empty_bytes = Path(FIXTURES / "empty.xlsx")
    try:
        workbook.save(workbook_bytes)
        empty_workbook.save(empty_bytes)
        headers, rows = _parse_xlsx(workbook_bytes.read_bytes())
        assert headers[0] == "last_name"
        assert len(rows) == 1

        empty_headers, empty_rows = _parse_xlsx(empty_bytes.read_bytes())
        assert empty_headers == []
        assert empty_rows == []
    finally:
        if workbook_bytes.exists():
            workbook_bytes.unlink()
        if empty_bytes.exists():
            empty_bytes.unlink()

    headers, rows = _parse_delimited(
        b"last_name\tfirst_name\tdate_of_birth\tgender\tmember_id\tservice_date\n"
        b"\n"
        b"SMITH\tJOHN\t19850115\tM\t12345678\t20260415\n",
        ".txt",
    )
    assert headers[0] == "last_name"
    assert len(rows) == 1

    fallback_headers, fallback_rows = _parse_delimited(b"", ".txt")
    assert fallback_headers == []
    assert fallback_rows == []


def test_convenience_row_normalization_covers_service_type_and_missing_field_errors() -> None:
    result = _normalize_rows(
        headers=[
            "last_name",
            "first_name",
            "date_of_birth",
            "gender",
            "member_id",
            "service_type_code",
            "service_date",
        ],
        rows=[
            {
                "last_name": "SMITH",
                "first_name": None,
                "date_of_birth": "1985-01-15",
                "gender": "M",
                "member_id": "",
                "service_type_code": "bad",
                "service_date": None,
            }
        ],
        default_service_type_code="30",
        default_service_date=None,
    )

    assert not result.patients
    assert any(correction.field == "service_type_code" for correction in result.corrections)
    assert {(error.field, error.message) for error in result.errors} >= {
        ("service_type_code", "Unsupported service_type_code 'BAD'."),
        ("first_name", "first_name is required."),
        ("service_date", "service_date is required and must be parseable."),
        ("member_id", "Provide at least one subscriber identifier: member_id or ssn."),
    }


def test_convenience_date_and_patient_coercion_helpers_cover_error_branches() -> None:
    corrections: list[object] = []
    assert (
        _normalize_date("   ", field_name="service_date", row_number=1, corrections=corrections)
        is None
    )
    assert _parse_flexible_date("20260230") is None
    assert _provider_prv_segment("207Q00000X") is not None
    assert (
        _provider_per_segment(
            contact_name="HELP DESK",
            contact_phone=None,
            contact_email="help@example.com",
        )
        is not None
    )

    with pytest.raises(Exception, match="failed validation"):
        _coerce_patients([{"last_name": "SMITH"}])

    with pytest.raises(Exception, match="must be a PatientRecord or mapping"):
        _coerce_patients([123])


def test_convenience_projection_and_status_helpers_cover_remaining_paths() -> None:
    subscriber_loop = read_271(FIXTURES / "271_ls_le_wrapper.x12").results
    assert subscriber_loop

    parsed = x12_parser.parse(read_fixture("271_ls_le_wrapper.x12"), strict=False).interchange
    loop = parsed.functional_groups[0].transactions[0].loop_2000a.loop_2000b[0].loop_2000c[0]
    synthetic_loop = loop.model_copy(update={"loop_2110c": [object(), loop.loop_2110c[0]]})
    projected = _project_subscriber_loop(synthetic_loop)
    assert projected.benefit_entities
    assert projected.benefit_entities[0].identifier == "PLAN123"

    assert _map_benefit_entities(loop.loop_2110c[0])[0].loop_identifier == "2120"
    assert _map_aaa_segments([object()]) == []
    assert _overall_status([EligibilitySegment(eligibility_code="6")], []) == "inactive"
    assert _overall_status([EligibilitySegment(eligibility_code="9")], []) == "unknown"
    assert _decimal_string(Decimal("5.00")) == "5.00"
    assert _enum_value(None) is None


def test_convenience_read_271_reraises_parse_errors() -> None:
    with pytest.raises(X12ParseError):
        read_271("not actually x12")


def test_segment_encoder_and_model_validators_cover_remaining_small_branches() -> None:
    class EmptySegment(X12Segment):
        segment_id: ClassVar[str] = "ZZ"
        _element_map: ClassVar[ElementMap] = {}

    assert EmptySegment().to_elements() == []
    assert _render_element(None, delimiters=Delimiters()) == ""
    assert _render_element(EntityIdentifierCode.PAYER, delimiters=Delimiters()) == "PR"
    assert _render_element(Decimal("5.00"), delimiters=Delimiters()) == "5.00"

    with pytest.raises(ValidationError):
        AAASegment(
            response_code="X",
            reject_reason_code=AAARejectReasonCode.INVALID_MEMBER_ID,
        )
    with pytest.raises(ValidationError):
        HLSegment(
            hierarchical_id_number="1",
            hierarchical_level_code=HierarchicalLevelCode.INFORMATION_SOURCE,
            hierarchical_child_code="9",
        )
    with pytest.raises(ValidationError):
        ISASegment.model_validate(
            build_isa_segment().model_dump(mode="python")
            | {"interchange_control_number": "ABCDEFGHI"}
        )


def test_parser_helpers_cover_edge_cases_and_lower_level_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = read_fixture("270_realtime_single.x12")

    with pytest.raises(X12ParseError, match="Invalid ISA delimiters"):
        monkeypatch.setattr(isa_parser, "Delimiters", mock_delimiters_raising)
        detect_delimiters(fixture)
    monkeypatch.setattr(isa_parser, "Delimiters", Delimiters)

    malformed_isa = fixture.replace("000000001", "ABC000001", 1)
    with pytest.raises(X12ParseError, match="ISA segment validation failed"):
        parse_isa_segment(malformed_isa)

    delimiters = Delimiters()
    assert render_raw_segment(SegmentToken("GS", (), 0), element_separator="*") == "GS"
    assert [token.segment_id for token in tokenize("~GS*HS*ONE~", delimiters)] == ["GS"]
    with pytest.raises(X12ParseError, match="missing a segment terminator"):
        tokenize("GS*HS", delimiters)
    with pytest.raises(X12ParseError, match="empty segment identifier"):
        tokenize("*ABC~", delimiters)
    with pytest.raises(X12ParseError, match="not well formed"):
        parse_segment(SegmentToken("TOOLONG", ("X",), 7), strict=False)

    with pytest.raises(ValueError, match="on_error must be one of"):
        x12_parser.parse(fixture, on_error="bad")  # type: ignore[arg-type]

    with pytest.raises(X12ParseError, match="Unexpected end of token stream"):
        x12_parser._collect_transaction_tokens([], start_index=0, element_separator="*")
    with pytest.raises(X12ParseError, match="Expected ST to open a transaction"):
        x12_parser._collect_transaction_tokens(
            [SegmentToken("BHT", ("13",), 5)],
            start_index=0,
            element_separator="*",
        )

    tokens = [
        SegmentToken("ST", ("270", "0001"), 0),
        SegmentToken("GE", ("1", "1"), 12),
    ]
    collected, cursor, collector_error = x12_parser._collect_transaction_tokens(
        tokens,
        start_index=0,
        element_separator="*",
    )
    assert collected == [tokens[0]]
    assert cursor == 1
    assert collector_error is not None

    eof_tokens = [SegmentToken("ST", ("270", "0001"), 0)]
    _, eof_cursor, eof_error = x12_parser._collect_transaction_tokens(
        eof_tokens,
        start_index=0,
        element_separator="*",
    )
    assert eof_cursor == 1
    assert eof_error is not None
    assert x12_parser._extract_st_control_number([]) is None
    assert x12_parser._extract_st_control_number([SegmentToken("BHT", ("13",), 0)]) is None


def mock_delimiters_raising(**_: object) -> Delimiters:
    raise ValueError("boom")


@pytest.mark.parametrize(
    ("segment_id", "expected_message"),
    [
        ("GS", "Expected GS"),
        ("GE", "Expected GE"),
        ("IEA", "Expected IEA"),
    ],
)
def test_parse_can_surface_nonstandard_guard_errors(
    monkeypatch: pytest.MonkeyPatch,
    segment_id: str,
    expected_message: str,
) -> None:
    real_parse_segment = x12_parser.parse_segment

    def fake_parse_segment(token: SegmentToken, **kwargs: object) -> object:
        if token.segment_id == segment_id:
            return GenericSegment(segment_id="ZZ", raw_elements=[])
        return real_parse_segment(token, **kwargs)

    monkeypatch.setattr(x12_parser, "parse_segment", fake_parse_segment)
    with pytest.raises(X12ParseError, match=expected_message):
        x12_parser.parse(read_fixture("270_realtime_single.x12"))


def test_parse_can_surface_missing_ge_and_missing_group_errors() -> None:
    missing_ge = (
        read_fixture("270_realtime_single.x12")
        .replace("GE*1*1~\n", "")
        .replace(
            "IEA*1*000000001~\n",
            "",
        )
    )
    with pytest.raises(X12ParseError, match="before a GE trailer"):
        x12_parser.parse(missing_ge)

    fixture = read_fixture("270_realtime_single.x12")
    isa_and_iea_only = fixture[:106] + "IEA*1*000000001~"
    with pytest.raises(X12ParseError, match="does not contain a functional group"):
        x12_parser.parse(isa_and_iea_only)


def test_loop_builder_270_hierarchy_populates_optional_provider_and_ref_segments() -> None:
    body = [
        pair(
            HLSegment(
                hierarchical_id_number="1",
                hierarchical_level_code=HierarchicalLevelCode.INFORMATION_SOURCE,
                hierarchical_child_code="1",
            ),
            1,
        ),
        pair(
            NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PAYER,
                entity_type_qualifier="2",
                last_name="DC MEDICAID",
                id_code_qualifier="PI",
                id_code="DCMEDICAID",
            ),
            2,
        ),
        pair(
            REFSegment(
                reference_identification_qualifier="2U", reference_identification="PAYERREF"
            ),
            3,
        ),
        pair(
            HLSegment(
                hierarchical_id_number="2",
                hierarchical_parent_id_number="1",
                hierarchical_level_code=HierarchicalLevelCode.INFORMATION_RECEIVER,
                hierarchical_child_code="1",
            ),
            4,
        ),
        pair(
            NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PROVIDER,
                entity_type_qualifier="2",
                last_name="ACME HOME HEALTH",
                id_code_qualifier="XX",
                id_code="1234567893",
            ),
            5,
        ),
        pair(
            PRVSegment(
                provider_code="BI",
                reference_identification_qualifier="PXC",
                reference_identification="207Q00000X",
            ),
            6,
        ),
        pair(
            PERSegment(
                contact_function_code="IC",
                name="HELP DESK",
                communication_number_qualifier_1="TE",
                communication_number_1="2025551212",
            ),
            7,
        ),
        pair(N3Segment(address_information_1="123 MAIN ST"), 8),
        pair(
            N4Segment(city_name="WASHINGTON", state_or_province_code="DC", postal_code="20001"), 9
        ),
        pair(
            REFSegment(
                reference_identification_qualifier="G2", reference_identification="PROVIDERREF"
            ),
            10,
        ),
        pair(
            HLSegment(
                hierarchical_id_number="3",
                hierarchical_parent_id_number="2",
                hierarchical_level_code=HierarchicalLevelCode.SUBSCRIBER,
                hierarchical_child_code="0",
            ),
            11,
        ),
        pair(
            TRNSegment(
                trace_type_code="1",
                reference_identification_1="TRACE0001",
                originating_company_identifier="1234567893",
            ),
            12,
        ),
        pair(
            NM1Segment(
                entity_identifier_code=EntityIdentifierCode.SUBSCRIBER,
                entity_type_qualifier="1",
                last_name="DOE",
                first_name="PATIENT",
                id_code_qualifier="MI",
                id_code="000123450",
            ),
            13,
        ),
        pair(
            DMGSegment(
                date_time_period_format_qualifier="D8",
                date_time_period="19900101",
                gender_code="F",
            ),
            14,
        ),
        pair(
            REFSegment(
                reference_identification_qualifier="SY", reference_identification="111223333"
            ),
            15,
        ),
        pair(EQSegment(service_type_code="30"), 16),
        pair(
            REFSegment(
                reference_identification_qualifier="EJ", reference_identification="INQUIRYREF"
            ),
            17,
        ),
        pair(
            DTPSegment(
                date_time_qualifier="291",
                date_time_period_format_qualifier="D8",
                date_time_period="20260412",
            ),
            18,
        ),
    ]

    hierarchy = _build_270_hierarchy(body, element_separator="*")
    provider_loop = hierarchy.loop_2000b[0].loop_2100b
    subscriber_loop = hierarchy.loop_2000b[0].loop_2000c[0]
    inquiry_loop = subscriber_loop.loop_2110c[0]

    assert hierarchy.loop_2100a.ref_segments[0].reference_identification == "PAYERREF"
    assert provider_loop.prv is not None
    assert provider_loop.per is not None
    assert provider_loop.n3 is not None
    assert provider_loop.n4 is not None
    assert provider_loop.ref_segments[0].reference_identification == "PROVIDERREF"
    assert subscriber_loop.loop_2100c.ref_segments[0].reference_identification == "111223333"
    assert inquiry_loop.ref_segments[0].reference_identification == "INQUIRYREF"


def test_loop_builder_271_hierarchy_routes_aaa_ref_and_address_segments_by_context() -> None:
    body = [
        pair(GenericSegment(segment_id="III", raw_elements=["X", "Y"]), 1),
        pair(
            HLSegment(
                hierarchical_id_number="1",
                hierarchical_level_code=HierarchicalLevelCode.INFORMATION_SOURCE,
                hierarchical_child_code="1",
            ),
            2,
        ),
        pair(
            AAASegment(
                response_code="N",
                reject_reason_code=AAARejectReasonCode.INVALID_MEMBER_ID,
                follow_up_action_code="C",
            ),
            3,
        ),
        pair(
            NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PAYER,
                entity_type_qualifier="2",
                last_name="DC MEDICAID",
                id_code_qualifier="PI",
                id_code="DCMEDICAID",
            ),
            4,
        ),
        pair(
            REFSegment(
                reference_identification_qualifier="2U", reference_identification="PAYERREF"
            ),
            5,
        ),
        pair(
            HLSegment(
                hierarchical_id_number="2",
                hierarchical_parent_id_number="1",
                hierarchical_level_code=HierarchicalLevelCode.INFORMATION_RECEIVER,
                hierarchical_child_code="1",
            ),
            6,
        ),
        pair(
            AAASegment(
                response_code="N",
                reject_reason_code=AAARejectReasonCode.INVALID_NAME,
                follow_up_action_code="C",
            ),
            7,
        ),
        pair(
            NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PROVIDER,
                entity_type_qualifier="2",
                last_name="ACME HOME HEALTH",
                id_code_qualifier="XX",
                id_code="1234567893",
            ),
            8,
        ),
        pair(
            PERSegment(
                contact_function_code="IC",
                name="HELP DESK",
                communication_number_qualifier_1="TE",
                communication_number_1="2025551212",
            ),
            9,
        ),
        pair(N3Segment(address_information_1="123 MAIN ST"), 10),
        pair(
            N4Segment(city_name="WASHINGTON", state_or_province_code="DC", postal_code="20001"), 11
        ),
        pair(
            REFSegment(
                reference_identification_qualifier="G2", reference_identification="PROVIDERREF"
            ),
            12,
        ),
        pair(
            HLSegment(
                hierarchical_id_number="3",
                hierarchical_parent_id_number="2",
                hierarchical_level_code=HierarchicalLevelCode.SUBSCRIBER,
                hierarchical_child_code="0",
            ),
            13,
        ),
        pair(
            AAASegment(
                response_code="N",
                reject_reason_code=AAARejectReasonCode.SUBSCRIBER_INSURED_NOT_FOUND,
                follow_up_action_code="C",
            ),
            14,
        ),
        pair(
            TRNSegment(
                trace_type_code="1",
                reference_identification_1="TRACE0001",
                originating_company_identifier="1234567893",
            ),
            15,
        ),
        pair(
            NM1Segment(
                entity_identifier_code=EntityIdentifierCode.SUBSCRIBER,
                entity_type_qualifier="1",
                last_name="DOE",
                first_name="PATIENT",
                id_code_qualifier="MI",
                id_code="000123450",
            ),
            16,
        ),
        pair(
            AAASegment(
                response_code="N",
                reject_reason_code=AAARejectReasonCode.DATE_OF_BIRTH_MISMATCH,
                follow_up_action_code="C",
            ),
            17,
        ),
        pair(N3Segment(address_information_1="456 OAK ST"), 18),
        pair(
            N4Segment(city_name="WASHINGTON", state_or_province_code="DC", postal_code="20002"), 19
        ),
        pair(
            DMGSegment(
                date_time_period_format_qualifier="D8",
                date_time_period="19900101",
                gender_code="F",
            ),
            20,
        ),
        pair(
            REFSegment(
                reference_identification_qualifier="SY", reference_identification="111223333"
            ),
            21,
        ),
        pair(
            EBSegment(
                eligibility_or_benefit_information="1",
                service_type_code="30",
                plan_coverage_description="ACTIVE COVERAGE",
            ),
            22,
        ),
        pair(
            AAASegment(
                response_code="N",
                reject_reason_code=AAARejectReasonCode.INVALID_MEMBER_ID,
                follow_up_action_code="C",
            ),
            23,
        ),
        pair(
            REFSegment(reference_identification_qualifier="1L", reference_identification="PLAN123"),
            24,
        ),
        pair(
            DTPSegment(
                date_time_qualifier="291",
                date_time_period_format_qualifier="D8",
                date_time_period="20260412",
            ),
            25,
        ),
        pair(LSSegment(loop_identifier_code="2120"), 26),
        pair(LESegment(loop_identifier_code="2120"), 27),
    ]

    hierarchy = _build_271_hierarchy(body, element_separator="*")
    receiver_loop = hierarchy.loop_2000b[0]
    subscriber_loop = receiver_loop.loop_2000c[0]
    inquiry_loop = subscriber_loop.loop_2110c[0]

    assert hierarchy.aaa_segments[0].reject_reason_code == "72"
    assert hierarchy.loop_2100a.ref_segments[0].reference_identification == "PAYERREF"
    assert receiver_loop.aaa_segments[0].reject_reason_code == "73"
    assert receiver_loop.loop_2100b.per is not None
    assert receiver_loop.loop_2100b.n3 is not None
    assert receiver_loop.loop_2100b.n4 is not None
    assert receiver_loop.loop_2100b.ref_segments[0].reference_identification == "PROVIDERREF"
    assert subscriber_loop.aaa_segments[0].reject_reason_code == "75"
    assert subscriber_loop.loop_2100c.aaa_segments[0].reject_reason_code == "71"
    assert subscriber_loop.loop_2100c.n3 is not None
    assert subscriber_loop.loop_2100c.n4 is not None
    assert subscriber_loop.loop_2100c.ref_segments[0].reference_identification == "111223333"
    assert inquiry_loop.aaa_segments[0].reject_reason_code == "72"
    assert inquiry_loop.ref_segments[0].reference_identification == "PLAN123"
    assert inquiry_loop.ls_segment is not None
    assert inquiry_loop.le_segment is not None


def test_loop_builder_append_helpers_cover_parent_resolution_and_orphans() -> None:
    token = SegmentToken("REF", ("EJ", "12345"), 10)
    ref = REFSegment(reference_identification_qualifier="EJ", reference_identification="12345")
    aaa = AAASegment(
        response_code="N",
        reject_reason_code=AAARejectReasonCode.INVALID_MEMBER_ID,
        follow_up_action_code="C",
    )
    current_2110c_270 = _Loop2110C270State()
    current_2000c_270 = _Loop2000C270State(
        hl=HLSegment(
            hierarchical_id_number="3",
            hierarchical_parent_id_number="2",
            hierarchical_level_code=HierarchicalLevelCode.SUBSCRIBER,
        ),
        loop_2100c=_Loop2100C270State(
            nm1=NM1Segment(
                entity_identifier_code=EntityIdentifierCode.SUBSCRIBER,
                entity_type_qualifier="1",
                last_name="DOE",
                first_name="PATIENT",
            )
        ),
    )
    current_2000b_270 = _Loop2000B270State(
        hl=HLSegment(
            hierarchical_id_number="2",
            hierarchical_parent_id_number="1",
            hierarchical_level_code=HierarchicalLevelCode.INFORMATION_RECEIVER,
        ),
        loop_2100b=_Loop2100B270State(
            nm1=NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PROVIDER,
                entity_type_qualifier="2",
                last_name="ACME HOME HEALTH",
            )
        ),
    )
    current_2000a_270 = _Loop2000A270State(
        hl=HLSegment(
            hierarchical_id_number="1",
            hierarchical_level_code=HierarchicalLevelCode.INFORMATION_SOURCE,
        ),
        loop_2100a=_Loop2100A270State(
            nm1=NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PAYER,
                entity_type_qualifier="2",
                last_name="DC MEDICAID",
            )
        ),
    )

    _append_270_ref(
        ref_segment=ref,
        current_2000a=current_2000a_270,
        current_2000b=current_2000b_270,
        current_2000c=current_2000c_270,
        current_2110c=current_2110c_270,
        token=token,
        element_separator="*",
    )
    assert current_2110c_270.ref_segments[0].reference_identification == "12345"

    current_2110c_271 = _Loop2110C271State()
    current_2000c_271 = _Loop2000C271State(
        hl=current_2000c_270.hl,
        loop_2100c=_Loop2100C271State(
            nm1=NM1Segment(
                entity_identifier_code=EntityIdentifierCode.SUBSCRIBER,
                entity_type_qualifier="1",
                last_name="DOE",
            )
        ),
    )
    current_2000b_271 = _Loop2000B271State(
        hl=current_2000b_270.hl,
        loop_2100b=_Loop2100B271State(
            nm1=NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PROVIDER,
                entity_type_qualifier="2",
                last_name="ACME HOME HEALTH",
            )
        ),
    )
    current_2000a_271 = _Loop2000A271State(
        hl=current_2000a_270.hl,
        loop_2100a=_Loop2100A271State(
            nm1=NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PAYER,
                entity_type_qualifier="2",
                last_name="DC MEDICAID",
            )
        ),
    )

    _append_271_ref(
        ref_segment=ref,
        current_2000a=current_2000a_271,
        current_2000b=current_2000b_271,
        current_2000c=current_2000c_271,
        current_2110c=current_2110c_271,
        token=token,
        element_separator="*",
    )
    _append_271_aaa(
        aaa_segment=aaa,
        current_2000a=current_2000a_271,
        current_2000b=current_2000b_271,
        current_2000c=current_2000c_271,
        current_2110c=current_2110c_271,
        token=SegmentToken("AAA", ("N", "", "72"), 12),
        element_separator="*",
    )
    assert current_2110c_271.ref_segments[0].reference_identification == "12345"
    assert current_2110c_271.aaa_segments[0].reject_reason_code == "72"

    with pytest.raises(ParserComponentError, match="does not have an active parent loop"):
        _append_270_ref(
            ref_segment=ref,
            current_2000a=None,
            current_2000b=None,
            current_2000c=None,
            current_2110c=None,
            token=token,
            element_separator="*",
        )
    with pytest.raises(ParserComponentError, match="does not have an active parent loop"):
        _append_271_ref(
            ref_segment=ref,
            current_2000a=None,
            current_2000b=None,
            current_2000c=None,
            current_2110c=None,
            token=token,
            element_separator="*",
        )
    with pytest.raises(ParserComponentError, match="does not have an active parent loop"):
        _append_271_aaa(
            aaa_segment=aaa,
            current_2000a=None,
            current_2000b=None,
            current_2000c=None,
            current_2110c=None,
            token=SegmentToken("AAA", ("N", "", "72"), 12),
            element_separator="*",
        )


def test_loop_builder_error_paths_cover_incomplete_and_unsupported_transactions() -> None:
    with pytest.raises(ParserComponentError, match="Transaction is incomplete") as short_error:
        build_transaction(
            [
                pair(
                    STSegment(
                        transaction_set_identifier_code="270",
                        transaction_set_control_number="0001",
                    ),
                    1,
                )
            ],
            element_separator="*",
        )
    assert short_error.value.error == "incomplete_transaction"

    with pytest.raises(ParserComponentError, match="Unsupported transaction set") as unsupported:
        build_transaction(
            [
                pair(
                    STSegment(
                        transaction_set_identifier_code="999",
                        transaction_set_control_number="0001",
                    ),
                    1,
                ),
                pair(
                    BHTSegment(
                        hierarchical_structure_code="0022",
                        transaction_set_purpose_code="13",
                        reference_identification="REF1",
                        date="20260412",
                        time="1200",
                    ),
                    2,
                ),
                pair(GenericSegment(segment_id="ZZ", raw_elements=["X"]), 3),
                pair(
                    SESegment(number_of_included_segments=4, transaction_set_control_number="0001"),
                    4,
                ),
            ],
            element_separator="*",
        )
    assert unsupported.value.error == "unsupported_transaction"

    incomplete_270 = [
        pair(
            STSegment(transaction_set_identifier_code="270", transaction_set_control_number="0001"),
            1,
        ),
        pair(
            BHTSegment(
                hierarchical_structure_code="0022",
                transaction_set_purpose_code="13",
                reference_identification="REF1",
                date="20260412",
                time="1200",
            ),
            2,
        ),
        pair(
            HLSegment(
                hierarchical_id_number="1",
                hierarchical_level_code=HierarchicalLevelCode.INFORMATION_SOURCE,
                hierarchical_child_code="1",
            ),
            3,
        ),
        pair(
            NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PAYER,
                entity_type_qualifier="2",
                last_name="DC MEDICAID",
            ),
            4,
        ),
        pair(
            HLSegment(
                hierarchical_id_number="2",
                hierarchical_parent_id_number="1",
                hierarchical_level_code=HierarchicalLevelCode.INFORMATION_RECEIVER,
                hierarchical_child_code="1",
            ),
            5,
        ),
        pair(
            NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PROVIDER,
                entity_type_qualifier="2",
                last_name="ACME HOME HEALTH",
            ),
            6,
        ),
        pair(
            HLSegment(
                hierarchical_id_number="3",
                hierarchical_parent_id_number="2",
                hierarchical_level_code=HierarchicalLevelCode.SUBSCRIBER,
                hierarchical_child_code="0",
            ),
            7,
        ),
        pair(SESegment(number_of_included_segments=8, transaction_set_control_number="0001"), 8),
    ]
    with pytest.raises(ParserComponentError, match="missing required 2100C NM1"):
        build_transaction(incomplete_270, element_separator="*")

    incomplete_271 = [
        pair(
            STSegment(transaction_set_identifier_code="271", transaction_set_control_number="0001"),
            1,
        ),
        pair(
            BHTSegment(
                hierarchical_structure_code="0022",
                transaction_set_purpose_code="11",
                reference_identification="REF1",
                date="20260412",
                time="1200",
            ),
            2,
        ),
        pair(
            HLSegment(
                hierarchical_id_number="1",
                hierarchical_level_code=HierarchicalLevelCode.INFORMATION_SOURCE,
                hierarchical_child_code="1",
            ),
            3,
        ),
        pair(
            NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PAYER,
                entity_type_qualifier="2",
                last_name="DC MEDICAID",
            ),
            4,
        ),
        pair(
            HLSegment(
                hierarchical_id_number="2",
                hierarchical_parent_id_number="1",
                hierarchical_level_code=HierarchicalLevelCode.INFORMATION_RECEIVER,
                hierarchical_child_code="1",
            ),
            5,
        ),
        pair(
            NM1Segment(
                entity_identifier_code=EntityIdentifierCode.PROVIDER,
                entity_type_qualifier="2",
                last_name="ACME HOME HEALTH",
            ),
            6,
        ),
        pair(
            HLSegment(
                hierarchical_id_number="3",
                hierarchical_parent_id_number="2",
                hierarchical_level_code=HierarchicalLevelCode.SUBSCRIBER,
                hierarchical_child_code="0",
            ),
            7,
        ),
        pair(SESegment(number_of_included_segments=8, transaction_set_control_number="0001"), 8),
    ]
    with pytest.raises(ParserComponentError, match="missing required 2100C NM1"):
        build_transaction(incomplete_271, element_separator="*")


def test_snip2_helpers_cover_missing_envelope_and_structure_errors() -> None:
    envelope_issues = validate_snip2(
        Interchange.model_construct(
            isa=None,
            functional_groups=[
                object(),
                FunctionalGroup.model_construct(gs=None, transactions=[], ge=None),
            ],
            iea=None,
            delimiters=Delimiters(),
        )
    )
    assert issue_codes(envelope_issues) >= {"SNIP2_MISSING_ISA", "SNIP2_MISSING_GS"}

    payer_nm1 = NM1Segment.model_construct(
        entity_identifier_code=EntityIdentifierCode.PAYER,
        entity_type_qualifier="2",
        last_name=None,
        id_code_qualifier="PI",
        id_code="DCMEDICAID",
    )
    provider_nm1 = NM1Segment.model_construct(
        entity_identifier_code=EntityIdentifierCode.PROVIDER,
        entity_type_qualifier="2",
        last_name=None,
        id_code_qualifier="XX",
        id_code="1234567893",
    )
    subscriber_nm1 = NM1Segment.model_construct(
        entity_identifier_code=EntityIdentifierCode.SUBSCRIBER,
        entity_type_qualifier="1",
        last_name=None,
        id_code_qualifier="MI",
        id_code="000123450",
    )
    malformed_270 = Loop2000A_270.model_construct(
        hl=None,
        loop_2100a=Loop2100A_270.model_construct(nm1=payer_nm1, ref_segments=[]),
        loop_2000b=[
            object(),
            Loop2000B_270.model_construct(hl=None, loop_2100b=None, loop_2000c=[]),
            Loop2000B_270.model_construct(
                hl=None,
                loop_2100b=Loop2100B_270.model_construct(nm1=provider_nm1, ref_segments=[]),
                loop_2000c=[
                    object(),
                    Loop2000C_270.model_construct(
                        hl=None,
                        trn=None,
                        loop_2100c=Loop2100C_270.model_construct(
                            nm1=subscriber_nm1,
                            dmg=None,
                            ref_segments=[],
                        ),
                        loop_2110c=[],
                    ),
                ],
            ),
        ],
    )
    structure_270 = _validate_270_structure(malformed_270, "FG[0].TX[0]")
    assert issue_codes(structure_270) >= {
        "SNIP2_MISSING_HL",
        "SNIP2_REQUIRED_ELEMENT_EMPTY",
        "SNIP2_MISSING_2100B_NM1",
        "SNIP2_MISSING_2000C",
        "SNIP2_MISSING_2110C",
    }

    structure_271 = _validate_271_structure(
        Loop2000A_271.model_construct(
            hl=None,
            loop_2100a=None,
            loop_2000b=[
                object(),
                Loop2000B_271.model_construct(
                    hl=None,
                    loop_2100b=None,
                    loop_2000c=[
                        object(),
                        Loop2000C_271.model_construct(
                            hl=None, trn=None, loop_2100c=None, loop_2110c=[]
                        ),
                    ],
                ),
            ],
        ),
        "FG[0].TX[1]",
    )
    assert issue_codes(structure_271) >= {
        "SNIP2_MISSING_2100A_NM1",
        "SNIP2_MISSING_2100B_NM1",
        "SNIP2_MISSING_2100C_NM1",
    }

    missing_271_root = _validate_271_structure(None, "FG[0].TX[2]")
    assert issue_codes(missing_271_root) == {"SNIP2_MISSING_HL"}


def test_snip2_transaction_content_helper_covers_invalid_st_and_bht_codes() -> None:
    tx_context = TransactionContext(
        functional_group_index=0,
        transaction_index=0,
        transaction=Transaction270.model_construct(),
    )
    invalid_transaction = Transaction270.model_construct(
        st=STSegment.model_construct(
            transaction_set_identifier_code="999",
            transaction_set_control_number="0001",
            implementation_convention_reference="WRONG",
        ),
        bht=BHTSegment.model_construct(
            hierarchical_structure_code="0022",
            transaction_set_purpose_code="99",
            reference_identification="REF1",
            date="20260412",
            time="1200",
        ),
        loop_2000a=None,
        se=SESegment.model_construct(
            number_of_included_segments=8, transaction_set_control_number="0001"
        ),
    )
    issues = _validate_transaction_required_content(invalid_transaction, tx_context)
    assert issue_codes(issues) >= {
        "SNIP2_INVALID_ST01",
        "SNIP2_INVALID_ST03",
        "SNIP2_INVALID_BHT02",
        "SNIP2_MISSING_HL",
    }


def test_snip4_helpers_cover_missing_hl_refs_sequences_and_dtp_formats() -> None:
    assert _validate_hl_structure(Transaction270.model_construct(loop_2000a=None), 0, 0) == []

    interchange = build_interchange()
    transaction = interchange.functional_groups[0].transactions[0]
    transaction.loop_2000a.hl = HLSegment.model_construct(
        **(
            transaction.loop_2000a.hl.model_dump(mode="python")
            | {
                "hierarchical_level_code": "21",
                "hierarchical_parent_id_number": "9",
            }
        )
    )
    transaction.loop_2000a.loop_2000b[0].loop_2000c[0].hl = HLSegment.model_construct(
        **(
            transaction.loop_2000a.loop_2000b[0].loop_2000c[0].hl.model_dump(mode="python")
            | {"hierarchical_level_code": "21"}
        )
    )
    hl_issues = _validate_hl_structure(transaction, 0, 0)
    assert issue_codes(hl_issues) >= {
        "SNIP4_INVALID_HL03_SEQUENCE",
        "SNIP4_ROOT_PARENT_NOT_ALLOWED",
    }

    transaction.loop_2000a.loop_2000b[0].loop_2000c[0].loop_2110c[0].dtp_segments = [
        DTPSegment.model_construct(
            date_time_qualifier="291",
            date_time_period_format_qualifier="ZZ",
            date_time_period="20260412",
        ),
        DTPSegment.model_construct(
            date_time_qualifier="291",
            date_time_period_format_qualifier="D8",
            date_time_period="bad",
        ),
    ]
    dtp_issues = _validate_dtp_formats(transaction, 0, 0)
    assert issue_codes(dtp_issues) >= {
        "SNIP4_UNSUPPORTED_DTP_FORMAT",
        "SNIP4_DTP_FORMAT_MISMATCH",
    }


def test_snip5_validation_covers_271_specific_semantic_and_code_set_errors() -> None:
    interchange = x12_parser.parse(read_fixture("271_active_response.x12")).interchange
    group = interchange.functional_groups[0]
    group.gs = GSSegment.model_construct(
        **(group.gs.model_dump(mode="python") | {"date": "20260230"})
    )
    transaction = group.transactions[0]
    provider_loop = transaction.loop_2000a.loop_2000b[0].loop_2100b
    provider_loop.nm1 = NM1Segment.model_construct(
        **(provider_loop.nm1.model_dump(mode="python") | {"id_code": "1234567890"})
    )
    provider_loop.n4 = N4Segment(
        city_name="WASHINGTON", state_or_province_code="XX", postal_code="20001"
    )

    subscriber_loop = transaction.loop_2000a.loop_2000b[0].loop_2000c[0]
    subscriber_loop.loop_2100c.dmg = DMGSegment.model_construct(
        date_time_period_format_qualifier="D8",
        date_time_period="20260230",
        gender_code="X",
    )
    subscriber_loop.loop_2100c.n4 = N4Segment(
        city_name="WASHINGTON",
        state_or_province_code="XX",
        postal_code="20001",
    )
    inquiry_loop = subscriber_loop.loop_2110c[0]
    inquiry_loop.eb_segments.append(
        EBSegment.model_construct(
            eligibility_or_benefit_information="1",
            service_type_code="ZZ",
        )
    )
    inquiry_loop.dtp_segments.append(
        DTPSegment.model_construct(
            date_time_qualifier="291",
            date_time_period_format_qualifier="RD8",
            date_time_period="20260101-notadate",
        )
    )

    issues = validate_snip5(interchange)
    assert issue_codes(issues) >= {
        "SNIP5_INVALID_DATE",
        "SNIP5_INVALID_STATE_CODE",
        "SNIP5_INVALID_GENDER_CODE",
        "SNIP5_INVALID_SERVICE_TYPE_CODE",
        "SNIP5_INVALID_NPI",
    }


def test_dc_medicaid_profile_private_helpers_cover_remaining_validation_paths() -> None:
    profile = DCMedicaidProfile()
    interchange = build_interchange()
    interchange.functional_groups[0].gs = interchange.functional_groups[0].gs.model_copy(
        update={"application_receiver_code": "OTHER"}
    )
    envelope_issues = profile._validate_envelope_values(interchange)
    assert "DCM_INVALID_GS03" in issue_codes(envelope_issues)

    payer_issues = profile._validate_payer_nm1(
        NM1Segment.model_construct(
            entity_identifier_code=EntityIdentifierCode.PAYER,
            entity_type_qualifier="2",
            last_name="OTHER PAYER",
            id_code_qualifier="PI",
            id_code="OTHER",
        ),
        location="Loop2100A.NM1",
    )
    assert issue_codes(payer_issues) == {"DCM_INVALID_PAYER_NAME", "DCM_INVALID_PAYER_ID"}

    date_issues = profile._validate_2110c_dates(
        Loop2110C_271.model_construct(
            dtp_segments=[
                DTPSegment.model_construct(
                    date_time_qualifier="291",
                    date_time_period_format_qualifier="RD8",
                    date_time_period="20260101-20260131",
                ),
                DTPSegment.model_construct(
                    date_time_qualifier="291",
                    date_time_period_format_qualifier="D8",
                    date_time_period="not-a-date",
                ),
            ]
        ),
        anchor_date=date(2026, 4, 12),
        location="Loop2110C[0]",
    )
    assert date_issues == []

    service_type_issues = profile._validate_2110c_service_types(
        Loop2110C_271.model_construct(
            eq_segments=[EQSegment.model_construct(service_type_code="ZZ")],
            eb_segments=[
                EBSegment.model_construct(
                    eligibility_or_benefit_information="1",
                    service_type_code="ZZ",
                )
            ],
        ),
        location="Loop2110C[0]",
    )
    assert issue_codes(service_type_issues) == {"DCM_INVALID_SERVICE_TYPE"}

    aaa_issues = profile._map_aaa_segments(
        [
            object(),
            AAASegment.model_construct(response_code="N", reject_reason_code="99"),
            AAASegment(
                response_code="N",
                reject_reason_code=AAARejectReasonCode.INVALID_MEMBER_ID,
                follow_up_action_code="C",
            ),
        ],
        location="Loop2100C.AAA",
    )
    assert issue_codes(aaa_issues) == {"DCM_AAA_REJECT_72"}
