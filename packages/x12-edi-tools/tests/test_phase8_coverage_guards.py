from __future__ import annotations

import sys
from pathlib import Path

import pytest

from test_phase1_models import build_interchange
from x12_edi_tools import Delimiters, SnipLevel, parse, validate
from x12_edi_tools.common.enums import GenderCode
from x12_edi_tools.config import SubmitterConfig
from x12_edi_tools.convenience import build_270, from_csv, from_excel, read_271
from x12_edi_tools.exceptions import X12ParseError, X12ValidationError
from x12_edi_tools.models.base import GenericSegment
from x12_edi_tools.models.segments import (
    AAASegment,
    DTPSegment,
    LESegment,
    LSSegment,
    N3Segment,
    N4Segment,
    PERSegment,
    PRVSegment,
    REFSegment,
)
from x12_edi_tools.payers import get_profile, list_profiles
from x12_edi_tools.payers.dc_medicaid.search_criteria import evaluate_search_criteria
from x12_edi_tools.validator.base import (
    ValidationResult,
    as_list,
    count_transaction_segments,
    issue,
    iter_transaction_body_segments,
    iter_transactions,
    normalize_str,
    parse_date_yymmdd,
    parse_date_yyyymmdd,
    subtract_months,
)

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_delimiters_validate_character_width_and_aliases() -> None:
    delimiters = Delimiters(element="|", sub_element=":", segment="!", repetition="~")

    assert delimiters.element_separator == "|"
    assert delimiters.component_separator == ":"
    assert delimiters.segment_terminator == "!"
    assert delimiters.repetition_separator == "~"

    with pytest.raises(ValueError):
        Delimiters(element="**")


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("provider_npi", "NOTNUMERIC", "provider_npi must contain only digits"),
        ("provider_entity_type", "3", "provider_entity_type must be '1' or '2'"),
        ("usage_indicator", "X", "usage_indicator must be 'T' or 'P'"),
        ("acknowledgment_requested", "9", "acknowledgment_requested must be '0' or '1'"),
    ],
)
def test_submitter_config_validators(field: str, value: str, expected: str) -> None:
    payload = {
        "organization_name": "ACME HOME HEALTH",
        "provider_npi": "1234567893",
        "trading_partner_id": "ACMETP01",
        "payer_name": "DC MEDICAID",
        "payer_id": "DCMEDICAID",
        "interchange_receiver_id": "DCMEDICAID",
    }
    payload[field] = value

    with pytest.raises(ValueError, match=expected):
        SubmitterConfig(**payload)


def test_submitter_config_accepts_explicit_valid_control_flags() -> None:
    config = SubmitterConfig(
        organization_name="ACME HOME HEALTH",
        provider_npi="1234567893",
        provider_entity_type="1",
        trading_partner_id="ACMETP01",
        payer_name="DC MEDICAID",
        payer_id="DCMEDICAID",
        interchange_receiver_id="DCMEDICAID",
        usage_indicator="P",
        acknowledgment_requested="1",
    )

    assert config.provider_entity_type == "1"
    assert config.usage_indicator == "P"
    assert config.acknowledgment_requested == "1"


@pytest.mark.parametrize("function", [from_csv, from_excel, read_271])
def test_convenience_rejects_missing_source_files(function) -> None:
    with pytest.raises(X12ValidationError, match="does not exist"):
        function(FIXTURES / "no_such_file.csv")  # type: ignore[misc]


def test_build_270_requires_at_least_one_patient() -> None:
    from x12_edi_tools.exceptions import X12EncodeError

    config = SubmitterConfig(
        organization_name="ACME HOME HEALTH",
        provider_npi="1234567893",
        trading_partner_id="ACMETP01",
        payer_name="DC MEDICAID",
        payer_id="DCMEDICAID",
        interchange_receiver_id="DCMEDICAID",
    )

    with pytest.raises(X12EncodeError, match="requires at least one patient"):
        build_270([], config=config, profile="dc_medicaid")


def test_payer_registry_and_search_criteria_helpers() -> None:
    interchange = build_interchange()
    subscriber_loop = (
        interchange.functional_groups[0].transactions[0].loop_2000a.loop_2000b[0].loop_2000c[0]
    )
    subscriber_loop.loop_2100c.ref_segments.append(
        REFSegment(
            reference_identification_qualifier="SY",
            reference_identification="111223333",
        )
    )

    criteria = evaluate_search_criteria(subscriber_loop)

    assert "dc_medicaid" in list_profiles()
    assert get_profile("DC_MEDICAID").name == "dc_medicaid"
    assert criteria.is_valid is True
    assert criteria.describe() == "member ID, name, DOB, SSN"

    with pytest.raises(X12ValidationError, match="Unknown payer profile"):
        get_profile("missing")


def test_validation_base_helpers_cover_summary_and_dates() -> None:
    result = ValidationResult(
        issues=[
            issue(level=SnipLevel.SNIP1, code="ERR", message="bad", suggestion="fix"),
            issue(level=SnipLevel.SNIP2, severity="warning", code="WARN", message="warn"),
            issue(level=SnipLevel.SNIP3, severity="info", code="INFO", message="note"),
        ]
    )

    assert result.is_valid is False
    assert result.error_count == 1
    assert result.warning_count == 1
    assert result.info_count == 1
    assert len(result.errors) == 1
    assert len(result.warnings) == 1
    assert len(result.infos) == 1
    assert "Validation failed" in result.human_readable_summary()
    assert ValidationResult().human_readable_summary() == "Validation passed with no issues."
    with pytest.raises(X12ValidationError, match="optional pandas extra"):
        result.to_dataframe()

    assert SnipLevel.from_value(1) is SnipLevel.SNIP1
    assert SnipLevel.from_value("2") is SnipLevel.SNIP2
    assert SnipLevel.from_value("snip3") is SnipLevel.SNIP3
    with pytest.raises(ValueError):
        SnipLevel.from_value(9)
    with pytest.raises(ValueError):
        SnipLevel.from_value("unknown")

    assert as_list((1, 2)) == [1, 2]
    assert as_list("x") == []
    assert normalize_str(GenderCode.FEMALE) == "F"
    assert normalize_str(None) is None
    assert parse_date_yyyymmdd("20260412").isoformat() == "2026-04-12"
    assert parse_date_yyyymmdd("20260230") is None
    assert parse_date_yymmdd("260412").isoformat() == "2026-04-12"
    assert parse_date_yymmdd("bad") is None
    assert parse_date_yymmdd("991332") is None
    assert subtract_months(parse_date_yyyymmdd("20260331"), 1).isoformat() == "2026-02-28"


def test_validation_result_to_dataframe_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class _PandasStub:
        @staticmethod
        def DataFrame(rows):
            return {"rows": rows}

    monkeypatch.setitem(sys.modules, "pandas", _PandasStub())
    dataframe = ValidationResult(
        issues=[issue(level=SnipLevel.SNIP1, code="ERR", message="bad")]
    ).to_dataframe()

    assert dataframe["rows"][0]["code"] == "ERR"


def test_transaction_body_iteration_supports_270_and_271() -> None:
    interchange_270 = build_interchange()
    transaction_270 = interchange_270.functional_groups[0].transactions[0]
    subscriber_270 = transaction_270.loop_2000a.loop_2000b[0].loop_2000c[0]
    inquiry_270 = subscriber_270.loop_2110c[0]
    transaction_270 = transaction_270.model_copy(
        update={
            "loop_2000a": transaction_270.loop_2000a.model_copy(
                update={
                    "loop_2100a": transaction_270.loop_2000a.loop_2100a.model_copy(
                        update={
                            "ref_segments": [
                                REFSegment(
                                    reference_identification_qualifier="2U",
                                    reference_identification="PAYERREF",
                                )
                            ]
                        }
                    ),
                    "loop_2000b": [
                        transaction_270.loop_2000a.loop_2000b[0].model_copy(
                            update={
                                "loop_2100b": transaction_270.loop_2000a.loop_2000b[
                                    0
                                ].loop_2100b.model_copy(
                                    update={
                                        "prv": PRVSegment(
                                            provider_code="PE",
                                            reference_identification_qualifier="ZZ",
                                            reference_identification="207Q00000X",
                                        ),
                                        "per": PERSegment(
                                            contact_function_code="IC",
                                            name="HELP DESK",
                                            communication_number_qualifier_1="TE",
                                            communication_number_1="2025551212",
                                        ),
                                        "n3": N3Segment(address_information_1="123 MAIN ST"),
                                        "n4": N4Segment(
                                            city_name="WASHINGTON",
                                            state_or_province_code="DC",
                                            postal_code="20001",
                                        ),
                                        "ref_segments": [
                                            REFSegment(
                                                reference_identification_qualifier="EI",
                                                reference_identification="991234567",
                                            )
                                        ],
                                    }
                                ),
                                "loop_2000c": [
                                    subscriber_270.model_copy(
                                        update={
                                            "loop_2100c": subscriber_270.loop_2100c.model_copy(
                                                update={
                                                    "ref_segments": [
                                                        REFSegment(
                                                            reference_identification_qualifier="SY",
                                                            reference_identification="111223333",
                                                        )
                                                    ]
                                                }
                                            ),
                                            "loop_2110c": [
                                                inquiry_270.model_copy(
                                                    update={
                                                        "ref_segments": [
                                                            REFSegment(
                                                                reference_identification_qualifier="6P",
                                                                reference_identification="TRACE",
                                                            )
                                                        ]
                                                    }
                                                )
                                            ],
                                        }
                                    )
                                ],
                            }
                        )
                    ],
                }
            )
        }
    )

    transaction_271 = (
        parse(read_fixture("271_active_response.x12"))
        .interchange.functional_groups[0]
        .transactions[0]
    )
    receiver_271 = transaction_271.loop_2000a.loop_2000b[0]
    subscriber_271 = receiver_271.loop_2000c[0]
    inquiry_271 = subscriber_271.loop_2110c[0]
    transaction_271 = transaction_271.model_copy(
        update={
            "loop_2000a": transaction_271.loop_2000a.model_copy(
                update={
                    "aaa_segments": [
                        AAASegment(
                            response_code="N",
                            reject_reason_code="71",
                            follow_up_action_code="C",
                        )
                    ],
                    "loop_2100a": transaction_271.loop_2000a.loop_2100a.model_copy(
                        update={
                            "aaa_segments": [
                                AAASegment(
                                    response_code="N",
                                    reject_reason_code="72",
                                    follow_up_action_code="C",
                                )
                            ],
                            "ref_segments": [
                                REFSegment(
                                    reference_identification_qualifier="2U",
                                    reference_identification="PAYER271",
                                )
                            ],
                        }
                    ),
                    "loop_2000b": [
                        receiver_271.model_copy(
                            update={
                                "aaa_segments": [
                                    AAASegment(
                                        response_code="N",
                                        reject_reason_code="71",
                                        follow_up_action_code="C",
                                    )
                                ],
                                "loop_2100b": receiver_271.loop_2100b.model_copy(
                                    update={
                                        "per": PERSegment(
                                            contact_function_code="IC",
                                            name="HELP DESK",
                                            communication_number_qualifier_1="TE",
                                            communication_number_1="2025551313",
                                        ),
                                        "n3": N3Segment(address_information_1="500 PAYER AVE"),
                                        "n4": N4Segment(
                                            city_name="WASHINGTON",
                                            state_or_province_code="DC",
                                            postal_code="20001",
                                        ),
                                        "ref_segments": [
                                            REFSegment(
                                                reference_identification_qualifier="TJ",
                                                reference_identification="271REF",
                                            )
                                        ],
                                    }
                                ),
                                "loop_2000c": [
                                    subscriber_271.model_copy(
                                        update={
                                            "aaa_segments": [
                                                AAASegment(
                                                    response_code="N",
                                                    reject_reason_code="71",
                                                    follow_up_action_code="C",
                                                )
                                            ],
                                            "loop_2100c": subscriber_271.loop_2100c.model_copy(
                                                update={
                                                    "n3": N3Segment(
                                                        address_information_1="400 MEMBER RD"
                                                    ),
                                                    "n4": N4Segment(
                                                        city_name="WASHINGTON",
                                                        state_or_province_code="DC",
                                                        postal_code="20002",
                                                    ),
                                                    "aaa_segments": [
                                                        AAASegment(
                                                            response_code="N",
                                                            reject_reason_code="72",
                                                            follow_up_action_code="C",
                                                        )
                                                    ],
                                                    "ref_segments": [
                                                        REFSegment(
                                                            reference_identification_qualifier="6P",
                                                            reference_identification="SUBREF",
                                                        )
                                                    ],
                                                }
                                            ),
                                            "loop_2110c": [
                                                inquiry_271.model_copy(
                                                    update={
                                                        "aaa_segments": [
                                                            AAASegment(
                                                                response_code="N",
                                                                reject_reason_code="71",
                                                                follow_up_action_code="C",
                                                            )
                                                        ],
                                                        "ls_segment": LSSegment(
                                                            loop_identifier_code="2120"
                                                        ),
                                                        "le_segment": LESegment(
                                                            loop_identifier_code="2120"
                                                        ),
                                                        "ref_segments": [
                                                            REFSegment(
                                                                reference_identification_qualifier="N6",
                                                                reference_identification="PLAN271",
                                                            )
                                                        ],
                                                        "dtp_segments": [
                                                            DTPSegment(
                                                                date_time_qualifier="291",
                                                                date_time_period_format_qualifier="D8",
                                                                date_time_period="20260412",
                                                            )
                                                        ],
                                                    }
                                                )
                                            ],
                                        }
                                    )
                                ],
                            }
                        )
                    ],
                }
            )
        }
    )

    assert count_transaction_segments(transaction_270) == 21
    assert any(
        segment.segment_id == "EQ" for segment in iter_transaction_body_segments(transaction_270)
    )
    assert any(
        segment.segment_id == "PRV" for segment in iter_transaction_body_segments(transaction_270)
    )
    assert any(
        segment.segment_id == "EB" for segment in iter_transaction_body_segments(transaction_271)
    )
    assert any(
        segment.segment_id == "AAA" for segment in iter_transaction_body_segments(transaction_271)
    )
    assert any(
        segment.segment_id == "REF" for segment in iter_transaction_body_segments(transaction_271)
    )
    assert any(
        segment.segment_id == "DTP" for segment in iter_transaction_body_segments(transaction_271)
    )
    assert any(
        segment.segment_id == "LS" for segment in iter_transaction_body_segments(transaction_271)
    )


def test_iter_transactions_skips_non_functional_groups() -> None:
    interchange = build_interchange().model_copy(
        update={"functional_groups": [object(), build_interchange().functional_groups[0]]}
    )

    contexts = list(iter_transactions(interchange))

    assert len(contexts) == 1
    assert contexts[0].functional_group_index == 1


def test_parse_rejects_invalid_error_mode_and_trailer_shapes() -> None:
    with pytest.raises(ValueError, match="on_error must be one of"):
        parse(read_fixture("270_realtime_single.x12"), on_error="bad-mode")  # type: ignore[arg-type]

    with pytest.raises(X12ParseError, match="missing the IEA trailer"):
        parse(read_fixture("270_realtime_single.x12").replace("IEA*1*000000001~", ""))

    with pytest.raises(X12ParseError, match="Unexpected segments found after the IEA trailer"):
        parse(read_fixture("270_realtime_single.x12") + "REF*ZZ*TRAILER~")

    malformed = read_fixture("270_realtime_single.x12").replace(
        "ISA*00*",
        "ISA^00*",
        1,
    )
    with pytest.raises(X12ParseError, match="ISA segment is malformed"):
        parse(malformed)


def test_snip1_covers_missing_envelope_segments_and_unknown_generics() -> None:
    interchange = build_interchange()
    transaction = (
        interchange.functional_groups[0]
        .transactions[0]
        .model_copy(
            update={
                "st": None,
                "se": None,
                "generic_segments": [GenericSegment(segment_id="ZZZ", raw_elements=["1"])],
            }
        )
    )
    interchange.functional_groups[0] = interchange.functional_groups[0].model_copy(
        update={"gs": None, "ge": None, "transactions": [transaction]}
    )

    result = validate(interchange, levels={SnipLevel.SNIP1})
    codes = {issue.code for issue in result.issues}

    assert "SNIP1_MISSING_GS" in codes
    assert "SNIP1_MISSING_GE" in codes
    assert "SNIP1_MISSING_ST" in codes
    assert "SNIP1_MISSING_SE" in codes
    assert "SNIP1_UNKNOWN_SEGMENT_ID" in codes


def test_snip5_covers_dates_gender_and_service_type_rules() -> None:
    interchange = build_interchange()
    transaction = interchange.functional_groups[0].transactions[0]
    subscriber_loop = transaction.loop_2000a.loop_2000b[0].loop_2000c[0]
    inquiry_loop = subscriber_loop.loop_2110c[0]
    updated_dmg = subscriber_loop.loop_2100c.dmg.model_copy(
        update={
            "date_time_period": "20260230",
            "gender_code": "X",
        }
    )
    updated_dtp = inquiry_loop.dtp_segments[0].model_copy(
        update={
            "date_time_period_format_qualifier": "RD8",
            "date_time_period": "20260101-bad",
        }
    )

    interchange.isa = interchange.isa.model_copy(update={"interchange_date": "260231"})
    interchange.functional_groups[0].gs = interchange.functional_groups[0].gs.model_copy(
        update={"date": "20260230"}
    )
    interchange.functional_groups[0].transactions[0] = transaction.model_copy(
        update={
            "bht": transaction.bht.model_copy(update={"date": "20260230"}),
            "loop_2000a": transaction.loop_2000a.model_copy(
                update={
                    "loop_2000b": [
                        transaction.loop_2000a.loop_2000b[0].model_copy(
                            update={
                                "loop_2000c": [
                                    subscriber_loop.model_copy(
                                        update={
                                            "loop_2100c": subscriber_loop.loop_2100c.model_copy(
                                                update={"dmg": updated_dmg}
                                            ),
                                            "loop_2110c": [
                                                inquiry_loop.model_copy(
                                                    update={
                                                        "eq_segments": [
                                                            inquiry_loop.eq_segments[0].model_copy(
                                                                update={"service_type_code": "ZZ"}
                                                            )
                                                        ],
                                                        "dtp_segments": [updated_dtp],
                                                    }
                                                )
                                            ],
                                        }
                                    )
                                ]
                            }
                        )
                    ]
                }
            ),
        }
    )

    result = validate(interchange, levels={SnipLevel.SNIP5})
    codes = {issue.code for issue in result.issues}

    assert "SNIP5_INVALID_DATE" in codes
    assert "SNIP5_INVALID_GENDER_CODE" in codes
    assert "SNIP5_INVALID_SERVICE_TYPE_CODE" in codes


def test_snip5_covers_271_eb_service_type_branch() -> None:
    interchange = parse(read_fixture("271_active_response.x12")).interchange
    inquiry = (
        interchange.functional_groups[0]
        .transactions[0]
        .loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2110c[0]
    )
    inquiry.eb_segments[0] = inquiry.eb_segments[0].model_copy(update={"service_type_code": "ZZ"})

    result = validate(interchange, levels={SnipLevel.SNIP5})

    assert any(issue.code == "SNIP5_INVALID_SERVICE_TYPE_CODE" for issue in result.issues)
