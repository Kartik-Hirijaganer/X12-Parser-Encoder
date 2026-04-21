from __future__ import annotations

from pathlib import Path

from test_phase1_models import build_interchange
from x12_edi_tools import SnipLevel, ValidationResult, parse, validate
from x12_edi_tools.common.enums import EntityIdentifierCode
from x12_edi_tools.models.segments import HLSegment, ISASegment, N4Segment, NM1Segment

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def issue_codes(result: ValidationResult) -> set[str]:
    return {issue.code for issue in result.issues}


def error_codes(result: ValidationResult) -> set[str]:
    return {issue.code for issue in result.errors}


def find_issue(result: ValidationResult, code: str) -> str:
    for issue in result.issues:
        if issue.code == code:
            return issue.message
    raise AssertionError(f"Expected issue {code} in {result.issues!r}")


def first_transaction():
    return build_interchange().functional_groups[0].transactions[0]


def first_subscriber_loop(interchange):
    return interchange.functional_groups[0].transactions[0].loop_2000a.loop_2000b[0].loop_2000c[0]


def first_provider_loop(interchange):
    return interchange.functional_groups[0].transactions[0].loop_2000a.loop_2000b[0].loop_2100b


def test_validate_accepts_set_levels_and_returns_validation_result() -> None:
    interchange = parse(read_fixture("270_realtime_single.x12")).interchange

    result = validate(interchange, levels={1, 2, 3})

    assert isinstance(result, ValidationResult)
    assert result.is_valid


def test_snip1_missing_isa_reports_error() -> None:
    interchange = build_interchange().model_copy(update={"isa": None})

    result = validate(interchange, levels={SnipLevel.SNIP1})

    assert "SNIP1_MISSING_ISA" in error_codes(result)


def test_snip1_invalid_isa_wire_length_reports_error() -> None:
    base = build_interchange()
    invalid_isa = ISASegment.model_construct(
        **(base.isa.model_dump(mode="python") | {"sender_id": "SHORT"})
    )
    interchange = base.model_copy(update={"isa": invalid_isa})

    result = validate(interchange, levels={SnipLevel.SNIP1})

    assert "SNIP1_INVALID_ISA_LENGTH" in error_codes(result)


def test_snip1_missing_iea_reports_error() -> None:
    interchange = build_interchange().model_copy(update={"iea": None})

    result = validate(interchange, levels={SnipLevel.SNIP1})

    assert "SNIP1_MISSING_IEA" in error_codes(result)


def test_snip2_missing_bht_reports_error() -> None:
    interchange = build_interchange()
    transaction = interchange.functional_groups[0].transactions[0].model_copy(update={"bht": None})
    interchange.functional_groups[0].transactions[0] = transaction

    result = validate(interchange, levels={SnipLevel.SNIP2})

    assert "SNIP2_MISSING_BHT" in error_codes(result)


def test_snip2_empty_payer_nm103_reports_error() -> None:
    interchange = build_interchange()
    payer_loop = interchange.functional_groups[0].transactions[0].loop_2000a.loop_2100a
    payer_loop.nm1 = payer_loop.nm1.model_copy(update={"last_name": None})

    result = validate(interchange, levels={SnipLevel.SNIP2})

    assert "SNIP2_REQUIRED_ELEMENT_EMPTY" in error_codes(result)


def test_snip2_wrong_gs08_reports_error() -> None:
    interchange = build_interchange()
    interchange.functional_groups[0].gs = interchange.functional_groups[0].gs.model_copy(
        update={"version_release_industry_identifier_code": "004010X098"}
    )

    result = validate(interchange, levels={SnipLevel.SNIP2})

    assert "SNIP2_INVALID_GS08_VERSION" in error_codes(result)


def test_snip2_element_exceeding_max_length_reports_error() -> None:
    interchange = build_interchange()
    invalid_nm1 = NM1Segment.model_construct(
        **(
            interchange.functional_groups[0]
            .transactions[0]
            .loop_2000a.loop_2100a.nm1.model_dump(mode="python")
            | {"last_name": "X" * 200}
        )
    )
    interchange.functional_groups[0].transactions[0].loop_2000a.loop_2100a.nm1 = invalid_nm1

    result = validate(interchange, levels={SnipLevel.SNIP2})

    assert "SNIP2_ELEMENT_TOO_LONG" in error_codes(result)


def test_snip3_se01_mismatch_reports_error() -> None:
    interchange = build_interchange()
    transaction = interchange.functional_groups[0].transactions[0]
    interchange.functional_groups[0].transactions[0] = transaction.model_copy(
        update={"se": transaction.se.model_copy(update={"number_of_included_segments": 999})}
    )

    result = validate(interchange, levels={SnipLevel.SNIP3})

    assert "SNIP3_SE01_COUNT_MISMATCH" in error_codes(result)


def test_snip3_isa13_iea02_mismatch_reports_error() -> None:
    interchange = build_interchange()
    interchange.iea = interchange.iea.model_copy(update={"interchange_control_number": "999999999"})

    result = validate(interchange, levels={SnipLevel.SNIP3})

    assert "SNIP3_ISA13_IEA02_MISMATCH" in error_codes(result)


def test_snip4_invalid_hl_parent_reports_error() -> None:
    interchange = build_interchange()
    subscriber_loop = first_subscriber_loop(interchange)
    subscriber_loop.hl = HLSegment.model_construct(
        **(subscriber_loop.hl.model_dump(mode="python") | {"hierarchical_parent_id_number": "99"})
    )

    result = validate(interchange, levels={SnipLevel.SNIP4})

    assert "SNIP4_INVALID_HL_PARENT" in error_codes(result)


def test_snip4_invalid_nm101_context_reports_error() -> None:
    interchange = build_interchange()
    payer_loop = interchange.functional_groups[0].transactions[0].loop_2000a.loop_2100a
    payer_loop.nm1 = payer_loop.nm1.model_copy(
        update={"entity_identifier_code": EntityIdentifierCode.SUBSCRIBER}
    )

    result = validate(interchange, levels={SnipLevel.SNIP4})

    assert "SNIP4_INVALID_NM101_CONTEXT" in error_codes(result)


def test_snip5_invalid_state_code_reports_error() -> None:
    interchange = parse(read_fixture("271_active_response.x12")).interchange
    subscriber_loop = first_subscriber_loop(interchange)
    subscriber_loop.loop_2100c.n4 = N4Segment(
        city_name="WASHINGTON",
        state_or_province_code="XX",
        postal_code="20001",
    )

    result = validate(interchange, levels={SnipLevel.SNIP5})

    assert "SNIP5_INVALID_STATE_CODE" in error_codes(result)


def test_snip5_invalid_calendar_date_reports_error() -> None:
    interchange = build_interchange()
    subscriber_loop = first_subscriber_loop(interchange)
    subscriber_loop.loop_2100c.dtp_segments[0] = subscriber_loop.loop_2100c.dtp_segments[
        0
    ].model_copy(update={"date_time_period": "20260230"})

    result = validate(interchange, levels={SnipLevel.SNIP5})

    assert "SNIP5_INVALID_DATE" in error_codes(result)


def test_snip5_invalid_npi_reports_error() -> None:
    interchange = build_interchange()
    provider_loop = first_provider_loop(interchange)
    provider_loop.nm1 = provider_loop.nm1.model_copy(update={"id_code": "1234567890"})

    result = validate(interchange, levels={SnipLevel.SNIP5})

    assert "SNIP5_INVALID_NPI" in error_codes(result)


def test_dc_medicaid_receiver_id_rule_reports_error() -> None:
    interchange = build_interchange()
    interchange.isa = interchange.isa.model_copy(update={"receiver_id": "OTHERPAYER      "})

    result = validate(interchange, levels={SnipLevel.SNIP1}, profile="dc_medicaid")

    assert "DCM_INVALID_ISA08" in issue_codes(result)


def test_dc_medicaid_batch_limit_reports_error() -> None:
    interchange = build_interchange()
    transaction = interchange.functional_groups[0].transactions[0]
    interchange.functional_groups[0].transactions = [transaction] * 5001

    result = validate(interchange, levels={SnipLevel.SNIP1}, profile="dc_medicaid")

    assert "DCM_BATCH_LIMIT_EXCEEDED" in issue_codes(result)


def test_dc_medicaid_future_service_date_reports_error() -> None:
    interchange = build_interchange()
    subscriber_loop = first_subscriber_loop(interchange)
    subscriber_loop.loop_2100c.dtp_segments[0] = subscriber_loop.loop_2100c.dtp_segments[
        0
    ].model_copy(update={"date_time_period": "20260413"})

    result = validate(interchange, levels={SnipLevel.SNIP1}, profile="dc_medicaid")

    assert "DCM_FUTURE_SERVICE_DATE" in issue_codes(result)


def test_dc_medicaid_service_date_older_than_13_months_reports_error() -> None:
    interchange = build_interchange()
    subscriber_loop = first_subscriber_loop(interchange)
    subscriber_loop.loop_2100c.dtp_segments[0] = subscriber_loop.loop_2100c.dtp_segments[
        0
    ].model_copy(update={"date_time_period": "20240229"})

    result = validate(interchange, levels={SnipLevel.SNIP1}, profile="dc_medicaid")

    assert "DCM_SERVICE_DATE_TOO_OLD" in issue_codes(result)


def test_dc_medicaid_270_rejects_2110c_dtp291_without_2100c_subscriber_date() -> None:
    legacy_shape = read_fixture("270_realtime_single.x12").replace(
        "DTP*291*D8*20260412~\nEQ*30~",
        "EQ*30~\nDTP*291*D8*20260412~",
    )
    interchange = parse(legacy_shape).interchange

    result = validate(interchange, profile="dc_medicaid")

    placement_issue = next(
        issue for issue in result.issues if issue.code == "DCM_270_DTP291_REQUIRES_2100C"
    )
    assert result.is_valid is False
    assert placement_issue.level == SnipLevel.SNIP5
    assert placement_issue.segment_id == "DTP"
    assert placement_issue.element == "01"
    assert "Subscriber Eligibility/Benefit Date" in placement_issue.message
    assert "Subscriber Date" in placement_issue.message
    assert placement_issue.suggestion == (
        "Move DTP*291 before the EQ segment so it is in Loop 2100C."
    )


def test_dc_medicaid_dependent_hl_reports_error() -> None:
    interchange = build_interchange()
    subscriber_loop = first_subscriber_loop(interchange)
    subscriber_loop.hl = HLSegment.model_construct(
        **(subscriber_loop.hl.model_dump(mode="python") | {"hierarchical_level_code": "23"})
    )

    result = validate(interchange, levels={SnipLevel.SNIP1}, profile="dc_medicaid")

    assert "DCM_DEPENDENT_LOOP_NOT_ALLOWED" in issue_codes(result)


def test_dc_medicaid_invalid_search_criteria_reports_error() -> None:
    interchange = build_interchange()
    subscriber_loop = first_subscriber_loop(interchange)
    subscriber_loop.loop_2100c = subscriber_loop.loop_2100c.model_copy(
        update={
            "nm1": subscriber_loop.loop_2100c.nm1.model_copy(
                update={"first_name": None, "id_code": None, "id_code_qualifier": None}
            ),
            "dmg": None,
            "ref_segments": [],
        }
    )

    result = validate(interchange, levels={SnipLevel.SNIP1}, profile="dc_medicaid")

    assert "DCM_INVALID_SEARCH_CRITERIA" in issue_codes(result)


def test_dc_medicaid_aaa_reject_mapping_surfaces_plain_english_message() -> None:
    interchange = parse(read_fixture("271_rejected_subscriber.x12")).interchange

    result = validate(interchange, levels={SnipLevel.SNIP1}, profile="dc_medicaid")

    assert "DCM_AAA_REJECT_72" in issue_codes(result)
    assert "Invalid member ID" in find_issue(result, "DCM_AAA_REJECT_72")


def test_valid_270_fixture_passes_generic_and_profile_validation() -> None:
    interchange = parse(read_fixture("270_realtime_single.x12")).interchange

    result = validate(interchange, profile="dc_medicaid")

    assert result.is_valid
    assert result.issues == []


def test_valid_271_fixture_passes_generic_and_profile_validation() -> None:
    interchange = parse(read_fixture("271_active_response.x12")).interchange

    result = validate(interchange, profile="dc_medicaid")

    assert result.is_valid
    assert result.issues == []


def test_validate_without_profile_runs_only_snip_levels() -> None:
    interchange = parse(read_fixture("270_realtime_single.x12")).interchange
    interchange.isa = interchange.isa.model_copy(update={"receiver_id": "OTHERPAYER     "})

    result = validate(interchange)

    assert "DCM_INVALID_ISA08" not in issue_codes(result)
    assert result.is_valid


def test_validation_result_human_summary_uses_plain_english() -> None:
    interchange = build_interchange()
    interchange.iea = interchange.iea.model_copy(update={"interchange_control_number": "999999999"})

    result = validate(interchange, levels={SnipLevel.SNIP3})
    summary = result.human_readable_summary()

    assert "Validation failed" in summary
    assert "ISA13 '000000001' does not match IEA02 '999999999'" in summary
