"""Top-level X12 parser orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from x12_edi_tools._logging import build_log_extra, get_logger
from x12_edi_tools.common.types import SegmentToken
from x12_edi_tools.exceptions import TransactionParseError, X12ParseError
from x12_edi_tools.models.base import GenericSegment
from x12_edi_tools.models.segments import GESegment, GSSegment, IEASegment
from x12_edi_tools.models.transactions import FunctionalGroup, Interchange
from x12_edi_tools.models.transactions.transaction_270 import Transaction270
from x12_edi_tools.models.transactions.transaction_271 import Transaction271
from x12_edi_tools.parser._exceptions import ParserComponentError
from x12_edi_tools.parser.isa_parser import parse_isa_segment
from x12_edi_tools.parser.loop_builder import build_transaction
from x12_edi_tools.parser.segment_parser import (
    ParsedSegment,
    parse_segment,
    render_raw_segment,
)
from x12_edi_tools.parser.tokenizer import tokenize

OnErrorMode = Literal["raise", "skip", "collect"]
logger = get_logger(__name__)


@dataclass(slots=True)
class ParseResult:
    """Public parse contract returned by ``parse()``."""

    interchange: Interchange
    errors: list[TransactionParseError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse(
    raw: str,
    *,
    strict: bool = True,
    on_error: OnErrorMode = "raise",
    correlation_id: str | None = None,
) -> ParseResult:
    """Parse a raw X12 interchange into typed models."""

    if on_error not in {"raise", "skip", "collect"}:
        raise ValueError("on_error must be one of: 'raise', 'skip', 'collect'")

    logger.info(
        "x12_parse_started",
        extra=build_log_extra(
            correlation_id=correlation_id,
            strict=strict,
            on_error=on_error,
            payload_characters=len(raw),
        ),
    )

    isa, delimiters, next_position = parse_isa_segment(raw)
    tokens = tokenize(raw[next_position:], delimiters, start_position=next_position)
    groups: list[FunctionalGroup] = []
    warnings: list[str] = []
    errors: list[TransactionParseError] = []
    group_cursor = 0
    transaction_index = 0

    while group_cursor < len(tokens) and tokens[group_cursor].segment_id != "IEA":
        gs_token = tokens[group_cursor]
        gs_segment = parse_segment(
            gs_token,
            strict=True,
            element_separator=delimiters.element,
            repetition_separator=delimiters.repetition,
        )
        if not isinstance(gs_segment, GSSegment):
            raise X12ParseError(f"Expected GS at position {gs_token.position}")
        group_cursor += 1

        transactions = []
        while group_cursor < len(tokens) and tokens[group_cursor].segment_id != "GE":
            transaction_tokens, group_cursor, collector_error = _collect_transaction_tokens(
                tokens,
                start_index=group_cursor,
                element_separator=delimiters.element,
            )
            st_control_number = _extract_st_control_number(transaction_tokens)

            if collector_error is not None:
                if on_error == "raise":
                    raise collector_error
                if on_error == "collect":
                    errors.append(
                        collector_error.to_transaction_error(
                            transaction_index=transaction_index,
                            st_control_number=st_control_number,
                        )
                    )
                transaction_index += 1
                continue

            try:
                transaction, transaction_warnings = _parse_transaction_tokens(
                    transaction_tokens,
                    strict=strict,
                    element_separator=delimiters.element,
                    repetition_separator=delimiters.repetition,
                    transaction_index=transaction_index,
                )
            except ParserComponentError as exc:
                if on_error == "raise":
                    raise
                if on_error == "collect":
                    errors.append(
                        exc.to_transaction_error(
                            transaction_index=transaction_index,
                            st_control_number=st_control_number,
                        )
                    )
                transaction_index += 1
                continue

            transactions.append(transaction)
            warnings.extend(transaction_warnings)
            transaction_index += 1

        if group_cursor >= len(tokens):
            raise X12ParseError("Interchange ended before a GE trailer was found")

        ge_token = tokens[group_cursor]
        ge_segment = parse_segment(
            ge_token,
            strict=True,
            element_separator=delimiters.element,
            repetition_separator=delimiters.repetition,
        )
        if not isinstance(ge_segment, GESegment):
            raise X12ParseError(f"Expected GE at position {ge_token.position}")

        groups.append(FunctionalGroup(gs=gs_segment, transactions=transactions, ge=ge_segment))
        group_cursor += 1

    if not groups:
        raise X12ParseError("Interchange does not contain a functional group")

    iea_token = tokens[group_cursor] if group_cursor < len(tokens) else None
    if iea_token is None or iea_token.segment_id != "IEA":
        raise X12ParseError("Interchange is missing the IEA trailer")
    iea_segment = parse_segment(
        iea_token,
        strict=True,
        element_separator=delimiters.element,
        repetition_separator=delimiters.repetition,
    )
    if not isinstance(iea_segment, IEASegment):
        raise X12ParseError(f"Expected IEA at position {iea_token.position}")
    if group_cursor != len(tokens) - 1:
        raise X12ParseError("Unexpected segments found after the IEA trailer")

    interchange = Interchange(
        isa=isa,
        functional_groups=groups,
        iea=iea_segment,
        delimiters=delimiters,
    )
    result = ParseResult(interchange=interchange, errors=errors, warnings=warnings)
    logger.info(
        "x12_parse_completed",
        extra=build_log_extra(
            correlation_id=correlation_id,
            functional_group_count=len(groups),
            transaction_count=sum(len(group.transactions) for group in groups),
            parser_warning_count=len(warnings),
            parser_error_count=len(errors),
            segment_count=len(tokens) + 2,
        ),
    )
    return result


def _collect_transaction_tokens(
    tokens: list[SegmentToken],
    *,
    start_index: int,
    element_separator: str,
) -> tuple[list[SegmentToken], int, ParserComponentError | None]:
    """Collect tokens spanning one transaction for transaction-scoped recovery."""

    if start_index >= len(tokens):
        raise X12ParseError("Unexpected end of token stream while reading transactions")

    start_token = tokens[start_index]
    if start_token.segment_id != "ST":
        raise X12ParseError(
            f"Expected ST to open a transaction at position {start_token.position}, "
            f"found {start_token.segment_id}"
        )

    cursor = start_index + 1
    while cursor < len(tokens):
        if tokens[cursor].segment_id == "SE":
            return tokens[start_index : cursor + 1], cursor + 1, None
        if tokens[cursor].segment_id in {"ST", "GE", "IEA"}:
            return (
                tokens[start_index:cursor],
                cursor,
                ParserComponentError(
                    "Transaction did not close with an SE segment",
                    error="missing_se",
                    segment_position=start_token.position,
                    segment_id=start_token.segment_id,
                    raw_segment=render_raw_segment(
                        start_token,
                        element_separator=element_separator,
                    ),
                    suggestion="Ensure each ST segment is matched by an SE trailer",
                ),
            )
        cursor += 1

    return (
        tokens[start_index:cursor],
        cursor,
        ParserComponentError(
            "Transaction reached end of file before an SE segment was found",
            error="missing_se",
            segment_position=start_token.position,
            segment_id=start_token.segment_id,
            raw_segment=render_raw_segment(
                start_token,
                element_separator=element_separator,
            ),
            suggestion="Ensure each ST segment is matched by an SE trailer",
        ),
    )


def _parse_transaction_tokens(
    tokens: list[SegmentToken],
    *,
    strict: bool,
    element_separator: str,
    repetition_separator: str,
    transaction_index: int,
) -> tuple[Transaction270 | Transaction271, list[str]]:
    """Parse tokens for a single transaction into a typed transaction model."""

    segment_pairs: list[tuple[ParsedSegment, SegmentToken]] = []
    warnings: list[str] = []

    for token in tokens:
        segment = parse_segment(
            token,
            strict=strict,
            element_separator=element_separator,
            repetition_separator=repetition_separator,
        )
        if isinstance(segment, GenericSegment):
            warnings.append(
                f"Transaction {transaction_index}: preserved unsupported segment "
                f"{token.segment_id} at position {token.position}"
            )
        segment_pairs.append((segment, token))

    transaction = build_transaction(segment_pairs, element_separator=element_separator)
    return transaction, warnings


def _extract_st_control_number(tokens: list[SegmentToken]) -> str | None:
    """Return the ST02 control number when a transaction token list has one."""

    if not tokens:
        return None
    st_token = tokens[0]
    if st_token.segment_id != "ST" or len(st_token.elements) < 2:
        return None
    return st_token.elements[1]
