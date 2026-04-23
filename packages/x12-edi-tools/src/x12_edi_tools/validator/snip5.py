"""Generic SNIP level 5 validation."""

from __future__ import annotations

from x12_edi_tools.common.enums import GenderCode, ServiceTypeCode
from x12_edi_tools.models.loops import (
    Loop2000A_270,
    Loop2000A_271,
    Loop2000B_270,
    Loop2000B_271,
    Loop2000C_270,
    Loop2000C_271,
)
from x12_edi_tools.models.segments import (
    DMGSegment,
    DTPSegment,
    EBSegment,
    EQSegment,
    N4Segment,
    NM1Segment,
)
from x12_edi_tools.models.transactions import (
    FunctionalGroup,
    Interchange,
    Transaction270,
    Transaction271,
)
from x12_edi_tools.validator.base import (
    SnipLevel,
    TransactionContext,
    ValidationError,
    annotate_transaction_issues,
    as_list,
    issue,
    normalize_str,
    parse_date_yymmdd,
    parse_date_yyyymmdd,
)

VALID_GENDER_CODES = {member.value for member in GenderCode}
VALID_SERVICE_TYPE_CODES = {member.value for member in ServiceTypeCode}
VALID_US_STATE_CODES = {
    "AL",
    "AK",
    "AS",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DC",
    "DE",
    "FL",
    "GA",
    "GU",
    "HI",
    "IA",
    "ID",
    "IL",
    "IN",
    "KS",
    "KY",
    "LA",
    "MA",
    "MD",
    "ME",
    "MI",
    "MN",
    "MO",
    "MP",
    "MS",
    "MT",
    "NC",
    "ND",
    "NE",
    "NH",
    "NJ",
    "NM",
    "NV",
    "NY",
    "OH",
    "OK",
    "OR",
    "PA",
    "PR",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VA",
    "VI",
    "VT",
    "WA",
    "WI",
    "WV",
    "WY",
}


def validate_snip5(interchange: Interchange) -> list[ValidationError]:
    """Validate external code-set and semantic-date rules."""

    issues: list[ValidationError] = []

    issues.extend(_validate_envelope_dates(interchange))

    for group_index, group in enumerate(as_list(getattr(interchange, "functional_groups", []))):
        if not isinstance(group, FunctionalGroup):
            continue

        gs_date = normalize_str(getattr(getattr(group, "gs", None), "date", None))
        if gs_date and parse_date_yyyymmdd(gs_date) is None:
            issues.append(
                issue(
                    level=SnipLevel.SNIP5,
                    code="SNIP5_INVALID_DATE",
                    message=f"GS04 date '{gs_date}' is not a valid calendar date.",
                    location=f"FunctionalGroup[{group_index}].GS.04",
                    segment_id="GS",
                    element="04",
                    suggestion="Use a real YYYYMMDD calendar date in GS04.",
                )
            )

        for transaction_index, transaction in enumerate(as_list(group.transactions)):
            if not isinstance(transaction, Transaction270 | Transaction271):
                continue
            tx_context = TransactionContext(
                functional_group_index=group_index,
                transaction_index=transaction_index,
                transaction=transaction,
            )
            issues.extend(
                annotate_transaction_issues(
                    _validate_transaction_codes(transaction, group_index, transaction_index),
                    tx_context,
                )
            )

    return issues


def _validate_envelope_dates(interchange: Interchange) -> list[ValidationError]:
    issues: list[ValidationError] = []
    isa_date = normalize_str(getattr(getattr(interchange, "isa", None), "interchange_date", None))
    if isa_date and parse_date_yymmdd(isa_date) is None:
        issues.append(
            issue(
                level=SnipLevel.SNIP5,
                code="SNIP5_INVALID_DATE",
                message=f"ISA09 date '{isa_date}' is not a valid calendar date.",
                location="ISA.09",
                segment_id="ISA",
                element="09",
                suggestion="Use a real YYMMDD calendar date in ISA09.",
            )
        )
    return issues


def _validate_transaction_codes(
    transaction: Transaction270 | Transaction271,
    group_index: int,
    transaction_index: int,
) -> list[ValidationError]:
    issues: list[ValidationError] = []
    prefix = f"FunctionalGroup[{group_index}].Transaction[{transaction_index}]"

    bht_date = normalize_str(getattr(getattr(transaction, "bht", None), "date", None))
    if bht_date and parse_date_yyyymmdd(bht_date) is None:
        issues.append(
            issue(
                level=SnipLevel.SNIP5,
                code="SNIP5_INVALID_DATE",
                message=f"BHT04 date '{bht_date}' is not a valid calendar date.",
                location=f"{prefix}.BHT.04",
                segment_id="BHT",
                element="04",
                suggestion="Use a real YYYYMMDD calendar date in BHT04.",
            )
        )

    if isinstance(transaction, Transaction270):
        loop_2000a = getattr(transaction, "loop_2000a", None)
        if isinstance(loop_2000a, Loop2000A_270):
            for receiver_index, receiver_loop in enumerate(as_list(loop_2000a.loop_2000b)):
                if not isinstance(receiver_loop, Loop2000B_270):
                    continue
                issues.extend(
                    _validate_nm1_npi(
                        getattr(getattr(receiver_loop, "loop_2100b", None), "nm1", None),
                        location=f"{prefix}.Loop2000B[{receiver_index}].Loop2100B.NM1",
                    )
                )
                issues.extend(
                    _validate_n4(
                        getattr(getattr(receiver_loop, "loop_2100b", None), "n4", None),
                        location=f"{prefix}.Loop2000B[{receiver_index}].Loop2100B.N4",
                    )
                )
                for subscriber_index, subscriber_loop in enumerate(
                    as_list(receiver_loop.loop_2000c)
                ):
                    if not isinstance(subscriber_loop, Loop2000C_270):
                        continue
                    subscriber_prefix = (
                        f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}]"
                    )
                    issues.extend(
                        _validate_dmg(
                            subscriber_loop.loop_2100c.dmg,
                            location=f"{subscriber_prefix}.Loop2100C.DMG",
                        )
                    )
                    issues.extend(
                        _validate_2110c_codes(
                            subscriber_loop.loop_2100c,
                            location=f"{subscriber_prefix}.Loop2100C",
                        )
                    )
                    for inquiry_index, inquiry_loop in enumerate(
                        as_list(subscriber_loop.loop_2110c)
                    ):
                        issues.extend(
                            _validate_2110c_codes(
                                inquiry_loop,
                                location=(f"{subscriber_prefix}.Loop2110C[{inquiry_index}]"),
                            )
                        )
        return issues

    loop_2000a = getattr(transaction, "loop_2000a", None)
    if isinstance(loop_2000a, Loop2000A_271):
        for receiver_index, receiver_loop in enumerate(as_list(loop_2000a.loop_2000b)):
            if not isinstance(receiver_loop, Loop2000B_271):
                continue
            issues.extend(
                _validate_nm1_npi(
                    getattr(getattr(receiver_loop, "loop_2100b", None), "nm1", None),
                    location=f"{prefix}.Loop2000B[{receiver_index}].Loop2100B.NM1",
                )
            )
            issues.extend(
                _validate_n4(
                    getattr(getattr(receiver_loop, "loop_2100b", None), "n4", None),
                    location=f"{prefix}.Loop2000B[{receiver_index}].Loop2100B.N4",
                )
            )
            for subscriber_index, subscriber_loop in enumerate(as_list(receiver_loop.loop_2000c)):
                if not isinstance(subscriber_loop, Loop2000C_271):
                    continue
                issues.extend(
                    _validate_dmg(
                        getattr(getattr(subscriber_loop, "loop_2100c", None), "dmg", None),
                        location=(
                            f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                            f"[{subscriber_index}].Loop2100C.DMG"
                        ),
                    )
                )
                issues.extend(
                    _validate_n4(
                        getattr(getattr(subscriber_loop, "loop_2100c", None), "n4", None),
                        location=(
                            f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                            f"[{subscriber_index}].Loop2100C.N4"
                        ),
                    )
                )
                for inquiry_index, inquiry_loop in enumerate(as_list(subscriber_loop.loop_2110c)):
                    issues.extend(
                        _validate_2110c_codes(
                            inquiry_loop,
                            location=(
                                f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                                f"[{subscriber_index}].Loop2110C[{inquiry_index}]"
                            ),
                        )
                    )

    return issues


def _validate_n4(n4: object, *, location: str) -> list[ValidationError]:
    if not isinstance(n4, N4Segment):
        return []
    state = normalize_str(getattr(n4, "state_or_province_code", None))
    if not state or state in VALID_US_STATE_CODES:
        return []
    return [
        issue(
            level=SnipLevel.SNIP5,
            code="SNIP5_INVALID_STATE_CODE",
            message=f"State code '{state}' is not a valid US state or territory code.",
            location=f"{location}.02",
            segment_id="N4",
            element="02",
            suggestion="Use a valid two-letter USPS state or territory code.",
        )
    ]


def _validate_dmg(dmg: object, *, location: str) -> list[ValidationError]:
    if not isinstance(dmg, DMGSegment):
        return []
    issues: list[ValidationError] = []

    fmt = normalize_str(getattr(dmg, "date_time_period_format_qualifier", None))
    period = normalize_str(getattr(dmg, "date_time_period", None))
    if fmt == "D8" and period and parse_date_yyyymmdd(period) is None:
        issues.append(
            issue(
                level=SnipLevel.SNIP5,
                code="SNIP5_INVALID_DATE",
                message=f"DMG02 date '{period}' is not a valid calendar date.",
                location=f"{location}.02",
                segment_id="DMG",
                element="02",
                suggestion="Use a real YYYYMMDD birth date in DMG02.",
            )
        )

    gender = normalize_str(getattr(dmg, "gender_code", None))
    if gender and gender not in VALID_GENDER_CODES:
        issues.append(
            issue(
                level=SnipLevel.SNIP5,
                code="SNIP5_INVALID_GENDER_CODE",
                message=f"Gender code '{gender}' is not valid for DMG03.",
                location=f"{location}.03",
                segment_id="DMG",
                element="03",
                suggestion="Use F, M, or U in DMG03.",
            )
        )

    return issues


def _validate_2110c_codes(loop: object, *, location: str) -> list[ValidationError]:
    issues: list[ValidationError] = []

    for eq_index, eq_segment in enumerate(as_list(getattr(loop, "eq_segments", []))):
        if not isinstance(eq_segment, EQSegment):
            continue
        service_type = normalize_str(getattr(eq_segment, "service_type_code", None))
        if service_type not in VALID_SERVICE_TYPE_CODES:
            issues.append(
                issue(
                    level=SnipLevel.SNIP5,
                    code="SNIP5_INVALID_SERVICE_TYPE_CODE",
                    message=f"Service type code '{service_type or ''}' is not valid in EQ01.",
                    location=f"{location}.EQ[{eq_index}].01",
                    segment_id="EQ",
                    element="01",
                    suggestion="Use one of the supported X12 service type codes.",
                )
            )

    for eb_index, eb_segment in enumerate(as_list(getattr(loop, "eb_segments", []))):
        if not isinstance(eb_segment, EBSegment):
            continue
        service_type = normalize_str(getattr(eb_segment, "service_type_code", None))
        if service_type is not None and service_type not in VALID_SERVICE_TYPE_CODES:
            issues.append(
                issue(
                    level=SnipLevel.SNIP5,
                    code="SNIP5_INVALID_SERVICE_TYPE_CODE",
                    message=f"Service type code '{service_type}' is not valid in EB03.",
                    location=f"{location}.EB[{eb_index}].03",
                    segment_id="EB",
                    element="03",
                    suggestion="Use one of the supported X12 service type codes.",
                )
            )

    for dtp_index, dtp_segment in enumerate(as_list(getattr(loop, "dtp_segments", []))):
        if not isinstance(dtp_segment, DTPSegment):
            continue
        qualifier = normalize_str(getattr(dtp_segment, "date_time_period_format_qualifier", None))
        period = normalize_str(getattr(dtp_segment, "date_time_period", None))
        if qualifier == "D8" and period and parse_date_yyyymmdd(period) is None:
            issues.append(
                issue(
                    level=SnipLevel.SNIP5,
                    code="SNIP5_INVALID_DATE",
                    message=f"DTP03 date '{period}' is not a valid calendar date.",
                    location=f"{location}.DTP[{dtp_index}].03",
                    segment_id="DTP",
                    element="03",
                    suggestion="Use a real YYYYMMDD date in DTP03.",
                )
            )
        if qualifier == "RD8" and period:
            try:
                start_text, end_text = period.split("-", maxsplit=1)
            except ValueError:
                continue
            start = parse_date_yyyymmdd(start_text)
            end = parse_date_yyyymmdd(end_text)
            if start is None or end is None:
                issues.append(
                    issue(
                        level=SnipLevel.SNIP5,
                        code="SNIP5_INVALID_DATE",
                        message=f"DTP03 range '{period}' is not a valid calendar date range.",
                        location=f"{location}.DTP[{dtp_index}].03",
                        segment_id="DTP",
                        element="03",
                        suggestion="Use YYYYMMDD-YYYYMMDD when DTP02 is RD8.",
                    )
                )

    return issues


def _validate_nm1_npi(nm1: object, *, location: str) -> list[ValidationError]:
    if not isinstance(nm1, NM1Segment):
        return []
    qualifier = normalize_str(getattr(nm1, "id_code_qualifier", None))
    identifier = normalize_str(getattr(nm1, "id_code", None))
    if qualifier != "XX" or not identifier:
        return []
    if len(identifier) != 10 or not identifier.isdigit() or not _is_valid_npi(identifier):
        return [
            issue(
                level=SnipLevel.SNIP5,
                code="SNIP5_INVALID_NPI",
                message=f"NPI '{identifier}' is not valid for NM109.",
                location=f"{location}.09",
                segment_id="NM1",
                element="09",
                suggestion="Use a 10-digit NPI that passes the standard Luhn check.",
            )
        ]
    return []


def _is_valid_npi(npi: str) -> bool:
    body = "80840" + npi[:9]
    total = 0
    for index, character in enumerate(reversed(body), start=1):
        digit = int(character)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(npi[-1])
