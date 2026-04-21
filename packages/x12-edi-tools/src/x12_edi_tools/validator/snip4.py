"""Generic SNIP level 4 validation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from x12_edi_tools.common.enums import EntityIdentifierCode
from x12_edi_tools.models.loops import (
    Loop2000A_270,
    Loop2000A_271,
    Loop2000B_270,
    Loop2000B_271,
    Loop2000C_270,
    Loop2000C_271,
)
from x12_edi_tools.models.segments import DTPSegment, HLSegment, NM1Segment
from x12_edi_tools.models.transactions import Interchange, Transaction270, Transaction271
from x12_edi_tools.validator.base import (
    SnipLevel,
    ValidationError,
    as_list,
    issue,
    iter_transactions,
    normalize_str,
)

_DTP_PATTERNS: dict[str, str] = {
    "D8": r"^\d{8}$",
    "RD8": r"^\d{8}-\d{8}$",
    "DT": r"^\d{12,14}$",
    "TM": r"^\d{4,8}$",
}


@dataclass(frozen=True, slots=True)
class _HLRef:
    level_code: str | None
    hierarchical_id: str | None
    parent_id: str | None
    location: str


def validate_snip4(interchange: Interchange) -> list[ValidationError]:
    """Validate inter-segment situational rules."""

    issues: list[ValidationError] = []

    for tx_context in iter_transactions(interchange):
        transaction = tx_context.transaction
        issues.extend(
            _validate_hl_structure(
                transaction,
                tx_context.functional_group_index,
                tx_context.transaction_index,
            )
        )
        issues.extend(
            _validate_nm1_contexts(
                transaction,
                tx_context.functional_group_index,
                tx_context.transaction_index,
            )
        )
        issues.extend(
            _validate_dtp_formats(
                transaction,
                tx_context.functional_group_index,
                tx_context.transaction_index,
            )
        )

    return issues


def _validate_hl_structure(
    transaction: Transaction270 | Transaction271,
    group_index: int,
    transaction_index: int,
) -> list[ValidationError]:
    issues: list[ValidationError] = []
    hl_refs = _collect_hl_refs(transaction, group_index, transaction_index)
    if not hl_refs:
        return issues

    hl_by_id = {ref.hierarchical_id: ref for ref in hl_refs if ref.hierarchical_id}
    allowed_edges = {
        ("20", "21"),
        ("21", "22"),
    }

    root = hl_refs[0]
    if root.level_code != "20":
        issues.append(
            issue(
                level=SnipLevel.SNIP4,
                code="SNIP4_INVALID_HL03_SEQUENCE",
                message=(
                    f"The first HL must be level 20 (information source), got "
                    f"'{root.level_code or ''}'."
                ),
                location=f"{root.location}.03",
                segment_id="HL",
                element="03",
                suggestion="Start the hierarchy with HL03=20.",
            )
        )
    if root.parent_id not in {None, ""}:
        issues.append(
            issue(
                level=SnipLevel.SNIP4,
                code="SNIP4_ROOT_PARENT_NOT_ALLOWED",
                message="The top-level HL segment cannot reference a parent HL.",
                location=f"{root.location}.02",
                segment_id="HL",
                element="02",
                suggestion="Leave HL02 blank on the root 2000A HL segment.",
            )
        )

    for ref in hl_refs[1:]:
        if not ref.parent_id or ref.parent_id not in hl_by_id:
            issues.append(
                issue(
                    level=SnipLevel.SNIP4,
                    code="SNIP4_INVALID_HL_PARENT",
                    message=(
                        f"HL at {ref.location} references parent '{ref.parent_id or ''}', "
                        "but that HL ID does not exist."
                    ),
                    location=f"{ref.location}.02",
                    segment_id="HL",
                    element="02",
                    suggestion="Set HL02 to an existing parent HL01 value.",
                )
            )
            continue

        parent_ref = hl_by_id[ref.parent_id]
        if (parent_ref.level_code, ref.level_code) not in allowed_edges:
            issues.append(
                issue(
                    level=SnipLevel.SNIP4,
                    code="SNIP4_INVALID_HL03_SEQUENCE",
                    message=(
                        f"HL level '{ref.level_code or ''}' cannot follow parent level "
                        f"'{parent_ref.level_code or ''}'."
                    ),
                    location=f"{ref.location}.03",
                    segment_id="HL",
                    element="03",
                    suggestion="Use the standard 20 -> 21 -> 22 hierarchy for 270/271.",
                )
            )

    return issues


def _collect_hl_refs(
    transaction: Transaction270 | Transaction271,
    group_index: int,
    transaction_index: int,
) -> list[_HLRef]:
    prefix = f"FunctionalGroup[{group_index}].Transaction[{transaction_index}]"
    refs: list[_HLRef] = []

    if isinstance(transaction, Transaction270):
        loop_2000a = getattr(transaction, "loop_2000a", None)
        if isinstance(loop_2000a, Loop2000A_270):
            refs.append(_hl_ref(loop_2000a.hl, f"{prefix}.Loop2000A.HL"))
            for receiver_index, receiver_loop in enumerate(as_list(loop_2000a.loop_2000b)):
                if not isinstance(receiver_loop, Loop2000B_270):
                    continue
                refs.append(_hl_ref(receiver_loop.hl, f"{prefix}.Loop2000B[{receiver_index}].HL"))
                for subscriber_index, subscriber_loop in enumerate(
                    as_list(receiver_loop.loop_2000c)
                ):
                    if not isinstance(subscriber_loop, Loop2000C_270):
                        continue
                    refs.append(
                        _hl_ref(
                            subscriber_loop.hl,
                            f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}].HL",
                        )
                    )
        return refs

    loop_2000a = getattr(transaction, "loop_2000a", None)
    if isinstance(loop_2000a, Loop2000A_271):
        refs.append(_hl_ref(loop_2000a.hl, f"{prefix}.Loop2000A.HL"))
        for receiver_index, receiver_loop in enumerate(as_list(loop_2000a.loop_2000b)):
            if not isinstance(receiver_loop, Loop2000B_271):
                continue
            refs.append(_hl_ref(receiver_loop.hl, f"{prefix}.Loop2000B[{receiver_index}].HL"))
            for subscriber_index, subscriber_loop in enumerate(as_list(receiver_loop.loop_2000c)):
                if not isinstance(subscriber_loop, Loop2000C_271):
                    continue
                refs.append(
                    _hl_ref(
                        subscriber_loop.hl,
                        f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}].HL",
                    )
                )
    return refs


def _hl_ref(hl: HLSegment, location: str) -> _HLRef:
    return _HLRef(
        level_code=normalize_str(getattr(hl, "hierarchical_level_code", None)),
        hierarchical_id=normalize_str(getattr(hl, "hierarchical_id_number", None)),
        parent_id=normalize_str(getattr(hl, "hierarchical_parent_id_number", None)),
        location=location,
    )


def _validate_nm1_contexts(
    transaction: Transaction270 | Transaction271,
    group_index: int,
    transaction_index: int,
) -> list[ValidationError]:
    issues: list[ValidationError] = []
    prefix = f"FunctionalGroup[{group_index}].Transaction[{transaction_index}]"

    if isinstance(transaction, Transaction270):
        loop_2000a = getattr(transaction, "loop_2000a", None)
        if isinstance(loop_2000a, Loop2000A_270):
            issues.extend(
                _expect_nm1_entity(
                    getattr(getattr(loop_2000a, "loop_2100a", None), "nm1", None),
                    expected=EntityIdentifierCode.PAYER.value,
                    location=f"{prefix}.Loop2100A.NM1.01",
                    loop_name="2100A payer",
                )
            )
            for receiver_index, receiver_loop in enumerate(as_list(loop_2000a.loop_2000b)):
                if not isinstance(receiver_loop, Loop2000B_270):
                    continue
                issues.extend(
                    _expect_nm1_entity(
                        getattr(getattr(receiver_loop, "loop_2100b", None), "nm1", None),
                        expected=EntityIdentifierCode.PROVIDER.value,
                        location=f"{prefix}.Loop2000B[{receiver_index}].Loop2100B.NM1.01",
                        loop_name="2100B provider",
                    )
                )
                for subscriber_index, subscriber_loop in enumerate(
                    as_list(receiver_loop.loop_2000c)
                ):
                    if not isinstance(subscriber_loop, Loop2000C_270):
                        continue
                    issues.extend(
                        _expect_nm1_entity(
                            getattr(getattr(subscriber_loop, "loop_2100c", None), "nm1", None),
                            expected=EntityIdentifierCode.SUBSCRIBER.value,
                            location=(
                                f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                                f"[{subscriber_index}].Loop2100C.NM1.01"
                            ),
                            loop_name="2100C subscriber",
                        )
                    )
        return issues

    loop_2000a = getattr(transaction, "loop_2000a", None)
    if isinstance(loop_2000a, Loop2000A_271):
        issues.extend(
            _expect_nm1_entity(
                getattr(getattr(loop_2000a, "loop_2100a", None), "nm1", None),
                expected=EntityIdentifierCode.PAYER.value,
                location=f"{prefix}.Loop2100A.NM1.01",
                loop_name="2100A payer",
            )
        )
        for receiver_index, receiver_loop in enumerate(as_list(loop_2000a.loop_2000b)):
            if not isinstance(receiver_loop, Loop2000B_271):
                continue
            issues.extend(
                _expect_nm1_entity(
                    getattr(getattr(receiver_loop, "loop_2100b", None), "nm1", None),
                    expected=EntityIdentifierCode.PROVIDER.value,
                    location=f"{prefix}.Loop2000B[{receiver_index}].Loop2100B.NM1.01",
                    loop_name="2100B provider",
                )
            )
            for subscriber_index, subscriber_loop in enumerate(as_list(receiver_loop.loop_2000c)):
                if not isinstance(subscriber_loop, Loop2000C_271):
                    continue
                issues.extend(
                    _expect_nm1_entity(
                        getattr(getattr(subscriber_loop, "loop_2100c", None), "nm1", None),
                        expected=EntityIdentifierCode.SUBSCRIBER.value,
                        location=(
                            f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                            f"[{subscriber_index}].Loop2100C.NM1.01"
                        ),
                        loop_name="2100C subscriber",
                    )
                )

    return issues


def _expect_nm1_entity(
    nm1: object,
    *,
    expected: str,
    location: str,
    loop_name: str,
) -> list[ValidationError]:
    if not isinstance(nm1, NM1Segment):
        return []
    actual = normalize_str(getattr(nm1, "entity_identifier_code", None))
    if actual == expected:
        return []
    return [
        issue(
            level=SnipLevel.SNIP4,
            code="SNIP4_INVALID_NM101_CONTEXT",
            message=(f"{loop_name} NM101 must be '{expected}', but got '{actual or ''}'."),
            location=location,
            segment_id="NM1",
            element="01",
            suggestion=f"Set NM101 to '{expected}' in the {loop_name} loop.",
        )
    ]


def _validate_dtp_formats(
    transaction: Transaction270 | Transaction271,
    group_index: int,
    transaction_index: int,
) -> list[ValidationError]:
    issues: list[ValidationError] = []
    prefix = f"FunctionalGroup[{group_index}].Transaction[{transaction_index}]"
    dtp_refs = _collect_dtp_refs(transaction, prefix)

    for location, dtp in dtp_refs:
        if not isinstance(dtp, DTPSegment):
            continue
        qualifier = normalize_str(getattr(dtp, "date_time_period_format_qualifier", None))
        period = normalize_str(getattr(dtp, "date_time_period", None)) or ""
        pattern = _DTP_PATTERNS.get(qualifier or "")
        if pattern is None:
            issues.append(
                issue(
                    level=SnipLevel.SNIP4,
                    code="SNIP4_UNSUPPORTED_DTP_FORMAT",
                    message=(
                        f"DTP02 format qualifier '{qualifier or ''}' is not supported by "
                        "the current validator."
                    ),
                    location=f"{location}.02",
                    segment_id="DTP",
                    element="02",
                    suggestion="Use a supported DTP02 value such as D8 or RD8.",
                )
            )
            continue
        if not re.fullmatch(pattern, period):
            issues.append(
                issue(
                    level=SnipLevel.SNIP4,
                    code="SNIP4_DTP_FORMAT_MISMATCH",
                    message=(
                        f"DTP03 value '{period}' does not match the DTP02 qualifier '{qualifier}'."
                    ),
                    location=f"{location}.03",
                    segment_id="DTP",
                    element="03",
                    suggestion="Format DTP03 to match DTP02, for example YYYYMMDD for D8.",
                )
            )

    return issues


def _collect_dtp_refs(
    transaction: Transaction270 | Transaction271,
    prefix: str,
) -> list[tuple[str, DTPSegment]]:
    refs: list[tuple[str, DTPSegment]] = []

    if isinstance(transaction, Transaction270):
        loop_2000a = getattr(transaction, "loop_2000a", None)
        if not isinstance(loop_2000a, Loop2000A_270):
            return refs
        for receiver_index, receiver_loop in enumerate(as_list(loop_2000a.loop_2000b)):
            if not isinstance(receiver_loop, Loop2000B_270):
                continue
            for subscriber_index, subscriber_loop in enumerate(as_list(receiver_loop.loop_2000c)):
                if not isinstance(subscriber_loop, Loop2000C_270):
                    continue
                subscriber_prefix = (
                    f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}]"
                )
                for dtp_index, dtp in enumerate(subscriber_loop.loop_2100c.dtp_segments):
                    refs.append(
                        (
                            f"{subscriber_prefix}.Loop2100C.DTP[{dtp_index}]",
                            dtp,
                        )
                    )
                for inquiry_index, inquiry_loop in enumerate(as_list(subscriber_loop.loop_2110c)):
                    for dtp_index, dtp in enumerate(
                        as_list(getattr(inquiry_loop, "dtp_segments", []))
                    ):
                        if isinstance(dtp, DTPSegment):
                            refs.append(
                                (
                                    f"{subscriber_prefix}.Loop2110C[{inquiry_index}].DTP"
                                    f"[{dtp_index}]",
                                    dtp,
                                )
                            )
        return refs

    loop_2000a = getattr(transaction, "loop_2000a", None)
    if not isinstance(loop_2000a, Loop2000A_271):
        return refs
    for receiver_index, receiver_loop in enumerate(as_list(loop_2000a.loop_2000b)):
        if not isinstance(receiver_loop, Loop2000B_271):
            continue
        for subscriber_index, subscriber_loop in enumerate(as_list(receiver_loop.loop_2000c)):
            if not isinstance(subscriber_loop, Loop2000C_271):
                continue
            for inquiry_index, inquiry_loop in enumerate(as_list(subscriber_loop.loop_2110c)):
                for dtp_index, dtp in enumerate(as_list(getattr(inquiry_loop, "dtp_segments", []))):
                    if isinstance(dtp, DTPSegment):
                        refs.append(
                            (
                                f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                                f"[{subscriber_index}].Loop2110C[{inquiry_index}].DTP"
                                f"[{dtp_index}]",
                                dtp,
                            )
                        )

    return refs
