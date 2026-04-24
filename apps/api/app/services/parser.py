"""271 projection services."""

from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from x12_edi_tools import parse
from x12_edi_tools.exceptions import TransactionParseError, X12ParseError
from x12_edi_tools.models.loops import Loop2000B_271, Loop2000C_271, Loop2110C_271
from x12_edi_tools.models.transactions import Transaction271
from x12_edi_tools.payers.dc_medicaid.constants import AAA_REASON_MESSAGES, AAA_REASON_SUGGESTIONS
from x12_edi_tools.validator.base import as_list

from app.core.logging import get_logger
from app.core.metrics import (
    PARSER_ACCOUNTING_MISMATCH_TOTAL,
    observe_record_count,
    observe_segment_count,
)
from app.schemas.common import (
    AAAError,
    BenefitEntity,
    EligibilityResult,
    EligibilitySegment,
    EligibilitySummary,
)
from app.schemas.parse import ParseResponse, ParserIssue
from app.services.validator import harden_x12_payload

_ACTIVE_CODES = {"1", "2", "3", "4", "5"}
_INACTIVE_CODES = {"6", "7", "8"}
_SUPPLEMENTAL_CODES = {"B", "F", "J", "L", "N", "R", "MC"}
logger = get_logger(__name__)


def parse_271_document(
    *,
    filename: str,
    raw_x12: str,
    correlation_id: str | None = None,
    metrics_path: str = "/api/v1/parse",
) -> ParseResponse:
    """Parse a 271 payload into dashboard-oriented API data."""

    harden_x12_payload(raw_x12)
    try:
        parse_result = parse(
            raw_x12,
            strict=False,
            on_error="collect",
            correlation_id=correlation_id,
        )
    except X12ParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(exc)},
        ) from exc

    parser_issues = _collect_parser_issues(parse_result.errors)
    source_transaction_count = _source_transaction_count(
        raw_x12,
        element_separator=parse_result.interchange.delimiters.element,
        segment_separator=parse_result.interchange.delimiters.segment,
    )
    results: list[EligibilityResult] = []
    payer_name: str | None = None
    parsed_transaction_count = 0

    for group in parse_result.interchange.functional_groups:
        for transaction in group.transactions:
            if not isinstance(transaction, Transaction271):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "The uploaded document is not a 271 eligibility response."},
                )
            parsed_transaction_count += 1
            if payer_name is None and transaction.loop_2000a.loop_2100a is not None:
                payer_name = transaction.loop_2000a.loop_2100a.nm1.last_name
            st_control_number = transaction.st.transaction_set_control_number
            for receiver_loop in as_list(transaction.loop_2000a.loop_2000b):
                if isinstance(receiver_loop, Loop2000B_271):
                    results.extend(
                        _project_receiver_loop(
                            receiver_loop,
                            st_control_number=st_control_number,
                        )
                    )

    if source_transaction_count == 0:
        source_transaction_count = parsed_transaction_count + len(parser_issues)

    summary = EligibilitySummary(
        total=len(results),
        active=sum(1 for result in results if result.overall_status == "active"),
        inactive=sum(1 for result in results if result.overall_status == "inactive"),
        error=sum(1 for result in results if result.overall_status == "error"),
        not_found=sum(1 for result in results if result.overall_status == "not_found"),
        unknown=sum(1 for result in results if result.overall_status == "unknown"),
    )
    if len(results) + len(parser_issues) != source_transaction_count:
        PARSER_ACCOUNTING_MISMATCH_TOTAL.labels(path=metrics_path).inc()
        logger.warning(
            "parser_accounting_mismatch",
            extra={
                "correlation_id": correlation_id,
                "path": metrics_path,
                "source": source_transaction_count,
                "parsed": len(results),
                "issues": len(parser_issues),
            },
        )
    observe_record_count(path=metrics_path, operation="eligibility_results", count=len(results))
    observe_segment_count(
        path=metrics_path,
        operation="parsed_segments",
        count=raw_x12.count(parse_result.interchange.delimiters.segment),
    )
    response = ParseResponse(
        filename=filename,
        source_transaction_count=source_transaction_count,
        parsed_result_count=len(results),
        parser_issue_count=len(parser_issues),
        parser_issues=parser_issues,
        transaction_count=source_transaction_count,
        summary=summary,
        payer_name=payer_name,
        results=results,
    )
    logger.info(
        "parse_271_completed",
        extra={
            "correlation_id": correlation_id,
            "path": metrics_path,
            "source_transaction_count": source_transaction_count,
            "parsed_transaction_count": parsed_transaction_count,
            "eligibility_result_count": len(results),
            "parser_error_count": len(parser_issues),
        },
    )
    return response


def _project_receiver_loop(
    receiver_loop: Loop2000B_271,
    *,
    st_control_number: str | None,
) -> list[EligibilityResult]:
    results: list[EligibilityResult] = []
    for subscriber_loop in as_list(receiver_loop.loop_2000c):
        if isinstance(subscriber_loop, Loop2000C_271):
            results.append(
                _project_subscriber_loop(
                    subscriber_loop,
                    st_control_number=st_control_number,
                )
            )
    return results


def _project_subscriber_loop(
    subscriber_loop: Loop2000C_271,
    *,
    st_control_number: str | None,
) -> EligibilityResult:
    eligibility_segments: list[EligibilitySegment] = []
    benefit_entities: list[BenefitEntity] = []
    aaa_errors = _map_aaa_segments(
        [
            *as_list(subscriber_loop.aaa_segments),
            *as_list(getattr(subscriber_loop.loop_2100c, "aaa_segments", [])),
        ]
    )

    for inquiry_loop in as_list(subscriber_loop.loop_2110c):
        if not isinstance(inquiry_loop, Loop2110C_271):
            continue
        eligibility_segments.extend(_map_eligibility_segments(inquiry_loop))
        benefit_entities.extend(_map_benefit_entities(inquiry_loop))
        aaa_errors.extend(_map_aaa_segments(as_list(inquiry_loop.aaa_segments)))

    overall_status, status_reason = _overall_status(eligibility_segments, aaa_errors)
    nm1 = subscriber_loop.loop_2100c.nm1
    member_name = ", ".join(part for part in [nm1.last_name, nm1.first_name] if part)
    return EligibilityResult(
        member_name=member_name or "UNKNOWN",
        member_id=nm1.id_code,
        overall_status=overall_status,
        status_reason=status_reason,
        st_control_number=st_control_number,
        trace_number=_trace_number(subscriber_loop),
        eligibility_segments=eligibility_segments,
        benefit_entities=benefit_entities,
        aaa_errors=aaa_errors,
    )


def _map_eligibility_segments(loop: Loop2110C_271) -> list[EligibilitySegment]:
    result: list[EligibilitySegment] = []
    for eb in loop.eb_segments:
        result.append(
            EligibilitySegment(
                eligibility_code=str(eb.eligibility_or_benefit_information),
                service_type_code=_enum_value(eb.service_type_code),
                service_type_codes=_service_type_codes(eb),
                coverage_level_code=eb.coverage_level_code,
                insurance_type_code=eb.insurance_type_code,
                plan_coverage_description=eb.plan_coverage_description,
                monetary_amount=_decimal_string(eb.monetary_amount),
                quantity=_decimal_string(eb.quantity),
                in_plan_network_indicator=eb.in_plan_network_indicator,
            )
        )
    return result


def _map_benefit_entities(loop: Loop2110C_271) -> list[BenefitEntity]:
    result: list[BenefitEntity] = []
    loop_identifier = getattr(loop.ls_segment, "loop_identifier_code", None)
    for ref in loop.ref_segments:
        result.append(
            BenefitEntity(
                loop_identifier=loop_identifier,
                qualifier=ref.reference_identification_qualifier,
                identifier=ref.reference_identification,
                description=ref.description,
            )
        )
    for entity_loop in loop.loop_2120c:
        nm1 = entity_loop.nm1
        contacts = [
            contact
            for contact in (_per_contact_summary(per) for per in entity_loop.per_segments)
            if contact
        ]
        result.append(
            BenefitEntity(
                loop_identifier=getattr(entity_loop.ls, "loop_identifier_code", None),
                qualifier=nm1.id_code_qualifier,
                identifier=nm1.id_code,
                entity_identifier_code=_enum_value(nm1.entity_identifier_code),
                name=_entity_name(nm1),
                contacts=contacts,
            )
        )
    return result


def _map_aaa_segments(segments: list[object]) -> list[AAAError]:
    result: list[AAAError] = []
    for segment in segments:
        code = getattr(segment, "reject_reason_code", None)
        if code is None:
            continue
        code_value = str(code)
        result.append(
            AAAError(
                code=code_value,
                message=AAA_REASON_MESSAGES.get(
                    code_value,
                    "Eligibility response returned an AAA error.",
                ),
                follow_up_action_code=getattr(segment, "follow_up_action_code", None),
                suggestion=AAA_REASON_SUGGESTIONS.get(code_value),
            )
        )
    return result


def _overall_status(
    eligibility_segments: list[EligibilitySegment],
    aaa_errors: list[AAAError],
) -> tuple[str, str]:
    if any(error.code == "75" for error in aaa_errors):
        return "not_found", "Subscriber not found"
    if aaa_errors:
        return "error", _aaa_reason(aaa_errors[0].code)
    codes = {segment.eligibility_code for segment in eligibility_segments}
    if codes & _ACTIVE_CODES:
        return "active", "Coverage on file"
    if codes & _INACTIVE_CODES:
        return "inactive", "Coverage terminated"
    if codes & _SUPPLEMENTAL_CODES:
        return "unknown", "Additional payer information only"
    return "unknown", "No coverage signal"


def _collect_parser_issues(errors: list[TransactionParseError]) -> list[ParserIssue]:
    return [
        ParserIssue(
            transaction_index=error.transaction_index,
            transaction_control_number=error.st_control_number,
            segment_id=error.segment_id,
            location=f"segment_position:{error.segment_position}",
            message=error.message,
            severity="error",
        )
        for error in errors
    ]


def _source_transaction_count(
    raw_x12: str,
    *,
    element_separator: str,
    segment_separator: str,
) -> int:
    segments = [segment.strip() for segment in raw_x12.split(segment_separator)]
    st_271_prefix = f"ST{element_separator}271"
    source_count = sum(1 for segment in segments if segment.startswith(st_271_prefix))
    if source_count:
        return source_count
    st_prefix = f"ST{element_separator}"
    return sum(1 for segment in segments if segment.startswith(st_prefix))


def _trace_number(subscriber_loop: Loop2000C_271) -> str | None:
    trn = getattr(subscriber_loop, "trn", None)
    if trn is None:
        return None
    return getattr(trn, "reference_identification_1", None)


def _service_type_codes(eb: object) -> list[str]:
    values = [_enum_value(value) for value in getattr(eb, "service_type_codes", [])]
    service_type_codes = [value for value in values if value]
    if service_type_codes:
        return service_type_codes
    service_type_code = _enum_value(getattr(eb, "service_type_code", None))
    return [service_type_code] if service_type_code else []


def _entity_name(nm1: object) -> str | None:
    name_parts = [
        getattr(nm1, "last_name", None),
        getattr(nm1, "first_name", None),
        getattr(nm1, "middle_name", None),
    ]
    return ", ".join(part for part in name_parts if part) or None


def _per_contact_summary(per: object) -> str | None:
    contacts: list[str] = []
    for qualifier_attr, number_attr in (
        ("communication_number_qualifier_1", "communication_number_1"),
        ("communication_number_qualifier_2", "communication_number_2"),
        ("communication_number_qualifier_3", "communication_number_3"),
    ):
        qualifier = getattr(per, qualifier_attr, None)
        number = getattr(per, number_attr, None)
        if qualifier and number:
            contacts.append(f"{qualifier}:{number}")
        elif number:
            contacts.append(str(number))

    label = getattr(per, "name", None) or getattr(per, "contact_function_code", None)
    if label and contacts:
        return f"{label} ({', '.join(contacts)})"
    if label:
        return str(label)
    if contacts:
        return ", ".join(contacts)
    return None


def _aaa_reason(code: str | None) -> str:
    if code is None:
        return "Eligibility response returned an AAA error."
    return AAA_REASON_MESSAGES.get(code, "Eligibility response returned an AAA error.")


def _decimal_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _enum_value(value: object) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))
