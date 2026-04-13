"""Generic SNIP level 1 validation."""

from __future__ import annotations

from x12_edi_tools.common import Delimiters
from x12_edi_tools.encoder.isa_encoder import encode_isa
from x12_edi_tools.models.base import GenericSegment
from x12_edi_tools.models.transactions import FunctionalGroup, Interchange
from x12_edi_tools.models.transactions.transaction_270 import Transaction270
from x12_edi_tools.models.transactions.transaction_271 import Transaction271
from x12_edi_tools.validator.base import SnipLevel, ValidationError, as_list, issue

_ISA_FIELD_WIDTHS = {
    "authorization_information_qualifier": 2,
    "authorization_information": 10,
    "security_information_qualifier": 2,
    "security_information": 10,
    "sender_id_qualifier": 2,
    "sender_id": 15,
    "receiver_id_qualifier": 2,
    "receiver_id": 15,
    "interchange_date": 6,
    "interchange_time": 4,
    "repetition_separator": 1,
    "control_version_number": 5,
    "interchange_control_number": 9,
    "acknowledgment_requested": 1,
    "usage_indicator": 1,
    "component_element_separator": 1,
}


def validate_snip1(interchange: Interchange) -> list[ValidationError]:
    """Validate syntax-integrity rules representable on the typed interchange."""

    issues: list[ValidationError] = []

    if getattr(interchange, "isa", None) is None:
        issues.append(
            issue(
                level=SnipLevel.SNIP1,
                code="SNIP1_MISSING_ISA",
                message="The interchange is missing its ISA header segment.",
                location="ISA",
                segment_id="ISA",
                suggestion="Include one ISA header before any GS segments.",
            )
        )
    else:
        delimiters = getattr(interchange, "delimiters", None)
        if not isinstance(delimiters, Delimiters):
            delimiters = Delimiters()
        for field_name, expected_width in _ISA_FIELD_WIDTHS.items():
            value = getattr(interchange.isa, field_name, None)
            rendered = "" if value is None else str(value)
            if len(rendered) == expected_width:
                continue
            issues.append(
                issue(
                    level=SnipLevel.SNIP1,
                    code="SNIP1_INVALID_ISA_LENGTH",
                    message=(
                        f"ISA field '{field_name}' must be exactly {expected_width} "
                        f"characters, got {len(rendered)}."
                    ),
                    location="ISA",
                    segment_id="ISA",
                    suggestion="Pad or trim ISA fixed-width elements to their required widths.",
                )
            )
            break
        try:
            encoded_isa = encode_isa(interchange.isa, delimiters=delimiters)
            if len(encoded_isa) != 106:
                issues.append(
                    issue(
                        level=SnipLevel.SNIP1,
                        code="SNIP1_INVALID_ISA_LENGTH",
                        message=(
                            f"ISA must be exactly 106 characters on the wire, got "
                            f"{len(encoded_isa)}."
                        ),
                        location="ISA",
                        segment_id="ISA",
                        suggestion="Pad ISA fixed-width elements to their required widths.",
                    )
                )
        except Exception:  # pragma: no cover - defensive path for malformed model_construct
            issues.append(
                issue(
                    level=SnipLevel.SNIP1,
                    code="SNIP1_INVALID_ISA_LENGTH",
                    message="ISA cannot be rendered as a valid 106-character segment.",
                    location="ISA",
                    segment_id="ISA",
                    suggestion="Check ISA fixed-width element lengths and delimiters.",
                )
            )

    functional_groups = as_list(getattr(interchange, "functional_groups", []))
    if not functional_groups:
        issues.append(
            issue(
                level=SnipLevel.SNIP1,
                code="SNIP1_MISSING_GS_GE",
                message="The interchange does not contain a functional group.",
                location="GS",
                suggestion="Include one GS/GE envelope inside the ISA/IEA interchange.",
            )
        )

    if getattr(interchange, "iea", None) is None:
        issues.append(
            issue(
                level=SnipLevel.SNIP1,
                code="SNIP1_MISSING_IEA",
                message="The interchange is missing its IEA trailer segment.",
                location="IEA",
                segment_id="IEA",
                suggestion="Close the interchange with one IEA trailer after all GE segments.",
            )
        )

    for group_index, group in enumerate(functional_groups):
        if not isinstance(group, FunctionalGroup):
            continue

        if getattr(group, "gs", None) is None:
            issues.append(
                issue(
                    level=SnipLevel.SNIP1,
                    code="SNIP1_MISSING_GS",
                    message=f"Functional group {group_index + 1} is missing its GS header.",
                    location=f"FunctionalGroup[{group_index}].GS",
                    segment_id="GS",
                    suggestion="Open each functional group with a GS segment.",
                )
            )
        if getattr(group, "ge", None) is None:
            issues.append(
                issue(
                    level=SnipLevel.SNIP1,
                    code="SNIP1_MISSING_GE",
                    message=f"Functional group {group_index + 1} is missing its GE trailer.",
                    location=f"FunctionalGroup[{group_index}].GE",
                    segment_id="GE",
                    suggestion="Close each functional group with a GE segment.",
                )
            )

        transactions = as_list(getattr(group, "transactions", []))
        if not transactions:
            issues.append(
                issue(
                    level=SnipLevel.SNIP1,
                    code="SNIP1_MISSING_ST_SE",
                    message=f"Functional group {group_index + 1} does not contain a transaction.",
                    location=f"FunctionalGroup[{group_index}].ST",
                    suggestion="Add at least one ST/SE transaction set inside the GS/GE group.",
                )
            )

        for transaction_index, transaction in enumerate(transactions):
            location_prefix = f"FunctionalGroup[{group_index}].Transaction[{transaction_index}]"
            if not isinstance(transaction, Transaction270 | Transaction271):
                continue
            if getattr(transaction, "st", None) is None:
                issues.append(
                    issue(
                        level=SnipLevel.SNIP1,
                        code="SNIP1_MISSING_ST",
                        message=(
                            f"Transaction {transaction_index + 1} in functional group "
                            f"{group_index + 1} is missing its ST header."
                        ),
                        location=f"{location_prefix}.ST",
                        segment_id="ST",
                        suggestion="Open each transaction with an ST segment.",
                    )
                )
            if getattr(transaction, "se", None) is None:
                issues.append(
                    issue(
                        level=SnipLevel.SNIP1,
                        code="SNIP1_MISSING_SE",
                        message=(
                            f"Transaction {transaction_index + 1} in functional group "
                            f"{group_index + 1} is missing its SE trailer."
                        ),
                        location=f"{location_prefix}.SE",
                        segment_id="SE",
                        suggestion="Close each transaction with an SE segment.",
                    )
                )

            for generic_index, segment in enumerate(as_list(transaction.generic_segments)):
                if not isinstance(segment, GenericSegment):
                    continue
                issues.append(
                    issue(
                        level=SnipLevel.SNIP1,
                        code="SNIP1_UNKNOWN_SEGMENT_ID",
                        message=(
                            f"Unsupported segment ID '{segment.segment_id}' was preserved in "
                            "the transaction body."
                        ),
                        location=f"{location_prefix}.GenericSegment[{generic_index}]",
                        segment_id=segment.segment_id,
                        suggestion=(
                            "Remove the unsupported segment or add typed support before "
                            "submitting the transaction."
                        ),
                    )
                )

    return issues
