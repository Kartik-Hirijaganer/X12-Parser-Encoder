"""Shared validation result types and helpers."""

from __future__ import annotations

from calendar import monthrange
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum, StrEnum
from typing import Any, Literal, Protocol

from x12_edi_tools.exceptions import X12ValidationError
from x12_edi_tools.models.base import X12Segment
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

Severity = Literal["error", "warning", "info"]
TransactionModel = Transaction270 | Transaction271


class SnipLevel(StrEnum):
    """Supported generic SNIP validation levels."""

    SNIP1 = "snip1"
    SNIP2 = "snip2"
    SNIP3 = "snip3"
    SNIP4 = "snip4"
    SNIP5 = "snip5"

    @classmethod
    def from_value(cls, value: int | str | SnipLevel) -> SnipLevel:
        """Normalize integers and strings into a ``SnipLevel`` enum."""

        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            mapping = {
                1: cls.SNIP1,
                2: cls.SNIP2,
                3: cls.SNIP3,
                4: cls.SNIP4,
                5: cls.SNIP5,
            }
            try:
                return mapping[value]
            except KeyError as exc:
                raise ValueError(f"Unsupported SNIP level integer: {value}") from exc

        normalized = value.strip().lower()
        if normalized.isdigit():
            return cls.from_value(int(normalized))

        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"Unsupported SNIP level value: {value}") from exc


@dataclass(slots=True)
class ValidationError:
    """One normalized validation issue."""

    severity: Severity
    level: SnipLevel | str
    code: str
    message: str
    location: str | None = None
    segment_id: str | None = None
    element: str | None = None
    suggestion: str | None = None
    profile: str | None = None


@dataclass(slots=True)
class ValidationResult:
    """Aggregate validation result returned by ``validate()``."""

    issues: list[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "info")

    @property
    def errors(self) -> list[ValidationError]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationError]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def infos(self) -> list[ValidationError]:
        return [issue for issue in self.issues if issue.severity == "info"]

    def human_readable_summary(self) -> str:
        """Render a compact plain-English summary of the issues."""

        if not self.issues:
            return "Validation passed with no issues."

        status = "passed" if self.is_valid else "failed"
        lines = [
            (
                f"Validation {status}: {self.error_count} error(s), "
                f"{self.warning_count} warning(s), {self.info_count} info item(s)."
            )
        ]
        for issue in self.issues:
            parts = [f"[{issue.severity.upper()}] {issue.message}"]
            if issue.location:
                parts.append(f"Location: {issue.location}.")
            if issue.suggestion:
                parts.append(f"Fix: {issue.suggestion}")
            lines.append(" ".join(parts))
        return "\n".join(lines)

    def to_dataframe(self) -> object:
        """Return a pandas DataFrame when the optional pandas extra is installed."""

        try:
            import pandas as pd  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            raise X12ValidationError(
                "ValidationResult.to_dataframe() requires the optional pandas extra"
            ) from exc

        return pd.DataFrame([asdict(issue) for issue in self.issues])


class ValidationRule(Protocol):
    """Callable shape accepted by ``validate(..., custom_rules=...)``."""

    def __call__(self, interchange: Interchange) -> Sequence[ValidationError]:
        """Return zero or more validation issues."""


@dataclass(frozen=True, slots=True)
class TransactionContext:
    """Transaction location metadata used by validators."""

    functional_group_index: int
    transaction_index: int
    transaction: TransactionModel


def issue(
    *,
    severity: Severity = "error",
    level: SnipLevel | str,
    code: str,
    message: str,
    location: str | None = None,
    segment_id: str | None = None,
    element: str | None = None,
    suggestion: str | None = None,
    profile: str | None = None,
) -> ValidationError:
    """Build a normalized validation issue."""

    return ValidationError(
        severity=severity,
        level=level,
        code=code,
        message=message,
        location=location,
        segment_id=segment_id,
        element=element,
        suggestion=suggestion,
        profile=profile,
    )


def iter_transactions(interchange: Interchange) -> Iterator[TransactionContext]:
    """Yield every transaction with stable group/transaction indexes."""

    for group_index, group in enumerate(as_list(getattr(interchange, "functional_groups", []))):
        if not isinstance(group, FunctionalGroup):
            continue
        for transaction_index, transaction in enumerate(as_list(group.transactions)):
            if isinstance(transaction, Transaction270 | Transaction271):
                yield TransactionContext(
                    functional_group_index=group_index,
                    transaction_index=transaction_index,
                    transaction=transaction,
                )


def count_transaction_segments(transaction: TransactionModel) -> int:
    """Count transaction segments inclusively for SE01 balancing."""

    body_count = sum(1 for _ in iter_transaction_body_segments(transaction))
    generic_count = len(as_list(getattr(transaction, "generic_segments", [])))
    return body_count + generic_count + 3


def iter_transaction_body_segments(transaction: TransactionModel) -> Iterator[X12Segment]:
    """Yield typed body segments excluding ST/BHT/SE."""

    if isinstance(transaction, Transaction270):
        loop_2000a = getattr(transaction, "loop_2000a", None)
        if isinstance(loop_2000a, Loop2000A_270):
            yield from _iter_loop_2000a_270(loop_2000a)
        return

    loop_2000a = getattr(transaction, "loop_2000a", None)
    if isinstance(loop_2000a, Loop2000A_271):
        yield from _iter_loop_2000a_271(loop_2000a)


def as_list(value: object) -> list[Any]:
    """Return a list for sequence-like values, or an empty list otherwise."""

    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def normalize_str(value: object) -> str | None:
    """Return a string representation suitable for code-set checks."""

    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def parse_date_yyyymmdd(value: str) -> date | None:
    """Parse ``YYYYMMDD`` dates, returning ``None`` for invalid inputs."""

    if len(value) != 8 or not value.isdigit():
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def parse_date_yymmdd(value: str) -> date | None:
    """Parse ``YYMMDD`` dates, returning ``None`` for invalid inputs."""

    if len(value) != 6 or not value.isdigit():
        return None
    try:
        return datetime.strptime(value, "%y%m%d").date()
    except ValueError:
        return None


def subtract_months(anchor: date, months: int) -> date:
    """Return ``anchor`` shifted backwards by ``months`` calendar months."""

    year_month = anchor.year * 12 + (anchor.month - 1) - months
    year = year_month // 12
    month = year_month % 12 + 1
    day = min(anchor.day, monthrange(year, month)[1])
    return date(year=year, month=month, day=day)


def _iter_loop_2000a_270(loop: Loop2000A_270) -> Iterator[X12Segment]:
    yield loop.hl
    if isinstance(loop.loop_2100a, Loop2100A_270):
        yield from _iter_loop_2100a_270(loop.loop_2100a)
    for child_loop in as_list(loop.loop_2000b):
        if isinstance(child_loop, Loop2000B_270):
            yield from _iter_loop_2000b_270(child_loop)


def _iter_loop_2100a_270(loop: Loop2100A_270) -> Iterator[X12Segment]:
    yield loop.nm1
    for ref_segment in as_list(loop.ref_segments):
        if isinstance(ref_segment, X12Segment):
            yield ref_segment


def _iter_loop_2000b_270(loop: Loop2000B_270) -> Iterator[X12Segment]:
    yield loop.hl
    if isinstance(loop.loop_2100b, Loop2100B_270):
        yield from _iter_loop_2100b_270(loop.loop_2100b)
    for child_loop in as_list(loop.loop_2000c):
        if isinstance(child_loop, Loop2000C_270):
            yield from _iter_loop_2000c_270(child_loop)


def _iter_loop_2100b_270(loop: Loop2100B_270) -> Iterator[X12Segment]:
    yield loop.nm1
    for maybe_segment in (loop.prv, loop.per, loop.n3, loop.n4):
        if isinstance(maybe_segment, X12Segment):
            yield maybe_segment
    for ref_segment in as_list(loop.ref_segments):
        if isinstance(ref_segment, X12Segment):
            yield ref_segment


def _iter_loop_2000c_270(loop: Loop2000C_270) -> Iterator[X12Segment]:
    yield loop.hl
    if isinstance(loop.trn, X12Segment):
        yield loop.trn
    yield from _iter_loop_2100c_270(loop.loop_2100c)
    for child_loop in as_list(loop.loop_2110c):
        if isinstance(child_loop, Loop2110C_270):
            yield from _iter_loop_2110c_270(child_loop)


def _iter_loop_2100c_270(loop: Loop2100C_270) -> Iterator[X12Segment]:
    yield loop.nm1
    if isinstance(loop.dmg, X12Segment):
        yield loop.dmg
    for ref_segment in as_list(loop.ref_segments):
        if isinstance(ref_segment, X12Segment):
            yield ref_segment


def _iter_loop_2110c_270(loop: Loop2110C_270) -> Iterator[X12Segment]:
    for collection in (loop.eq_segments, loop.dtp_segments, loop.ref_segments):
        for segment in as_list(collection):
            if isinstance(segment, X12Segment):
                yield segment


def _iter_loop_2000a_271(loop: Loop2000A_271) -> Iterator[X12Segment]:
    yield loop.hl
    for aaa_segment in as_list(loop.aaa_segments):
        if isinstance(aaa_segment, X12Segment):
            yield aaa_segment
    if isinstance(loop.loop_2100a, Loop2100A_271):
        yield from _iter_loop_2100a_271(loop.loop_2100a)
    for child_loop in as_list(loop.loop_2000b):
        if isinstance(child_loop, Loop2000B_271):
            yield from _iter_loop_2000b_271(child_loop)


def _iter_loop_2100a_271(loop: Loop2100A_271) -> Iterator[X12Segment]:
    yield loop.nm1
    for collection in (loop.aaa_segments, loop.ref_segments):
        for segment in as_list(collection):
            if isinstance(segment, X12Segment):
                yield segment


def _iter_loop_2000b_271(loop: Loop2000B_271) -> Iterator[X12Segment]:
    yield loop.hl
    for aaa_segment in as_list(loop.aaa_segments):
        if isinstance(aaa_segment, X12Segment):
            yield aaa_segment
    if isinstance(loop.loop_2100b, Loop2100B_271):
        yield from _iter_loop_2100b_271(loop.loop_2100b)
    for child_loop in as_list(loop.loop_2000c):
        if isinstance(child_loop, Loop2000C_271):
            yield from _iter_loop_2000c_271(child_loop)


def _iter_loop_2100b_271(loop: Loop2100B_271) -> Iterator[X12Segment]:
    yield loop.nm1
    for maybe_segment in (loop.per, loop.n3, loop.n4):
        if isinstance(maybe_segment, X12Segment):
            yield maybe_segment
    for ref_segment in as_list(loop.ref_segments):
        if isinstance(ref_segment, X12Segment):
            yield ref_segment


def _iter_loop_2000c_271(loop: Loop2000C_271) -> Iterator[X12Segment]:
    yield loop.hl
    if isinstance(loop.trn, X12Segment):
        yield loop.trn
    for aaa_segment in as_list(loop.aaa_segments):
        if isinstance(aaa_segment, X12Segment):
            yield aaa_segment
    yield from _iter_loop_2100c_271(loop.loop_2100c)
    for child_loop in as_list(loop.loop_2110c):
        if isinstance(child_loop, Loop2110C_271):
            yield from _iter_loop_2110c_271(child_loop)


def _iter_loop_2100c_271(loop: Loop2100C_271) -> Iterator[X12Segment]:
    yield loop.nm1
    for maybe_segment in (loop.dmg, loop.n3, loop.n4):
        if isinstance(maybe_segment, X12Segment):
            yield maybe_segment
    for collection in (loop.aaa_segments, loop.ref_segments):
        for segment in as_list(collection):
            if isinstance(segment, X12Segment):
                yield segment


def _iter_loop_2110c_271(loop: Loop2110C_271) -> Iterator[X12Segment]:
    for eb_segment in as_list(loop.eb_segments):
        if isinstance(eb_segment, X12Segment):
            yield eb_segment
    for aaa_segment in as_list(loop.aaa_segments):
        if isinstance(aaa_segment, X12Segment):
            yield aaa_segment
    for maybe_segment in (loop.ls_segment, loop.le_segment):
        if isinstance(maybe_segment, X12Segment):
            yield maybe_segment
    for ref_segment in as_list(loop.ref_segments):
        if isinstance(ref_segment, X12Segment):
            yield ref_segment
    for dtp_segment in as_list(loop.dtp_segments):
        if isinstance(dtp_segment, X12Segment):
            yield dtp_segment
