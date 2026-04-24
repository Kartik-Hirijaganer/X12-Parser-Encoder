"""Generic SNIP level 2 validation."""

from __future__ import annotations

from annotated_types import MaxLen

from x12_edi_tools.models.base import X12Segment
from x12_edi_tools.models.loops import (
    Loop2000A_270,
    Loop2000A_271,
    Loop2000B_270,
    Loop2000B_271,
    Loop2000C_270,
    Loop2000C_271,
)
from x12_edi_tools.models.segments import BHTSegment, GSSegment, NM1Segment, STSegment
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
    annotate_transaction_issue,
    annotate_transaction_issues,
    as_list,
    issue,
    iter_transaction_body_segments,
    iter_transactions,
    normalize_str,
)

IMPLEMENTATION_VERSION = "005010X279A1"
VALID_BHT02 = {"11", "13"}
FIELD_MAX_LENGTH_OVERRIDES: dict[tuple[str, str], int] = {
    ("NM1", "entity_type_qualifier"): 1,
    ("NM1", "last_name"): 60,
    ("NM1", "first_name"): 35,
    ("NM1", "middle_name"): 25,
    ("NM1", "name_prefix"): 10,
    ("NM1", "name_suffix"): 10,
    ("NM1", "id_code_qualifier"): 3,
    ("NM1", "id_code"): 80,
}


def validate_snip2(interchange: Interchange) -> list[ValidationError]:
    """Validate required-segment, required-element, and bounded-length rules."""

    issues: list[ValidationError] = []

    isa = getattr(interchange, "isa", None)
    if isa is None:
        issues.append(
            issue(
                level=SnipLevel.SNIP2,
                code="SNIP2_MISSING_ISA",
                message="The interchange is missing ISA, which is required for all X12 files.",
                location="ISA",
                segment_id="ISA",
                suggestion="Add the ISA header before validating or encoding the interchange.",
            )
        )

    for group_index, group in enumerate(as_list(getattr(interchange, "functional_groups", []))):
        if not isinstance(group, FunctionalGroup):
            continue

        gs = getattr(group, "gs", None)
        if not isinstance(gs, GSSegment):
            issues.append(
                issue(
                    level=SnipLevel.SNIP2,
                    code="SNIP2_MISSING_GS",
                    message=f"Functional group {group_index + 1} is missing its GS segment.",
                    location=f"FunctionalGroup[{group_index}].GS",
                    segment_id="GS",
                    suggestion="Add a GS header to the functional group.",
                )
            )
        else:
            version = normalize_str(gs.version_release_industry_identifier_code)
            if version != IMPLEMENTATION_VERSION:
                issues.append(
                    issue(
                        level=SnipLevel.SNIP2,
                        code="SNIP2_INVALID_GS08_VERSION",
                        message=(
                            f"GS08 must be '{IMPLEMENTATION_VERSION}' for 270/271 transactions; "
                            f"got '{version or ''}'."
                        ),
                        location=f"FunctionalGroup[{group_index}].GS.08",
                        segment_id="GS",
                        element="08",
                        suggestion="Set GS08 to 005010X279A1.",
                    )
                )

        for tx_context in iter_transactions(interchange):
            if tx_context.functional_group_index != group_index:
                continue
            issues.extend(
                annotate_transaction_issues(
                    _validate_transaction_required_content(tx_context.transaction, tx_context),
                    tx_context,
                )
            )

    issues.extend(_validate_segment_lengths(interchange))
    return issues


def _validate_transaction_required_content(
    transaction: Transaction270 | Transaction271,
    tx_context: TransactionContext,
) -> list[ValidationError]:
    issues: list[ValidationError] = []
    location_prefix = (
        f"FunctionalGroup[{tx_context.functional_group_index}].Transaction"
        f"[{tx_context.transaction_index}]"
    )

    st = getattr(transaction, "st", None)
    if not isinstance(st, STSegment):
        issues.append(
            issue(
                level=SnipLevel.SNIP2,
                code="SNIP2_MISSING_ST",
                message="A transaction is missing the required ST segment.",
                location=f"{location_prefix}.ST",
                segment_id="ST",
                suggestion="Add an ST segment at the start of the transaction.",
            )
        )
    else:
        st01 = normalize_str(st.transaction_set_identifier_code)
        if st01 not in {"270", "271"}:
            issues.append(
                issue(
                    level=SnipLevel.SNIP2,
                    code="SNIP2_INVALID_ST01",
                    message=f"ST01 must be 270 or 271, got '{st01 or ''}'.",
                    location=f"{location_prefix}.ST.01",
                    segment_id="ST",
                    element="01",
                    suggestion="Use ST01=270 for inquiries or ST01=271 for responses.",
                )
            )
        st03 = normalize_str(st.implementation_convention_reference)
        if st03 and st03 != IMPLEMENTATION_VERSION:
            issues.append(
                issue(
                    level=SnipLevel.SNIP2,
                    code="SNIP2_INVALID_ST03",
                    message=(
                        f"ST03 must be '{IMPLEMENTATION_VERSION}' when populated; got '{st03}'."
                    ),
                    location=f"{location_prefix}.ST.03",
                    segment_id="ST",
                    element="03",
                    suggestion="Set ST03 to 005010X279A1.",
                )
            )

    bht = getattr(transaction, "bht", None)
    if not isinstance(bht, BHTSegment):
        issues.append(
            issue(
                level=SnipLevel.SNIP2,
                code="SNIP2_MISSING_BHT",
                message="The transaction is missing the required BHT segment.",
                location=f"{location_prefix}.BHT",
                segment_id="BHT",
                suggestion="Add BHT immediately after ST.",
            )
        )
    else:
        purpose_code = normalize_str(bht.transaction_set_purpose_code)
        if purpose_code not in VALID_BHT02:
            issues.append(
                issue(
                    level=SnipLevel.SNIP2,
                    code="SNIP2_INVALID_BHT02",
                    message=(
                        f"BHT02 must be 11 or 13 for eligibility transactions; got "
                        f"'{purpose_code or ''}'."
                    ),
                    location=f"{location_prefix}.BHT.02",
                    segment_id="BHT",
                    element="02",
                    suggestion="Use BHT02=13 for 270 or BHT02=11 for 271.",
                )
            )

    if isinstance(transaction, Transaction270):
        loop_2000a = getattr(transaction, "loop_2000a", None)
        issues.extend(_validate_270_structure(loop_2000a, location_prefix))
    else:
        loop_2000a = getattr(transaction, "loop_2000a", None)
        issues.extend(_validate_271_structure(loop_2000a, location_prefix))

    return issues


def _validate_270_structure(loop_2000a: object, prefix: str) -> list[ValidationError]:
    issues: list[ValidationError] = []
    if not isinstance(loop_2000a, Loop2000A_270):
        issues.append(
            issue(
                level=SnipLevel.SNIP2,
                code="SNIP2_MISSING_HL",
                message="The transaction is missing the top-level 2000A HL loop.",
                location=f"{prefix}.Loop2000A.HL",
                segment_id="HL",
                suggestion="Add HL*20 and the required 2100A payer loop.",
            )
        )
        return issues

    if getattr(loop_2000a, "hl", None) is None:
        issues.append(
            issue(
                level=SnipLevel.SNIP2,
                code="SNIP2_MISSING_HL",
                message="Loop 2000A is missing its required HL segment.",
                location=f"{prefix}.Loop2000A.HL",
                segment_id="HL",
                suggestion="Populate the HL segment for loop 2000A.",
            )
        )

    issues.extend(
        _require_nm1(
            getattr(loop_2000a, "loop_2100a", None),
            location=f"{prefix}.Loop2100A.NM1",
            code="SNIP2_MISSING_2100A_NM1",
            message="Loop 2100A is missing the required NM1 payer segment.",
        )
    )
    issues.extend(
        _require_nm1_last_name(
            getattr(getattr(loop_2000a, "loop_2100a", None), "nm1", None),
            location=f"{prefix}.Loop2100A.NM1.03",
            message="Payer NM103 is required in loop 2100A.",
        )
    )

    receiver_loops = as_list(getattr(loop_2000a, "loop_2000b", []))
    if not receiver_loops:
        issues.append(
            issue(
                level=SnipLevel.SNIP2,
                code="SNIP2_MISSING_2000B",
                message="The transaction is missing the required 2000B information receiver loop.",
                location=f"{prefix}.Loop2000B",
                suggestion="Add the provider/information receiver loop.",
            )
        )
    for receiver_index, receiver_loop in enumerate(receiver_loops):
        if not isinstance(receiver_loop, Loop2000B_270):
            continue
        issues.extend(
            _require_nm1(
                getattr(receiver_loop, "loop_2100b", None),
                location=f"{prefix}.Loop2000B[{receiver_index}].Loop2100B.NM1",
                code="SNIP2_MISSING_2100B_NM1",
                message="Loop 2100B is missing the required NM1 provider segment.",
            )
        )
        issues.extend(
            _require_nm1_last_name(
                getattr(getattr(receiver_loop, "loop_2100b", None), "nm1", None),
                location=f"{prefix}.Loop2000B[{receiver_index}].Loop2100B.NM1.03",
                message="Provider NM103 is required in loop 2100B.",
            )
        )

        subscriber_loops = as_list(getattr(receiver_loop, "loop_2000c", []))
        if not subscriber_loops:
            issues.append(
                issue(
                    level=SnipLevel.SNIP2,
                    code="SNIP2_MISSING_2000C",
                    message=(
                        "Loop 2000B must contain at least one subscriber loop "
                        "for an eligibility inquiry."
                    ),
                    location=f"{prefix}.Loop2000B[{receiver_index}].Loop2000C",
                    suggestion="Add a subscriber loop with NM1 and eligibility criteria.",
                )
            )
        for subscriber_index, subscriber_loop in enumerate(subscriber_loops):
            if not isinstance(subscriber_loop, Loop2000C_270):
                continue
            issues.extend(
                _require_nm1(
                    getattr(subscriber_loop, "loop_2100c", None),
                    location=(
                        f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}]"
                        ".Loop2100C.NM1"
                    ),
                    code="SNIP2_MISSING_2100C_NM1",
                    message="Loop 2100C is missing the required NM1 subscriber segment.",
                )
            )
            issues.extend(
                _require_nm1_last_name(
                    getattr(getattr(subscriber_loop, "loop_2100c", None), "nm1", None),
                    location=(
                        f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}]"
                        ".Loop2100C.NM1.03"
                    ),
                    message="Subscriber NM103 is required in loop 2100C.",
                )
            )
            if not as_list(getattr(subscriber_loop, "loop_2110c", [])):
                issues.append(
                    issue(
                        level=SnipLevel.SNIP2,
                        code="SNIP2_MISSING_2110C",
                        message="Loop 2000C must contain at least one 2110C eligibility loop.",
                        location=(
                            f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}]"
                            ".Loop2110C"
                        ),
                        suggestion="Add EQ criteria, and optionally DTP service dates, in 2110C.",
                    )
                )

    return issues


def _validate_271_structure(loop_2000a: object, prefix: str) -> list[ValidationError]:
    issues: list[ValidationError] = []
    if not isinstance(loop_2000a, Loop2000A_271):
        issues.append(
            issue(
                level=SnipLevel.SNIP2,
                code="SNIP2_MISSING_HL",
                message="The transaction is missing the top-level 2000A HL loop.",
                location=f"{prefix}.Loop2000A.HL",
                segment_id="HL",
                suggestion="Add HL*20 and the required 2100A payer loop.",
            )
        )
        return issues

    issues.extend(
        _require_nm1(
            getattr(loop_2000a, "loop_2100a", None),
            location=f"{prefix}.Loop2100A.NM1",
            code="SNIP2_MISSING_2100A_NM1",
            message="Loop 2100A is missing the required NM1 payer segment.",
        )
    )
    issues.extend(
        _require_nm1_last_name(
            getattr(getattr(loop_2000a, "loop_2100a", None), "nm1", None),
            location=f"{prefix}.Loop2100A.NM1.03",
            message="Payer NM103 is required in loop 2100A.",
        )
    )

    for receiver_index, receiver_loop in enumerate(as_list(getattr(loop_2000a, "loop_2000b", []))):
        if not isinstance(receiver_loop, Loop2000B_271):
            continue
        issues.extend(
            _require_nm1(
                getattr(receiver_loop, "loop_2100b", None),
                location=f"{prefix}.Loop2000B[{receiver_index}].Loop2100B.NM1",
                code="SNIP2_MISSING_2100B_NM1",
                message="Loop 2100B is missing the required NM1 provider segment.",
            )
        )
        for subscriber_index, subscriber_loop in enumerate(as_list(receiver_loop.loop_2000c)):
            if not isinstance(subscriber_loop, Loop2000C_271):
                continue
            issues.extend(
                _require_nm1(
                    getattr(subscriber_loop, "loop_2100c", None),
                    location=(
                        f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}]"
                        ".Loop2100C.NM1"
                    ),
                    code="SNIP2_MISSING_2100C_NM1",
                    message="Loop 2100C is missing the required NM1 subscriber segment.",
                )
            )

    return issues


def _require_nm1(
    loop_model: object,
    *,
    location: str,
    code: str,
    message: str,
) -> list[ValidationError]:
    nm1 = getattr(loop_model, "nm1", None)
    if isinstance(nm1, NM1Segment):
        return []
    return [
        issue(
            level=SnipLevel.SNIP2,
            code=code,
            message=message,
            location=location,
            segment_id="NM1",
            suggestion="Populate the required NM1 segment for this loop.",
        )
    ]


def _require_nm1_last_name(nm1: object, *, location: str, message: str) -> list[ValidationError]:
    if not isinstance(nm1, NM1Segment):
        return []
    if normalize_str(nm1.last_name):
        return []
    return [
        issue(
            level=SnipLevel.SNIP2,
            code="SNIP2_REQUIRED_ELEMENT_EMPTY",
            message=message,
            location=location,
            segment_id="NM1",
            element="03",
            suggestion="Populate NM103 with the payer, provider, or subscriber name.",
        )
    ]


def _validate_segment_lengths(interchange: Interchange) -> list[ValidationError]:
    issues: list[ValidationError] = []
    segments: list[tuple[str, X12Segment, TransactionContext | None]] = []

    isa = getattr(interchange, "isa", None)
    if isinstance(isa, X12Segment):
        segments.append(("ISA", isa, None))

    for group_index, group in enumerate(as_list(getattr(interchange, "functional_groups", []))):
        if not isinstance(group, FunctionalGroup):
            continue
        if isinstance(getattr(group, "gs", None), X12Segment):
            segments.append((f"FunctionalGroup[{group_index}].GS", group.gs, None))
        if isinstance(getattr(group, "ge", None), X12Segment):
            segments.append((f"FunctionalGroup[{group_index}].GE", group.ge, None))
        for tx_context in iter_transactions(interchange):
            if tx_context.functional_group_index != group_index:
                continue
            transaction = tx_context.transaction
            tx_prefix = (
                f"FunctionalGroup[{group_index}].Transaction[{tx_context.transaction_index}]"
            )
            for segment_name in ("st", "bht", "se"):
                segment = getattr(transaction, segment_name, None)
                if isinstance(segment, X12Segment):
                    segments.append((f"{tx_prefix}.{segment.segment_id}", segment, tx_context))
            for segment in iter_transaction_body_segments(transaction):
                segments.append((tx_prefix, segment, tx_context))

    for prefix, segment, segment_tx_context in segments:
        reverse_map = {
            field_name: position for position, field_name in segment._element_map.items()
        }
        for field_name, field_info in segment.__class__.model_fields.items():
            max_length = _extract_max_length(field_info.metadata)
            if max_length is None:
                max_length = FIELD_MAX_LENGTH_OVERRIDES.get((segment.segment_id, field_name))
            if max_length is None:
                continue
            value = getattr(segment, field_name, None)
            rendered = normalize_str(value)
            if rendered is None or len(rendered) <= max_length:
                continue
            position = reverse_map.get(field_name)
            location = f"{prefix}.{segment.segment_id}"
            if position is not None:
                location = f"{location}.{position:02d}"
            validation_issue = issue(
                level=SnipLevel.SNIP2,
                code="SNIP2_ELEMENT_TOO_LONG",
                message=(
                    f"{segment.segment_id}{position or ''} allows at most {max_length} "
                    f"characters, got {len(rendered)}."
                ),
                location=location,
                segment_id=segment.segment_id,
                element=f"{position:02d}" if position is not None else None,
                suggestion="Trim the element to the maximum allowed X12 length.",
            )
            if segment_tx_context is not None:
                validation_issue = annotate_transaction_issue(validation_issue, segment_tx_context)
            issues.append(validation_issue)

    return issues


def _extract_max_length(metadata: list[object]) -> int | None:
    for item in metadata:
        if isinstance(item, MaxLen):
            return getattr(item, "max_length", None)
    return None
