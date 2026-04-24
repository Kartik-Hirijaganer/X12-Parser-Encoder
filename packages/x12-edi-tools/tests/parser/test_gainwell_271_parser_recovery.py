from __future__ import annotations

from pathlib import Path

from x12_edi_tools import parse

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _build_271_with_benefit_entity(
    entity_identifier_code: str,
    *,
    eb03: str = "30^35^47",
    per_segments: tuple[str, ...] = ("PER*IC*HELP DESK*TE*8665550000~\n",),
) -> str:
    se_segment_count = 16 + len(per_segments)
    return (
        "ISA*00*          *00*          *ZZ*ACMEHOMEHLTH   *ZZ*DCMEDICAID     "
        "*260423*1000*^*00501*000000321*0*T*:~\n"
        "GS*HS*ACMEHOMEHLTH*DCMEDICAID*20260423*1000*321*X*005010X279A1~\n"
        "ST*271*0001*005010X279A1~\n"
        "BHT*0022*11*20009999*20260423*1000~\n"
        "HL*1**20*1~\n"
        "NM1*PR*2*DC MEDICAID*****PI*DCMEDICAID~\n"
        "HL*2*1*21*1~\n"
        "NM1*1P*2*ACME HOME HEALTH*****XX*1234567893~\n"
        "HL*3*2*22*0~\n"
        "TRN*2*TRACE2120*9876543210~\n"
        "NM1*IL*1*DOE*PARSER****MI*000123450~\n"
        "DMG*D8*19900101*F~\n"
        f"EB*1**{eb03}~\n"
        "DTP*291*D8*20260423~\n"
        "LS*2120~\n"
        f"NM1*{entity_identifier_code}*2*ENTITY TEST~\n"
        f"{''.join(per_segments)}"
        "LE*2120~\n"
        f"SE*{se_segment_count}*0001~\n"
        "GE*1*321~\n"
        "IEA*1*000000321~"
    )


def test_gainwell_271_redacted_fixture_parses_all_transactions_without_collected_errors() -> None:
    result = parse(read_fixture("gainwell_271_redacted.edi"), on_error="collect")

    assert len(result.interchange.functional_groups[0].transactions) == 153
    assert result.errors == []


def test_gainwell_271_redacted_fixture_splits_composite_eb03_and_routes_2120c() -> None:
    result = parse(read_fixture("gainwell_271_redacted.edi"))

    eligibility_loop = (
        result.interchange.functional_groups[0]
        .transactions[0]
        .loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2110c[0]
    )
    eb_segment = eligibility_loop.eb_segments[0]
    benefit_entity = eligibility_loop.loop_2120c[0]

    assert eb_segment.service_type_code == "30"
    assert eb_segment.service_type_codes == [
        "30",
        "1",
        "35",
        "47",
        "48",
        "50",
        "86",
        "88",
        "AL",
        "MH",
    ]
    assert eligibility_loop.dtp_segments[0].date_time_qualifier == "291"
    assert benefit_entity.nm1.entity_identifier_code == "P5"
    assert benefit_entity.ls.loop_identifier_code == "2120"
    assert benefit_entity.le.loop_identifier_code == "2120"
    assert "ls" in benefit_entity.model_dump()
    assert "ls_segment" not in benefit_entity.model_dump()
    assert eligibility_loop.ls_segment is None
    assert eligibility_loop.le_segment is None
    assert len(benefit_entity.per_segments) == 2
    assert benefit_entity.per_segments[0].communication_number_1 == "8665550001"


def test_parser_accepts_benefit_entity_nm1_codes_inside_2120c() -> None:
    for entity_identifier_code in ("P3", "P5", "1I"):
        result = parse(_build_271_with_benefit_entity(entity_identifier_code), on_error="collect")

        eligibility_loop = (
            result.interchange.functional_groups[0]
            .transactions[0]
            .loop_2000a.loop_2000b[0]
            .loop_2000c[0]
            .loop_2110c[0]
        )

        assert result.errors == []
        assert eligibility_loop.loop_2120c[0].nm1.entity_identifier_code == entity_identifier_code


def test_parser_splits_single_and_three_element_eb03_values() -> None:
    for eb03, expected in (("30", ["30"]), ("30^35^47", ["30", "35", "47"])):
        result = parse(_build_271_with_benefit_entity("P5", eb03=eb03), on_error="collect")
        eligibility_loop = (
            result.interchange.functional_groups[0]
            .transactions[0]
            .loop_2000a.loop_2000b[0]
            .loop_2000c[0]
            .loop_2110c[0]
        )
        eb_segment = eligibility_loop.eb_segments[0]

        assert result.errors == []
        assert eb_segment.service_type_code == expected[0]
        assert eb_segment.service_type_codes == expected


def test_parser_caps_2120c_per_segments_at_three() -> None:
    result = parse(
        _build_271_with_benefit_entity(
            "P5",
            per_segments=(
                "PER*IC*HELP DESK 1*TE*8665550001~\n",
                "PER*IC*HELP DESK 2*TE*8665550002~\n",
                "PER*IC*HELP DESK 3*TE*8665550003~\n",
                "PER*IC*HELP DESK 4*TE*8665550004~\n",
            ),
        ),
        on_error="collect",
    )
    benefit_entity = (
        result.interchange.functional_groups[0]
        .transactions[0]
        .loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2110c[0]
        .loop_2120c[0]
    )

    assert result.errors == []
    assert [per.communication_number_1 for per in benefit_entity.per_segments] == [
        "8665550001",
        "8665550002",
        "8665550003",
    ]


def test_parser_accepts_supplemental_eb01_codes_from_gainwell_fixture() -> None:
    result = parse(read_fixture("gainwell_271_redacted.edi"))

    transactions = result.interchange.functional_groups[0].transactions
    eb01_values = {
        transactions[index]
        .loop_2000a.loop_2000b[0]
        .loop_2000c[0]
        .loop_2110c[0]
        .eb_segments[0]
        .eligibility_or_benefit_information
        for index in (136, 137, 138, 139)
    }

    assert eb01_values == {"R", "L", "MC", "B"}
