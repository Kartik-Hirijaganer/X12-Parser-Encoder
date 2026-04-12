from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest
from pydantic import ValidationError

from x12_edi_tools import Delimiters
from x12_edi_tools.common.enums import (
    AAARejectReasonCode,
    EligibilityInfoCode,
    EntityIdentifierCode,
    GenderCode,
    HierarchicalLevelCode,
    ServiceTypeCode,
)
from x12_edi_tools.exceptions import TransactionParseError
from x12_edi_tools.models import (
    AAASegment,
    BHTSegment,
    DMGSegment,
    DTPSegment,
    EBSegment,
    EQSegment,
    FunctionalGroup,
    GenericSegment,
    GESegment,
    GSSegment,
    HLSegment,
    IEASegment,
    Interchange,
    ISASegment,
    Loop2000A_270,
    Loop2000A_271,
    Loop2000B_270,
    Loop2000C_270,
    Loop2100A_270,
    Loop2100A_271,
    Loop2100B_270,
    Loop2100C_270,
    Loop2100C_271,
    Loop2110C_270,
    Loop2110C_271,
    NM1Segment,
    SESegment,
    STSegment,
    Transaction270,
    Transaction271,
    TRNSegment,
)


def build_isa_segment() -> ISASegment:
    return ISASegment(
        authorization_information_qualifier="00",
        authorization_information="          ",
        security_information_qualifier="00",
        security_information="          ",
        sender_id_qualifier="ZZ",
        sender_id="ACMEHOMEHLTH   ",
        receiver_id_qualifier="ZZ",
        receiver_id="DCMEDICAID     ",
        interchange_date="260412",
        interchange_time="1200",
        repetition_separator="^",
        control_version_number="00501",
        interchange_control_number="000000001",
        acknowledgment_requested="0",
        usage_indicator="T",
        component_element_separator=":",
    )


def build_transaction_270() -> Transaction270:
    return Transaction270(
        st=STSegment(
            transaction_set_identifier_code="270",
            transaction_set_control_number="0001",
            implementation_convention_reference="005010X279A1",
        ),
        bht=BHTSegment(
            hierarchical_structure_code="0022",
            transaction_set_purpose_code="13",
            reference_identification="10001234",
            date="20260412",
            time="1200",
        ),
        loop_2000a=Loop2000A_270(
            hl=HLSegment(
                hierarchical_id_number="1",
                hierarchical_parent_id_number=None,
                hierarchical_level_code=HierarchicalLevelCode.INFORMATION_SOURCE,
                hierarchical_child_code="1",
            ),
            loop_2100a=Loop2100A_270(
                nm1=NM1Segment(
                    entity_identifier_code=EntityIdentifierCode.PAYER,
                    entity_type_qualifier="2",
                    last_name="DC MEDICAID",
                    id_code_qualifier="PI",
                    id_code="DCMEDICAID",
                ),
            ),
            loop_2000b=[
                Loop2000B_270(
                    hl=HLSegment(
                        hierarchical_id_number="2",
                        hierarchical_parent_id_number="1",
                        hierarchical_level_code=HierarchicalLevelCode.INFORMATION_RECEIVER,
                        hierarchical_child_code="1",
                    ),
                    loop_2100b=Loop2100B_270(
                        nm1=NM1Segment(
                            entity_identifier_code=EntityIdentifierCode.PROVIDER,
                            entity_type_qualifier="2",
                            last_name="ACME HOME HEALTH",
                            id_code_qualifier="XX",
                            id_code="1234567893",
                        ),
                    ),
                    loop_2000c=[
                        build_loop_2000c_270(),
                    ],
                ),
            ],
        ),
        se=SESegment(number_of_included_segments=12, transaction_set_control_number="0001"),
    )


def build_loop_2000c_270() -> Loop2000C_270:
    return Loop2000C_270(
        hl=HLSegment(
            hierarchical_id_number="3",
            hierarchical_parent_id_number="2",
            hierarchical_level_code=HierarchicalLevelCode.SUBSCRIBER,
            hierarchical_child_code="0",
        ),
        trn=TRNSegment(
            trace_type_code="1",
            reference_identification_1="TRACE0001",
            originating_company_identifier="9877281234",
        ),
        loop_2100c=Loop2100C_270(
            nm1=NM1Segment(
                entity_identifier_code=EntityIdentifierCode.SUBSCRIBER,
                entity_type_qualifier="1",
                last_name="DOE",
                first_name="PATIENT",
                id_code_qualifier="MI",
                id_code="000123450",
            ),
            dmg=DMGSegment(
                date_time_period_format_qualifier="D8",
                date_time_period="19900101",
                gender_code=GenderCode.FEMALE,
            ),
        ),
        loop_2110c=[
            Loop2110C_270(
                dtp_segments=[
                    DTPSegment(
                        date_time_qualifier="291",
                        date_time_period_format_qualifier="D8",
                        date_time_period="20260412",
                    ),
                ],
                eq_segments=[
                    EQSegment(service_type_code=ServiceTypeCode.HEALTH_BENEFIT_PLAN_COVERAGE)
                ],
            ),
        ],
    )


def build_interchange() -> Interchange:
    return Interchange(
        isa=build_isa_segment(),
        functional_groups=[
            FunctionalGroup(
                gs=GSSegment(
                    functional_identifier_code="HS",
                    application_sender_code="ACMEHOMEHLTH",
                    application_receiver_code="DCMEDICAID",
                    date="20260412",
                    time="1200",
                    group_control_number="1",
                    responsible_agency_code="X",
                    version_release_industry_identifier_code="005010X279A1",
                ),
                transactions=[build_transaction_270()],
                ge=GESegment(number_of_transaction_sets_included=1, group_control_number="1"),
            ),
        ],
        iea=IEASegment(
            number_of_included_functional_groups=1,
            interchange_control_number="000000001",
        ),
    )


def test_isa_segment_instantiates_with_all_fields() -> None:
    isa = build_isa_segment()

    assert isa.interchange_control_number == "000000001"
    assert isa.usage_indicator == "T"


def test_isa_segment_rejects_field_longer_than_max_width() -> None:
    with pytest.raises(ValidationError):
        ISASegment(
            authorization_information_qualifier="00",
            authorization_information="          ",
            security_information_qualifier="00",
            security_information="          ",
            sender_id_qualifier="ZZ",
            sender_id="ACMEHOMEHEALTHLONG",
            receiver_id_qualifier="ZZ",
            receiver_id="DCMEDICAID     ",
            interchange_date="260412",
            interchange_time="1200",
            repetition_separator="^",
            control_version_number="00501",
            interchange_control_number="000000001",
            acknowledgment_requested="0",
            usage_indicator="T",
            component_element_separator=":",
        )


def test_isa_segment_from_elements_round_trips_to_elements() -> None:
    elements = [
        "00",
        "          ",
        "00",
        "          ",
        "ZZ",
        "ACMEHOMEHLTH   ",
        "ZZ",
        "DCMEDICAID     ",
        "260412",
        "1200",
        "^",
        "00501",
        "000000001",
        "0",
        "T",
        ":",
    ]

    assert ISASegment.from_elements(elements).to_elements() == elements


def test_nm1_segment_payer_entity_model() -> None:
    nm1 = NM1Segment(
        entity_identifier_code=EntityIdentifierCode.PAYER,
        entity_type_qualifier="2",
        last_name="DC MEDICAID",
        id_code_qualifier="PI",
        id_code="DCMEDICAID",
    )

    assert nm1.entity_identifier_code == EntityIdentifierCode.PAYER
    assert nm1.entity_type_qualifier == "2"


def test_nm1_segment_subscriber_entity_model() -> None:
    nm1 = NM1Segment(
        entity_identifier_code=EntityIdentifierCode.SUBSCRIBER,
        entity_type_qualifier="1",
        last_name="DOE",
        first_name="PATIENT",
        middle_name="Q",
        id_code_qualifier="MI",
        id_code="000123450",
    )

    assert nm1.first_name == "PATIENT"
    assert nm1.middle_name == "Q"


def test_eb_segment_active_status() -> None:
    eb = EBSegment(
        eligibility_or_benefit_information=EligibilityInfoCode.ACTIVE_COVERAGE,
        service_type_code=ServiceTypeCode.HEALTH_BENEFIT_PLAN_COVERAGE,
        insurance_type_code="MC",
    )

    assert eb.eligibility_or_benefit_information == EligibilityInfoCode.ACTIVE_COVERAGE
    assert eb.insurance_type_code == "MC"


def test_eb_segment_copayment_monetary_amount() -> None:
    eb = EBSegment(
        eligibility_or_benefit_information=EligibilityInfoCode.CO_PAYMENT,
        service_type_code=ServiceTypeCode.HEALTH_BENEFIT_PLAN_COVERAGE,
        monetary_amount=Decimal("5.00"),
    )

    assert eb.monetary_amount == Decimal("5.00")
    assert eb.to_elements()[6] == "5.00"


def test_aaa_segment_invalid_member_id_rejection() -> None:
    aaa = AAASegment(
        response_code="N",
        reject_reason_code=AAARejectReasonCode.INVALID_MEMBER_ID,
        follow_up_action_code="C",
    )

    assert aaa.response_code == "N"
    assert aaa.reject_reason_code == AAARejectReasonCode.INVALID_MEMBER_ID


def test_loop_2000a_270_nests_loop_2000b_and_loop_2000c() -> None:
    loop_2000a = build_transaction_270().loop_2000a

    assert loop_2000a.loop_2000b[0].loop_2000c[0].loop_2100c.nm1.last_name == "DOE"


def test_transaction_270_contains_required_segments_and_loop() -> None:
    transaction = build_transaction_270()

    assert transaction.st.transaction_set_identifier_code == "270"
    assert transaction.bht.hierarchical_structure_code == "0022"
    assert transaction.loop_2000a.loop_2100a is not None
    assert transaction.se.number_of_included_segments == 12


def test_interchange_wraps_group_and_transaction() -> None:
    interchange = build_interchange()

    assert (
        interchange.functional_groups[0].transactions[0].st.transaction_set_identifier_code == "270"
    )
    assert interchange.iea.interchange_control_number == "000000001"


def test_service_type_code_values_match_phase_1_plan() -> None:
    assert {code.value for code in ServiceTypeCode} == {
        "1",
        "30",
        "33",
        "35",
        "47",
        "48",
        "50",
        "86",
        "88",
        "98",
        "AL",
        "MH",
        "UC",
    }


@pytest.mark.parametrize(
    ("segment_cls", "elements", "expected_none_fields"),
    [
        (STSegment, ["270", "0001", ""], ("implementation_convention_reference",)),
        (
            NM1Segment,
            ["IL", "1", "DOE", "PATIENT", "", "", "", "MI", ""],
            ("middle_name", "id_code"),
        ),
        (DMGSegment, ["D8", "19900101", ""], ("gender_code",)),
        (
            EBSegment,
            ["1", "", "30", "MC", "", "", "", "", "", "", "", "", ""],
            ("coverage_level_code", "plan_coverage_description", "monetary_amount"),
        ),
    ],
)
def test_from_elements_treats_trailing_empty_elements_as_none(
    segment_cls: type[object],
    elements: list[str],
    expected_none_fields: tuple[str, ...],
) -> None:
    segment = segment_cls.from_elements(elements)  # type: ignore[attr-defined]

    for field_name in expected_none_fields:
        assert getattr(segment, field_name) is None


def test_delimiters_is_frozen() -> None:
    delimiters = Delimiters()

    with pytest.raises(FrozenInstanceError):
        delimiters.element = "|"  # type: ignore[misc]


def test_generic_segment_preserves_segment_id_and_raw_elements() -> None:
    segment = GenericSegment(segment_id="III", raw_elements=["ZZ", "ABC", ""])

    assert segment.segment_id == "III"
    assert segment.raw_elements == ["ZZ", "ABC", ""]


def test_generic_segment_to_elements_returns_raw_elements_unchanged() -> None:
    segment = GenericSegment(segment_id="III", raw_elements=["ZZ", "ABC", ""])

    assert segment.to_elements() == ["ZZ", "ABC", ""]


def test_transaction_parse_error_contains_required_fields() -> None:
    error = TransactionParseError(
        transaction_index=0,
        st_control_number="0001",
        segment_position=128,
        segment_id="NM1",
        raw_segment="NM1*IL*1*DOE*PATIENT****MI*000123450",
        error="invalid_segment",
        message="The NM1 subscriber segment is invalid.",
        suggestion="Verify subscriber demographics and resubmit.",
    )

    assert set(error.__dataclass_fields__) == {
        "transaction_index",
        "st_control_number",
        "segment_position",
        "segment_id",
        "raw_segment",
        "error",
        "message",
        "suggestion",
    }


def test_transaction_271_uses_distinct_271_specific_loop_shapes() -> None:
    transaction = Transaction271(
        st=STSegment(
            transaction_set_identifier_code="271",
            transaction_set_control_number="0002",
            implementation_convention_reference="005010X279A1",
        ),
        bht=BHTSegment(
            hierarchical_structure_code="0022",
            transaction_set_purpose_code="11",
            reference_identification="10001235",
            date="20260412",
            time="1205",
        ),
        loop_2000a=Loop2000A_271(
            hl=HLSegment(
                hierarchical_id_number="1",
                hierarchical_parent_id_number=None,
                hierarchical_level_code=HierarchicalLevelCode.INFORMATION_SOURCE,
                hierarchical_child_code="1",
            ),
            loop_2100a=Loop2100A_271(
                nm1=NM1Segment(
                    entity_identifier_code=EntityIdentifierCode.PAYER,
                    entity_type_qualifier="2",
                    last_name="DC MEDICAID",
                    id_code_qualifier="PI",
                    id_code="DCMEDICAID",
                ),
            ),
            loop_2000b=[],
        ),
        se=SESegment(number_of_included_segments=8, transaction_set_control_number="0002"),
    )

    loop_2100c_271 = Loop2100C_271(
        nm1=NM1Segment(
            entity_identifier_code=EntityIdentifierCode.SUBSCRIBER,
            entity_type_qualifier="1",
            last_name="DOE",
            first_name="PATIENT",
            id_code_qualifier="MI",
            id_code="000123450",
        ),
        aaa_segments=[
            AAASegment(
                response_code="N",
                reject_reason_code=AAARejectReasonCode.INVALID_MEMBER_ID,
                follow_up_action_code="C",
            ),
        ],
    )
    loop_2110c_271 = Loop2110C_271(
        eb_segments=[
            EBSegment(
                eligibility_or_benefit_information=EligibilityInfoCode.ACTIVE_COVERAGE,
                service_type_code=ServiceTypeCode.HEALTH_BENEFIT_PLAN_COVERAGE,
                insurance_type_code="MC",
            ),
        ],
    )

    assert transaction.st.transaction_set_identifier_code == "271"
    assert (
        loop_2100c_271.aaa_segments[0].reject_reason_code == AAARejectReasonCode.INVALID_MEMBER_ID
    )
    assert loop_2110c_271.eb_segments[0].insurance_type_code == "MC"


def test_phase_1_models_serialize_to_json() -> None:
    interchange = build_interchange()

    payload = interchange.model_dump(mode="json")

    assert (
        payload["functional_groups"][0]["transactions"][0]["st"]["transaction_set_identifier_code"]
        == "270"
    )
    assert payload["delimiters"]["element"] == "*"
