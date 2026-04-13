"""Loop-building state machine for 270/271 eligibility transactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NoReturn, TypeAlias, TypeVar

from x12_edi_tools.common.enums import EntityIdentifierCode, HierarchicalLevelCode
from x12_edi_tools.common.types import SegmentToken
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
from x12_edi_tools.models.segments import (
    AAASegment,
    BHTSegment,
    DMGSegment,
    DTPSegment,
    EBSegment,
    EQSegment,
    HLSegment,
    LESegment,
    LSSegment,
    N3Segment,
    N4Segment,
    NM1Segment,
    PERSegment,
    PRVSegment,
    REFSegment,
    SESegment,
    STSegment,
    TRNSegment,
)
from x12_edi_tools.models.transactions import Transaction270, Transaction271
from x12_edi_tools.parser._exceptions import ParserComponentError
from x12_edi_tools.parser.segment_parser import ParsedSegment, render_raw_segment

ParsedSegmentPair: TypeAlias = tuple[ParsedSegment, SegmentToken]
SegmentModelT = TypeVar("SegmentModelT", bound=X12Segment)


def build_transaction(
    segment_pairs: list[ParsedSegmentPair],
    *,
    element_separator: str,
) -> Transaction270 | Transaction271:
    """Build a typed transaction model from parsed segments."""

    if len(segment_pairs) < 4:
        token = segment_pairs[0][1] if segment_pairs else SegmentToken("?", (), 0)
        _raise_builder_error(
            token,
            element_separator=element_separator,
            message="Transaction is incomplete",
            error="incomplete_transaction",
            suggestion=(
                "Ensure each transaction contains ST, BHT, at least one HL hierarchy, and SE"
            ),
        )

    st = _expect_segment(segment_pairs[0], STSegment, element_separator=element_separator)
    bht = _expect_segment(segment_pairs[1], BHTSegment, element_separator=element_separator)
    se = _expect_segment(segment_pairs[-1], SESegment, element_separator=element_separator)
    body = segment_pairs[2:-1]
    generic_segments = [
        segment.model_copy(update={"body_index": body_index})
        for body_index, (segment, _) in enumerate(body)
        if isinstance(segment, GenericSegment)
    ]

    transaction_type = st.transaction_set_identifier_code
    if transaction_type == "270":
        loop_2000a_270 = _build_270_hierarchy(body, element_separator=element_separator)
        return Transaction270(
            st=st,
            bht=bht,
            loop_2000a=loop_2000a_270,
            se=se,
            generic_segments=generic_segments,
        )
    if transaction_type == "271":
        loop_2000a_271 = _build_271_hierarchy(body, element_separator=element_separator)
        return Transaction271(
            st=st,
            bht=bht,
            loop_2000a=loop_2000a_271,
            se=se,
            generic_segments=generic_segments,
        )

    _raise_builder_error(
        segment_pairs[0][1],
        element_separator=element_separator,
        message=f"Unsupported transaction set '{transaction_type}'",
        error="unsupported_transaction",
        suggestion="Only 270 and 271 transactions are supported in Phase 2",
    )


@dataclass(slots=True)
class _Loop2100A270State:
    nm1: NM1Segment
    ref_segments: list[REFSegment] = field(default_factory=list)

    def build(self) -> Loop2100A_270:
        return Loop2100A_270(nm1=self.nm1, ref_segments=list(self.ref_segments))


@dataclass(slots=True)
class _Loop2100A271State:
    nm1: NM1Segment
    aaa_segments: list[AAASegment] = field(default_factory=list)
    ref_segments: list[REFSegment] = field(default_factory=list)

    def build(self) -> Loop2100A_271:
        return Loop2100A_271(
            nm1=self.nm1,
            aaa_segments=list(self.aaa_segments),
            ref_segments=list(self.ref_segments),
        )


@dataclass(slots=True)
class _Loop2100B270State:
    nm1: NM1Segment
    prv: PRVSegment | None = None
    per: PERSegment | None = None
    n3: N3Segment | None = None
    n4: N4Segment | None = None
    ref_segments: list[REFSegment] = field(default_factory=list)

    def build(self) -> Loop2100B_270:
        return Loop2100B_270(
            nm1=self.nm1,
            prv=self.prv,
            per=self.per,
            n3=self.n3,
            n4=self.n4,
            ref_segments=list(self.ref_segments),
        )


@dataclass(slots=True)
class _Loop2100B271State:
    nm1: NM1Segment
    per: PERSegment | None = None
    n3: N3Segment | None = None
    n4: N4Segment | None = None
    ref_segments: list[REFSegment] = field(default_factory=list)

    def build(self) -> Loop2100B_271:
        return Loop2100B_271(
            nm1=self.nm1,
            per=self.per,
            n3=self.n3,
            n4=self.n4,
            ref_segments=list(self.ref_segments),
        )


@dataclass(slots=True)
class _Loop2100C270State:
    nm1: NM1Segment
    dmg: DMGSegment | None = None
    ref_segments: list[REFSegment] = field(default_factory=list)

    def build(self) -> Loop2100C_270:
        return Loop2100C_270(
            nm1=self.nm1,
            dmg=self.dmg,
            ref_segments=list(self.ref_segments),
        )


@dataclass(slots=True)
class _Loop2100C271State:
    nm1: NM1Segment
    dmg: DMGSegment | None = None
    n3: N3Segment | None = None
    n4: N4Segment | None = None
    aaa_segments: list[AAASegment] = field(default_factory=list)
    ref_segments: list[REFSegment] = field(default_factory=list)

    def build(self) -> Loop2100C_271:
        return Loop2100C_271(
            nm1=self.nm1,
            dmg=self.dmg,
            n3=self.n3,
            n4=self.n4,
            aaa_segments=list(self.aaa_segments),
            ref_segments=list(self.ref_segments),
        )


@dataclass(slots=True)
class _Loop2110C270State:
    eq_segments: list[EQSegment] = field(default_factory=list)
    dtp_segments: list[DTPSegment] = field(default_factory=list)
    ref_segments: list[REFSegment] = field(default_factory=list)

    def build(self) -> Loop2110C_270:
        return Loop2110C_270(
            eq_segments=list(self.eq_segments),
            dtp_segments=list(self.dtp_segments),
            ref_segments=list(self.ref_segments),
        )


@dataclass(slots=True)
class _Loop2110C271State:
    eb_segments: list[EBSegment] = field(default_factory=list)
    aaa_segments: list[AAASegment] = field(default_factory=list)
    ref_segments: list[REFSegment] = field(default_factory=list)
    dtp_segments: list[DTPSegment] = field(default_factory=list)
    ls_segment: LSSegment | None = None
    le_segment: LESegment | None = None

    def build(self) -> Loop2110C_271:
        return Loop2110C_271(
            eb_segments=list(self.eb_segments),
            aaa_segments=list(self.aaa_segments),
            ref_segments=list(self.ref_segments),
            dtp_segments=list(self.dtp_segments),
            ls_segment=self.ls_segment,
            le_segment=self.le_segment,
        )


@dataclass(slots=True)
class _Loop2000C270State:
    hl: HLSegment
    trn: TRNSegment | None = None
    loop_2100c: _Loop2100C270State | None = None
    loop_2110c: list[_Loop2110C270State] = field(default_factory=list)

    def build(self) -> Loop2000C_270:
        if self.loop_2100c is None:
            raise ValueError("Loop 2000C (270) is missing required 2100C NM1 data")
        return Loop2000C_270(
            hl=self.hl,
            trn=self.trn,
            loop_2100c=self.loop_2100c.build(),
            loop_2110c=[item.build() for item in self.loop_2110c],
        )


@dataclass(slots=True)
class _Loop2000C271State:
    hl: HLSegment
    trn: TRNSegment | None = None
    aaa_segments: list[AAASegment] = field(default_factory=list)
    loop_2100c: _Loop2100C271State | None = None
    loop_2110c: list[_Loop2110C271State] = field(default_factory=list)

    def build(self) -> Loop2000C_271:
        if self.loop_2100c is None:
            raise ValueError("Loop 2000C (271) is missing required 2100C NM1 data")
        return Loop2000C_271(
            hl=self.hl,
            trn=self.trn,
            aaa_segments=list(self.aaa_segments),
            loop_2100c=self.loop_2100c.build(),
            loop_2110c=[item.build() for item in self.loop_2110c],
        )


@dataclass(slots=True)
class _Loop2000B270State:
    hl: HLSegment
    loop_2100b: _Loop2100B270State | None = None
    loop_2000c: list[_Loop2000C270State] = field(default_factory=list)

    def build(self) -> Loop2000B_270:
        return Loop2000B_270(
            hl=self.hl,
            loop_2100b=self.loop_2100b.build() if self.loop_2100b else None,
            loop_2000c=[item.build() for item in self.loop_2000c],
        )


@dataclass(slots=True)
class _Loop2000B271State:
    hl: HLSegment
    aaa_segments: list[AAASegment] = field(default_factory=list)
    loop_2100b: _Loop2100B271State | None = None
    loop_2000c: list[_Loop2000C271State] = field(default_factory=list)

    def build(self) -> Loop2000B_271:
        return Loop2000B_271(
            hl=self.hl,
            aaa_segments=list(self.aaa_segments),
            loop_2100b=self.loop_2100b.build() if self.loop_2100b else None,
            loop_2000c=[item.build() for item in self.loop_2000c],
        )


@dataclass(slots=True)
class _Loop2000A270State:
    hl: HLSegment
    loop_2100a: _Loop2100A270State | None = None
    loop_2000b: list[_Loop2000B270State] = field(default_factory=list)

    def build(self) -> Loop2000A_270:
        return Loop2000A_270(
            hl=self.hl,
            loop_2100a=self.loop_2100a.build() if self.loop_2100a else None,
            loop_2000b=[item.build() for item in self.loop_2000b],
        )


@dataclass(slots=True)
class _Loop2000A271State:
    hl: HLSegment
    aaa_segments: list[AAASegment] = field(default_factory=list)
    loop_2100a: _Loop2100A271State | None = None
    loop_2000b: list[_Loop2000B271State] = field(default_factory=list)

    def build(self) -> Loop2000A_271:
        return Loop2000A_271(
            hl=self.hl,
            aaa_segments=list(self.aaa_segments),
            loop_2100a=self.loop_2100a.build() if self.loop_2100a else None,
            loop_2000b=[item.build() for item in self.loop_2000b],
        )


def _build_270_hierarchy(
    body: list[ParsedSegmentPair],
    *,
    element_separator: str,
) -> Loop2000A_270:
    root_2000a: _Loop2000A270State | None = None
    current_2000a: _Loop2000A270State | None = None
    current_2000b: _Loop2000B270State | None = None
    current_2000c: _Loop2000C270State | None = None
    current_2110c: _Loop2110C270State | None = None

    for segment, token in body:
        if isinstance(segment, GenericSegment):
            continue

        if isinstance(segment, HLSegment):
            if segment.hierarchical_level_code == HierarchicalLevelCode.INFORMATION_SOURCE:
                current_2000a = _Loop2000A270State(hl=segment)
                root_2000a = current_2000a
                current_2000b = None
                current_2000c = None
                current_2110c = None
                continue
            if segment.hierarchical_level_code == HierarchicalLevelCode.INFORMATION_RECEIVER:
                if current_2000a is None:
                    _raise_builder_error(
                        token,
                        element_separator=element_separator,
                        message="Encountered 2000B HL before 2000A",
                        error="unexpected_hl",
                        suggestion="Start the hierarchy with HL level code 20",
                    )
                current_2000b = _Loop2000B270State(hl=segment)
                current_2000a.loop_2000b.append(current_2000b)
                current_2000c = None
                current_2110c = None
                continue
            if segment.hierarchical_level_code == HierarchicalLevelCode.SUBSCRIBER:
                if current_2000b is None:
                    _raise_builder_error(
                        token,
                        element_separator=element_separator,
                        message="Encountered 2000C HL before 2000B",
                        error="unexpected_hl",
                        suggestion=(
                            "Subscriber loops must be nested under a 2000B information receiver"
                        ),
                    )
                current_2000c = _Loop2000C270State(hl=segment)
                current_2000b.loop_2000c.append(current_2000c)
                current_2110c = None
                continue

        if isinstance(segment, NM1Segment):
            if segment.entity_identifier_code == EntityIdentifierCode.PAYER:
                if current_2000a is None:
                    _raise_builder_error(
                        token,
                        element_separator=element_separator,
                        message="NM1*PR must follow the 2000A HL segment",
                        error="unexpected_nm1",
                    )
                current_2000a.loop_2100a = _Loop2100A270State(nm1=segment)
                continue
            if segment.entity_identifier_code == EntityIdentifierCode.PROVIDER:
                if current_2000b is None:
                    _raise_builder_error(
                        token,
                        element_separator=element_separator,
                        message="NM1*1P must follow the 2000B HL segment",
                        error="unexpected_nm1",
                    )
                current_2000b.loop_2100b = _Loop2100B270State(nm1=segment)
                continue
            if segment.entity_identifier_code == EntityIdentifierCode.SUBSCRIBER:
                if current_2000c is None:
                    _raise_builder_error(
                        token,
                        element_separator=element_separator,
                        message="NM1*IL must follow the 2000C HL segment",
                        error="unexpected_nm1",
                    )
                current_2000c.loop_2100c = _Loop2100C270State(nm1=segment)
                continue

        if isinstance(segment, TRNSegment):
            if current_2000c is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="TRN must appear within loop 2000C",
                    error="unexpected_trn",
                )
            current_2000c.trn = segment
            continue

        if isinstance(segment, PRVSegment):
            target = current_2000b.loop_2100b if current_2000b else None
            if target is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="PRV must appear within loop 2100B",
                    error="unexpected_prv",
                )
            target.prv = segment
            continue

        if isinstance(segment, PERSegment):
            target = current_2000b.loop_2100b if current_2000b else None
            if target is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="PER must appear within loop 2100B",
                    error="unexpected_per",
                )
            target.per = segment
            continue

        if isinstance(segment, N3Segment):
            target = current_2000b.loop_2100b if current_2000b else None
            if target is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="N3 must appear within loop 2100B",
                    error="unexpected_n3",
                )
            target.n3 = segment
            continue

        if isinstance(segment, N4Segment):
            target = current_2000b.loop_2100b if current_2000b else None
            if target is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="N4 must appear within loop 2100B",
                    error="unexpected_n4",
                )
            target.n4 = segment
            continue

        if isinstance(segment, DMGSegment):
            target_2100c = current_2000c.loop_2100c if current_2000c else None
            if target_2100c is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="DMG must appear within loop 2100C",
                    error="unexpected_dmg",
                )
            target_2100c.dmg = segment
            continue

        if isinstance(segment, REFSegment):
            _append_270_ref(
                ref_segment=segment,
                current_2000a=current_2000a,
                current_2000b=current_2000b,
                current_2000c=current_2000c,
                current_2110c=current_2110c,
                token=token,
                element_separator=element_separator,
            )
            continue

        if isinstance(segment, EQSegment):
            if current_2000c is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="EQ must appear within loop 2000C",
                    error="unexpected_eq",
                )
            if current_2110c is None:
                current_2110c = _Loop2110C270State()
                current_2000c.loop_2110c.append(current_2110c)
            current_2110c.eq_segments.append(segment)
            continue

        if isinstance(segment, DTPSegment):
            if current_2000c is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="DTP must appear within loop 2000C",
                    error="unexpected_dtp",
                )
            if current_2110c is None:
                current_2110c = _Loop2110C270State()
                current_2000c.loop_2110c.append(current_2110c)
            current_2110c.dtp_segments.append(segment)
            continue

        _raise_builder_error(
            token,
            element_separator=element_separator,
            message=f"Segment {segment.segment_id} is not supported in a 270 hierarchy",
            error="unsupported_segment_in_transaction",
        )

    if root_2000a is None:
        missing_token = body[0][1] if body else SegmentToken("HL", (), 0)
        _raise_builder_error(
            missing_token,
            element_separator=element_separator,
            message="Transaction is missing the 2000A hierarchy",
            error="missing_hierarchy",
            suggestion="Start the body with HL*...*20",
        )

    try:
        return root_2000a.build()
    except ValueError as exc:
        failing_token = body[-1][1] if body else SegmentToken("HL", (), 0)
        _raise_builder_error(
            failing_token,
            element_separator=element_separator,
            message=str(exc),
            error="incomplete_loop",
            suggestion="Ensure each subscriber loop includes an NM1 subscriber segment",
        )


def _build_271_hierarchy(
    body: list[ParsedSegmentPair],
    *,
    element_separator: str,
) -> Loop2000A_271:
    root_2000a: _Loop2000A271State | None = None
    current_2000a: _Loop2000A271State | None = None
    current_2000b: _Loop2000B271State | None = None
    current_2000c: _Loop2000C271State | None = None
    current_2110c: _Loop2110C271State | None = None

    for segment, token in body:
        if isinstance(segment, GenericSegment):
            continue

        if isinstance(segment, HLSegment):
            if segment.hierarchical_level_code == HierarchicalLevelCode.INFORMATION_SOURCE:
                current_2000a = _Loop2000A271State(hl=segment)
                root_2000a = current_2000a
                current_2000b = None
                current_2000c = None
                current_2110c = None
                continue
            if segment.hierarchical_level_code == HierarchicalLevelCode.INFORMATION_RECEIVER:
                if current_2000a is None:
                    _raise_builder_error(
                        token,
                        element_separator=element_separator,
                        message="Encountered 2000B HL before 2000A",
                        error="unexpected_hl",
                    )
                current_2000b = _Loop2000B271State(hl=segment)
                current_2000a.loop_2000b.append(current_2000b)
                current_2000c = None
                current_2110c = None
                continue
            if segment.hierarchical_level_code == HierarchicalLevelCode.SUBSCRIBER:
                if current_2000b is None:
                    _raise_builder_error(
                        token,
                        element_separator=element_separator,
                        message="Encountered 2000C HL before 2000B",
                        error="unexpected_hl",
                    )
                current_2000c = _Loop2000C271State(hl=segment)
                current_2000b.loop_2000c.append(current_2000c)
                current_2110c = None
                continue

        if isinstance(segment, NM1Segment):
            if segment.entity_identifier_code == EntityIdentifierCode.PAYER:
                if current_2000a is None:
                    _raise_builder_error(
                        token,
                        element_separator=element_separator,
                        message="NM1*PR must follow the 2000A HL segment",
                        error="unexpected_nm1",
                    )
                current_2000a.loop_2100a = _Loop2100A271State(nm1=segment)
                continue
            if segment.entity_identifier_code == EntityIdentifierCode.PROVIDER:
                if current_2000b is None:
                    _raise_builder_error(
                        token,
                        element_separator=element_separator,
                        message="NM1*1P must follow the 2000B HL segment",
                        error="unexpected_nm1",
                    )
                current_2000b.loop_2100b = _Loop2100B271State(nm1=segment)
                continue
            if segment.entity_identifier_code == EntityIdentifierCode.SUBSCRIBER:
                if current_2000c is None:
                    _raise_builder_error(
                        token,
                        element_separator=element_separator,
                        message="NM1*IL must follow the 2000C HL segment",
                        error="unexpected_nm1",
                    )
                current_2000c.loop_2100c = _Loop2100C271State(nm1=segment)
                continue

        if isinstance(segment, TRNSegment):
            if current_2000c is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="TRN must appear within loop 2000C",
                    error="unexpected_trn",
                )
            current_2000c.trn = segment
            continue

        if isinstance(segment, AAASegment):
            _append_271_aaa(
                aaa_segment=segment,
                current_2000a=current_2000a,
                current_2000b=current_2000b,
                current_2000c=current_2000c,
                current_2110c=current_2110c,
                token=token,
                element_separator=element_separator,
            )
            continue

        if isinstance(segment, PERSegment):
            target = current_2000b.loop_2100b if current_2000b else None
            if target is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="PER must appear within loop 2100B",
                    error="unexpected_per",
                )
            target.per = segment
            continue

        if isinstance(segment, N3Segment):
            if current_2000c and current_2000c.loop_2100c is not None:
                current_2000c.loop_2100c.n3 = segment
                continue
            target_2100b = current_2000b.loop_2100b if current_2000b else None
            if target_2100b is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="N3 must appear within loop 2100B or 2100C",
                    error="unexpected_n3",
                )
            target_2100b.n3 = segment
            continue

        if isinstance(segment, N4Segment):
            if current_2000c and current_2000c.loop_2100c is not None:
                current_2000c.loop_2100c.n4 = segment
                continue
            target_2100b = current_2000b.loop_2100b if current_2000b else None
            if target_2100b is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="N4 must appear within loop 2100B or 2100C",
                    error="unexpected_n4",
                )
            target_2100b.n4 = segment
            continue

        if isinstance(segment, DMGSegment):
            target_2100c = current_2000c.loop_2100c if current_2000c else None
            if target_2100c is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="DMG must appear within loop 2100C",
                    error="unexpected_dmg",
                )
            target_2100c.dmg = segment
            continue

        if isinstance(segment, REFSegment):
            _append_271_ref(
                ref_segment=segment,
                current_2000a=current_2000a,
                current_2000b=current_2000b,
                current_2000c=current_2000c,
                current_2110c=current_2110c,
                token=token,
                element_separator=element_separator,
            )
            continue

        if isinstance(segment, EBSegment):
            if current_2000c is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="EB must appear within loop 2000C",
                    error="unexpected_eb",
                )
            if current_2110c is None:
                current_2110c = _Loop2110C271State()
                current_2000c.loop_2110c.append(current_2110c)
            current_2110c.eb_segments.append(segment)
            continue

        if isinstance(segment, DTPSegment):
            if current_2110c is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="DTP must follow an EB segment within loop 2110C",
                    error="unexpected_dtp",
                )
            current_2110c.dtp_segments.append(segment)
            continue

        if isinstance(segment, LSSegment):
            if current_2110c is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="LS must appear within loop 2110C",
                    error="unexpected_ls",
                )
            current_2110c.ls_segment = segment
            continue

        if isinstance(segment, LESegment):
            if current_2110c is None:
                _raise_builder_error(
                    token,
                    element_separator=element_separator,
                    message="LE must appear within loop 2110C",
                    error="unexpected_le",
                )
            current_2110c.le_segment = segment
            continue

        _raise_builder_error(
            token,
            element_separator=element_separator,
            message=f"Segment {segment.segment_id} is not supported in a 271 hierarchy",
            error="unsupported_segment_in_transaction",
        )

    if root_2000a is None:
        missing_token = body[0][1] if body else SegmentToken("HL", (), 0)
        _raise_builder_error(
            missing_token,
            element_separator=element_separator,
            message="Transaction is missing the 2000A hierarchy",
            error="missing_hierarchy",
            suggestion="Start the body with HL*...*20",
        )

    try:
        return root_2000a.build()
    except ValueError as exc:
        failing_token = body[-1][1] if body else SegmentToken("HL", (), 0)
        _raise_builder_error(
            failing_token,
            element_separator=element_separator,
            message=str(exc),
            error="incomplete_loop",
            suggestion="Ensure each subscriber loop includes an NM1 subscriber segment",
        )


def _append_270_ref(
    *,
    ref_segment: REFSegment,
    current_2000a: _Loop2000A270State | None,
    current_2000b: _Loop2000B270State | None,
    current_2000c: _Loop2000C270State | None,
    current_2110c: _Loop2110C270State | None,
    token: SegmentToken,
    element_separator: str,
) -> None:
    if current_2110c is not None:
        current_2110c.ref_segments.append(ref_segment)
        return
    if current_2000c and current_2000c.loop_2100c is not None:
        current_2000c.loop_2100c.ref_segments.append(ref_segment)
        return
    if current_2000b and current_2000b.loop_2100b is not None:
        current_2000b.loop_2100b.ref_segments.append(ref_segment)
        return
    if current_2000a and current_2000a.loop_2100a is not None:
        current_2000a.loop_2100a.ref_segments.append(ref_segment)
        return
    _raise_builder_error(
        token,
        element_separator=element_separator,
        message="REF segment does not have an active parent loop",
        error="orphan_ref",
    )


def _append_271_aaa(
    *,
    aaa_segment: AAASegment,
    current_2000a: _Loop2000A271State | None,
    current_2000b: _Loop2000B271State | None,
    current_2000c: _Loop2000C271State | None,
    current_2110c: _Loop2110C271State | None,
    token: SegmentToken,
    element_separator: str,
) -> None:
    if current_2110c is not None:
        current_2110c.aaa_segments.append(aaa_segment)
        return
    if current_2000c and current_2000c.loop_2100c is not None:
        current_2000c.loop_2100c.aaa_segments.append(aaa_segment)
        return
    if current_2000c is not None:
        current_2000c.aaa_segments.append(aaa_segment)
        return
    if current_2000b is not None:
        current_2000b.aaa_segments.append(aaa_segment)
        return
    if current_2000a and current_2000a.loop_2100a is not None:
        current_2000a.loop_2100a.aaa_segments.append(aaa_segment)
        return
    if current_2000a is not None:
        current_2000a.aaa_segments.append(aaa_segment)
        return
    _raise_builder_error(
        token,
        element_separator=element_separator,
        message="AAA segment does not have an active parent loop",
        error="orphan_aaa",
    )


def _append_271_ref(
    *,
    ref_segment: REFSegment,
    current_2000a: _Loop2000A271State | None,
    current_2000b: _Loop2000B271State | None,
    current_2000c: _Loop2000C271State | None,
    current_2110c: _Loop2110C271State | None,
    token: SegmentToken,
    element_separator: str,
) -> None:
    if current_2110c is not None:
        current_2110c.ref_segments.append(ref_segment)
        return
    if current_2000c and current_2000c.loop_2100c is not None:
        current_2000c.loop_2100c.ref_segments.append(ref_segment)
        return
    if current_2000b and current_2000b.loop_2100b is not None:
        current_2000b.loop_2100b.ref_segments.append(ref_segment)
        return
    if current_2000a and current_2000a.loop_2100a is not None:
        current_2000a.loop_2100a.ref_segments.append(ref_segment)
        return
    _raise_builder_error(
        token,
        element_separator=element_separator,
        message="REF segment does not have an active parent loop",
        error="orphan_ref",
    )


def _expect_segment(
    pair: ParsedSegmentPair,
    expected_type: type[SegmentModelT],
    *,
    element_separator: str,
) -> SegmentModelT:
    segment, token = pair
    if not isinstance(segment, expected_type):
        _raise_builder_error(
            token,
            element_separator=element_separator,
            message=f"Expected {expected_type.segment_id} but found {token.segment_id}",
            error="unexpected_segment",
        )
    return segment


def _raise_builder_error(
    token: SegmentToken,
    *,
    element_separator: str,
    message: str,
    error: str,
    suggestion: str | None = None,
) -> NoReturn:
    raise ParserComponentError(
        message,
        error=error,
        segment_position=token.position,
        segment_id=token.segment_id,
        raw_segment=render_raw_segment(token, element_separator=element_separator),
        suggestion=suggestion,
    )
