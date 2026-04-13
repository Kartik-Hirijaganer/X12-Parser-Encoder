"""Generic SNIP level 3 validation."""

from __future__ import annotations

from x12_edi_tools.models.transactions import FunctionalGroup, Interchange
from x12_edi_tools.validator.base import (
    SnipLevel,
    ValidationError,
    as_list,
    count_transaction_segments,
    issue,
    iter_transactions,
    normalize_str,
)


def validate_snip3(interchange: Interchange) -> list[ValidationError]:
    """Validate balancing counts and control-number cross references."""

    issues: list[ValidationError] = []

    functional_groups = as_list(getattr(interchange, "functional_groups", []))
    iea = getattr(interchange, "iea", None)
    if iea is not None:
        actual_group_count = len(
            [group for group in functional_groups if isinstance(group, FunctionalGroup)]
        )
        reported_group_count = getattr(iea, "number_of_included_functional_groups", None)
        if reported_group_count != actual_group_count:
            issues.append(
                issue(
                    level=SnipLevel.SNIP3,
                    code="SNIP3_IEA01_COUNT_MISMATCH",
                    message=(
                        f"IEA01 reports {reported_group_count} functional groups, but the "
                        f"interchange contains {actual_group_count}."
                    ),
                    location="IEA.01",
                    segment_id="IEA",
                    element="01",
                    suggestion="Set IEA01 to the actual number of GS/GE groups in the interchange.",
                )
            )

        isa_control = normalize_str(
            getattr(getattr(interchange, "isa", None), "interchange_control_number", None)
        )
        iea_control = normalize_str(getattr(iea, "interchange_control_number", None))
        if isa_control and iea_control and isa_control != iea_control:
            issues.append(
                issue(
                    level=SnipLevel.SNIP3,
                    code="SNIP3_ISA13_IEA02_MISMATCH",
                    message=(f"ISA13 '{isa_control}' does not match IEA02 '{iea_control}'."),
                    location="IEA.02",
                    segment_id="IEA",
                    element="02",
                    suggestion="Use the same interchange control number in ISA13 and IEA02.",
                )
            )

    for group_index, group in enumerate(functional_groups):
        if not isinstance(group, FunctionalGroup):
            continue

        transactions = as_list(getattr(group, "transactions", []))
        ge = getattr(group, "ge", None)
        if ge is not None:
            reported_transaction_count = getattr(ge, "number_of_transaction_sets_included", None)
            actual_transaction_count = len(transactions)
            if reported_transaction_count != actual_transaction_count:
                issues.append(
                    issue(
                        level=SnipLevel.SNIP3,
                        code="SNIP3_GE01_COUNT_MISMATCH",
                        message=(
                            f"GE01 reports {reported_transaction_count} transaction sets, but "
                            f"the group contains {actual_transaction_count}."
                        ),
                        location=f"FunctionalGroup[{group_index}].GE.01",
                        segment_id="GE",
                        element="01",
                        suggestion="Set GE01 to the number of ST/SE transactions in the group.",
                    )
                )

            gs_control = normalize_str(
                getattr(getattr(group, "gs", None), "group_control_number", None)
            )
            ge_control = normalize_str(getattr(ge, "group_control_number", None))
            if gs_control and ge_control and gs_control != ge_control:
                issues.append(
                    issue(
                        level=SnipLevel.SNIP3,
                        code="SNIP3_GS06_GE02_MISMATCH",
                        message=f"GS06 '{gs_control}' does not match GE02 '{ge_control}'.",
                        location=f"FunctionalGroup[{group_index}].GE.02",
                        segment_id="GE",
                        element="02",
                        suggestion="Use the same group control number in GS06 and GE02.",
                    )
                )

    for tx_context in iter_transactions(interchange):
        transaction = tx_context.transaction
        se = getattr(transaction, "se", None)
        actual_segment_count = count_transaction_segments(transaction)
        location_prefix = (
            f"FunctionalGroup[{tx_context.functional_group_index}].Transaction"
            f"[{tx_context.transaction_index}]"
        )

        if se is not None:
            reported_segment_count = getattr(se, "number_of_included_segments", None)
            if reported_segment_count != actual_segment_count:
                issues.append(
                    issue(
                        level=SnipLevel.SNIP3,
                        code="SNIP3_SE01_COUNT_MISMATCH",
                        message=(
                            f"SE01 reports {reported_segment_count} included segments, but the "
                            f"transaction contains {actual_segment_count}."
                        ),
                        location=f"{location_prefix}.SE.01",
                        segment_id="SE",
                        element="01",
                        suggestion="Set SE01 to the inclusive count from ST through SE.",
                    )
                )

            st_control = normalize_str(
                getattr(getattr(transaction, "st", None), "transaction_set_control_number", None)
            )
            se_control = normalize_str(getattr(se, "transaction_set_control_number", None))
            if st_control and se_control and st_control != se_control:
                issues.append(
                    issue(
                        level=SnipLevel.SNIP3,
                        code="SNIP3_ST02_SE02_MISMATCH",
                        message=f"ST02 '{st_control}' does not match SE02 '{se_control}'.",
                        location=f"{location_prefix}.SE.02",
                        segment_id="SE",
                        element="02",
                        suggestion="Use the same transaction control number in ST02 and SE02.",
                    )
                )

    return issues
