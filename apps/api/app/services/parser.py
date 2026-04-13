"""271 projection services."""

from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from x12_edi_tools import parse
from x12_edi_tools.exceptions import X12ParseError
from x12_edi_tools.models.loops import Loop2000B_271, Loop2000C_271, Loop2110C_271
from x12_edi_tools.models.transactions import Transaction271
from x12_edi_tools.payers.dc_medicaid.constants import AAA_REASON_MESSAGES, AAA_REASON_SUGGESTIONS
from x12_edi_tools.validator.base import as_list

from app.core.logging import get_logger
from app.core.metrics import observe_record_count, observe_segment_count
from app.schemas.common import (
    AAAError,
    BenefitEntity,
    EligibilityResult,
    EligibilitySegment,
    EligibilitySummary,
)
from app.schemas.parse import ParseResponse
from app.services.validator import harden_x12_payload

_ACTIVE_CODES = {"1", "2", "3", "4", "5"}
_INACTIVE_CODES = {"6", "7", "8"}
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

    results: list[EligibilityResult] = []
    payer_name: str | None = None
    transaction_count = 0

    for group in parse_result.interchange.functional_groups:
        for transaction in group.transactions:
            if not isinstance(transaction, Transaction271):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "The uploaded document is not a 271 eligibility response."},
                )
            transaction_count += 1
            if payer_name is None and transaction.loop_2000a.loop_2100a is not None:
                payer_name = transaction.loop_2000a.loop_2100a.nm1.last_name
            for receiver_loop in as_list(transaction.loop_2000a.loop_2000b):
                if isinstance(receiver_loop, Loop2000B_271):
                    results.extend(_project_receiver_loop(receiver_loop))

    if not results and parse_result.errors:
        first_error = parse_result.errors[0]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": first_error.message, "suggestion": first_error.suggestion},
        )

    summary = EligibilitySummary(
        total=len(results),
        active=sum(1 for result in results if result.overall_status == "active"),
        inactive=sum(1 for result in results if result.overall_status == "inactive"),
        error=sum(1 for result in results if result.overall_status == "error"),
        unknown=sum(1 for result in results if result.overall_status == "unknown"),
    )
    observe_record_count(path=metrics_path, operation="eligibility_results", count=len(results))
    observe_segment_count(
        path=metrics_path,
        operation="parsed_segments",
        count=raw_x12.count(parse_result.interchange.delimiters.segment),
    )
    response = ParseResponse(
        filename=filename,
        transaction_count=transaction_count,
        summary=summary,
        payer_name=payer_name,
        results=results,
    )
    logger.info(
        "parse_271_completed",
        extra={
            "correlation_id": correlation_id,
            "path": metrics_path,
            "transaction_count": transaction_count,
            "eligibility_result_count": len(results),
            "parser_error_count": len(parse_result.errors),
        },
    )
    return response


def _project_receiver_loop(receiver_loop: Loop2000B_271) -> list[EligibilityResult]:
    results: list[EligibilityResult] = []
    for subscriber_loop in as_list(receiver_loop.loop_2000c):
        if isinstance(subscriber_loop, Loop2000C_271):
            results.append(_project_subscriber_loop(subscriber_loop))
    return results


def _project_subscriber_loop(subscriber_loop: Loop2000C_271) -> EligibilityResult:
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

    overall_status = _overall_status(eligibility_segments, aaa_errors)
    nm1 = subscriber_loop.loop_2100c.nm1
    member_name = ", ".join(part for part in [nm1.last_name, nm1.first_name] if part)
    return EligibilityResult(
        member_name=member_name or "UNKNOWN",
        member_id=nm1.id_code,
        overall_status=overall_status,
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
) -> str:
    if aaa_errors:
        return "error"
    codes = {segment.eligibility_code for segment in eligibility_segments}
    if codes & _ACTIVE_CODES:
        return "active"
    if codes & _INACTIVE_CODES:
        return "inactive"
    return "unknown"


def _decimal_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _enum_value(value: object) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))
