"""Top-level X12 encoding orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypeAlias

from x12_edi_tools._logging import build_log_extra, get_logger
from x12_edi_tools.common.delimiters import Delimiters
from x12_edi_tools.config import SubmitterConfig
from x12_edi_tools.encoder.isa_encoder import encode_isa
from x12_edi_tools.encoder.segment_encoder import encode_segment
from x12_edi_tools.exceptions import X12EncodeError
from x12_edi_tools.models.base import GenericSegment, X12Segment
from x12_edi_tools.models.loops import (
    Loop2000A_270,
    Loop2000A_271,
    Loop2000B_270,
    Loop2000B_271,
    Loop2000C_270,
    Loop2000C_271,
    Loop2100A_270,
    Loop2100A_271,
    Loop2100B_270,
    Loop2100B_271,
    Loop2100C_270,
    Loop2100C_271,
    Loop2110C_270,
    Loop2110C_271,
)
from x12_edi_tools.models.transactions import (
    FunctionalGroup,
    Interchange,
    Transaction270,
    Transaction271,
)

BodySegment: TypeAlias = X12Segment | GenericSegment
TransactionModel: TypeAlias = Transaction270 | Transaction271
logger = get_logger(__name__)


@dataclass(slots=True)
class _ControlNumberState:
    next_isa: int
    next_gs: int
    next_st: int
    regenerate: bool

    def next_interchange_control(self, existing: str) -> str:
        if not self.regenerate:
            return existing
        control_number = f"{self.next_isa:09d}"
        self.next_isa += 1
        return control_number

    def next_group_control(self, existing: str) -> str:
        if not self.regenerate:
            return existing
        control_number = str(self.next_gs)
        self.next_gs += 1
        return control_number

    def next_transaction_control(self, existing: str) -> str:
        if not self.regenerate:
            return existing
        control_number = f"{self.next_st:04d}"
        self.next_st += 1
        return control_number


def encode(
    interchange: Interchange | list[Interchange],
    *,
    delimiters: Delimiters | None = None,
    config: SubmitterConfig | None = None,
    correlation_id: str | None = None,
) -> str | list[str]:
    """Encode one interchange to a string or many interchanges to a list of strings.

    Single-interchange encodes preserve existing control numbers by default so
    parse/encode roundtrips remain stable. Passing ``config`` or encoding a list
    regenerates control numbers using the configured or default starting values.
    """

    interchanges = interchange if isinstance(interchange, list) else [interchange]
    if not interchanges:
        raise X12EncodeError("encode() requires at least one interchange")

    logger.info(
        "x12_encode_started",
        extra=build_log_extra(
            correlation_id=correlation_id,
            interchange_count=len(interchanges),
            override_delimiters=delimiters is not None,
            regenerate_control_numbers=config is not None or len(interchanges) > 1,
        ),
    )

    control_numbers = _build_control_number_state(
        interchange_count=len(interchanges),
        config=config,
    )
    rendered = [
        _encode_one_interchange(
            item,
            delimiters=delimiters or item.delimiters,
            control_numbers=control_numbers,
        )
        for item in interchanges
    ]
    logger.info(
        "x12_encode_completed",
        extra=build_log_extra(
            correlation_id=correlation_id,
            interchange_count=len(interchanges),
            transaction_count=sum(
                len(group.transactions) for item in interchanges for group in item.functional_groups
            ),
            rendered_bytes=sum(len(document.encode("utf-8")) for document in rendered),
        ),
    )
    return rendered if isinstance(interchange, list) else rendered[0]


def _build_control_number_state(
    *,
    interchange_count: int,
    config: SubmitterConfig | None,
) -> _ControlNumberState:
    regenerate = config is not None or interchange_count > 1
    return _ControlNumberState(
        next_isa=(
            config.isa_control_number_start if config and config.isa_control_number_start else 1
        ),
        next_gs=(
            config.gs_control_number_start if config and config.gs_control_number_start else 1
        ),
        next_st=(
            config.st_control_number_start if config and config.st_control_number_start else 1
        ),
        regenerate=regenerate,
    )


def _encode_one_interchange(
    interchange: Interchange,
    *,
    delimiters: Delimiters,
    control_numbers: _ControlNumberState,
) -> str:
    if not interchange.functional_groups:
        raise X12EncodeError("Interchange must contain at least one functional group")

    isa_control_number = control_numbers.next_interchange_control(
        interchange.isa.interchange_control_number
    )
    isa_segment = interchange.isa.model_copy(
        update={
            "interchange_control_number": isa_control_number,
            "repetition_separator": delimiters.repetition,
            "component_element_separator": delimiters.sub_element,
        }
    )
    iea_segment = interchange.iea.model_copy(
        update={
            "number_of_included_functional_groups": len(interchange.functional_groups),
            "interchange_control_number": isa_control_number,
        }
    )

    parts = [encode_isa(isa_segment, delimiters=delimiters)]
    parts.extend(
        _encode_functional_group(
            group,
            delimiters=delimiters,
            control_numbers=control_numbers,
        )
        for group in interchange.functional_groups
    )
    parts.append(encode_segment(iea_segment, delimiters=delimiters))
    return "".join(parts)


def _encode_functional_group(
    group: FunctionalGroup,
    *,
    delimiters: Delimiters,
    control_numbers: _ControlNumberState,
) -> str:
    if not group.transactions:
        raise X12EncodeError("Functional groups must contain at least one transaction")

    group_control_number = control_numbers.next_group_control(group.gs.group_control_number)
    gs_segment = group.gs.model_copy(update={"group_control_number": group_control_number})
    ge_segment = group.ge.model_copy(
        update={
            "number_of_transaction_sets_included": len(group.transactions),
            "group_control_number": group_control_number,
        }
    )

    body = [encode_segment(gs_segment, delimiters=delimiters)]
    body.extend(
        _encode_transaction(
            transaction,
            delimiters=delimiters,
            control_numbers=control_numbers,
        )
        for transaction in group.transactions
    )
    body.append(encode_segment(ge_segment, delimiters=delimiters))
    return "".join(body)


def _encode_transaction(
    transaction: TransactionModel,
    *,
    delimiters: Delimiters,
    control_numbers: _ControlNumberState,
) -> str:
    control_number = control_numbers.next_transaction_control(
        transaction.st.transaction_set_control_number
    )
    body_segments = _materialize_transaction_body(transaction)

    st_segment = transaction.st.model_copy(
        update={"transaction_set_control_number": control_number}
    )
    se_segment = transaction.se.model_copy(
        update={
            "number_of_included_segments": len(body_segments) + 3,
            "transaction_set_control_number": control_number,
        }
    )

    rendered = [encode_segment(st_segment, delimiters=delimiters)]
    rendered.append(encode_segment(transaction.bht, delimiters=delimiters))
    rendered.extend(encode_segment(segment, delimiters=delimiters) for segment in body_segments)
    rendered.append(encode_segment(se_segment, delimiters=delimiters))
    return "".join(rendered)


def _materialize_transaction_body(transaction: TransactionModel) -> list[BodySegment]:
    if isinstance(transaction, Transaction270):
        typed_segments = list(_iter_270_body_segments(transaction))
    else:
        typed_segments = list(_iter_271_body_segments(transaction))
    return _inject_generic_segments(typed_segments, transaction.generic_segments)


def _inject_generic_segments(
    typed_segments: list[X12Segment],
    generic_segments: list[GenericSegment],
) -> list[BodySegment]:
    if not generic_segments:
        return [*typed_segments]

    indexed_generic_segments = [
        segment for segment in generic_segments if segment.body_index is not None
    ]
    trailing_generic_segments = [
        segment for segment in generic_segments if segment.body_index is None
    ]
    if not indexed_generic_segments:
        merged_without_indexes: list[BodySegment] = [*typed_segments, *trailing_generic_segments]
        return merged_without_indexes

    indexed_generic_segments.sort(key=lambda segment: segment.body_index or 0)
    merged: list[BodySegment] = []
    generic_index = 0
    overall_index = 0

    for segment in typed_segments:
        while (
            generic_index < len(indexed_generic_segments)
            and indexed_generic_segments[generic_index].body_index == overall_index
        ):
            merged.append(indexed_generic_segments[generic_index])
            generic_index += 1
            overall_index += 1
        merged.append(segment)
        overall_index += 1

    while generic_index < len(indexed_generic_segments):
        merged.append(indexed_generic_segments[generic_index])
        generic_index += 1

    merged.extend(trailing_generic_segments)
    return merged


def _iter_270_body_segments(transaction: Transaction270) -> Iterable[X12Segment]:
    yield from _iter_loop_2000a_270(transaction.loop_2000a)


def _iter_loop_2000a_270(loop: Loop2000A_270) -> Iterable[X12Segment]:
    yield loop.hl
    if loop.loop_2100a is not None:
        yield from _iter_loop_2100a_270(loop.loop_2100a)
    for child_loop in loop.loop_2000b:
        yield from _iter_loop_2000b_270(child_loop)


def _iter_loop_2100a_270(loop: Loop2100A_270) -> Iterable[X12Segment]:
    yield loop.nm1
    yield from loop.ref_segments


def _iter_loop_2000b_270(loop: Loop2000B_270) -> Iterable[X12Segment]:
    yield loop.hl
    if loop.loop_2100b is not None:
        yield from _iter_loop_2100b_270(loop.loop_2100b)
    for child_loop in loop.loop_2000c:
        yield from _iter_loop_2000c_270(child_loop)


def _iter_loop_2100b_270(loop: Loop2100B_270) -> Iterable[X12Segment]:
    yield loop.nm1
    if loop.prv is not None:
        yield loop.prv
    if loop.per is not None:
        yield loop.per
    if loop.n3 is not None:
        yield loop.n3
    if loop.n4 is not None:
        yield loop.n4
    yield from loop.ref_segments


def _iter_loop_2000c_270(loop: Loop2000C_270) -> Iterable[X12Segment]:
    yield loop.hl
    if loop.trn is not None:
        yield loop.trn
    yield from _iter_loop_2100c_270(loop.loop_2100c)
    for child_loop in loop.loop_2110c:
        yield from _iter_loop_2110c_270(child_loop)


def _iter_loop_2100c_270(loop: Loop2100C_270) -> Iterable[X12Segment]:
    yield loop.nm1
    if loop.dmg is not None:
        yield loop.dmg
    yield from loop.ref_segments
    yield from loop.dtp_segments


def _iter_loop_2110c_270(loop: Loop2110C_270) -> Iterable[X12Segment]:
    yield from loop.eq_segments
    yield from loop.dtp_segments
    yield from loop.ref_segments


def _iter_271_body_segments(transaction: Transaction271) -> Iterable[X12Segment]:
    yield from _iter_loop_2000a_271(transaction.loop_2000a)


def _iter_loop_2000a_271(loop: Loop2000A_271) -> Iterable[X12Segment]:
    yield loop.hl
    yield from loop.aaa_segments
    if loop.loop_2100a is not None:
        yield from _iter_loop_2100a_271(loop.loop_2100a)
    for child_loop in loop.loop_2000b:
        yield from _iter_loop_2000b_271(child_loop)


def _iter_loop_2100a_271(loop: Loop2100A_271) -> Iterable[X12Segment]:
    yield loop.nm1
    yield from loop.aaa_segments
    yield from loop.ref_segments


def _iter_loop_2000b_271(loop: Loop2000B_271) -> Iterable[X12Segment]:
    yield loop.hl
    yield from loop.aaa_segments
    if loop.loop_2100b is not None:
        yield from _iter_loop_2100b_271(loop.loop_2100b)
    for child_loop in loop.loop_2000c:
        yield from _iter_loop_2000c_271(child_loop)


def _iter_loop_2100b_271(loop: Loop2100B_271) -> Iterable[X12Segment]:
    yield loop.nm1
    if loop.per is not None:
        yield loop.per
    if loop.n3 is not None:
        yield loop.n3
    if loop.n4 is not None:
        yield loop.n4
    yield from loop.ref_segments


def _iter_loop_2000c_271(loop: Loop2000C_271) -> Iterable[X12Segment]:
    yield loop.hl
    if loop.trn is not None:
        yield loop.trn
    yield from loop.aaa_segments
    yield from _iter_loop_2100c_271(loop.loop_2100c)
    for child_loop in loop.loop_2110c:
        yield from _iter_loop_2110c_271(child_loop)


def _iter_loop_2100c_271(loop: Loop2100C_271) -> Iterable[X12Segment]:
    yield loop.nm1
    if loop.dmg is not None:
        yield loop.dmg
    if loop.n3 is not None:
        yield loop.n3
    if loop.n4 is not None:
        yield loop.n4
    yield from loop.aaa_segments
    yield from loop.ref_segments


def _iter_loop_2110c_271(loop: Loop2110C_271) -> Iterable[X12Segment]:
    yield from loop.eb_segments
    yield from loop.aaa_segments
    if loop.ls_segment is not None:
        yield loop.ls_segment
    yield from loop.ref_segments
    if loop.le_segment is not None:
        yield loop.le_segment
    yield from loop.dtp_segments
