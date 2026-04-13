"""Internal parser exceptions with transaction-scoped metadata."""

from __future__ import annotations

from x12_edi_tools.exceptions import TransactionParseError, X12ParseError


class ParserComponentError(X12ParseError):
    """Parse failure carrying segment-level metadata for recovery modes."""

    def __init__(
        self,
        message: str,
        *,
        error: str,
        segment_position: int,
        segment_id: str | None,
        raw_segment: str,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error = error
        self.segment_position = segment_position
        self.segment_id = segment_id
        self.raw_segment = raw_segment
        self.suggestion = suggestion

    def to_transaction_error(
        self,
        *,
        transaction_index: int,
        st_control_number: str | None,
    ) -> TransactionParseError:
        """Convert the failure into the public transaction error shape."""

        return TransactionParseError(
            transaction_index=transaction_index,
            st_control_number=st_control_number,
            segment_position=self.segment_position,
            segment_id=self.segment_id,
            raw_segment=self.raw_segment,
            error=self.error,
            message=str(self),
            suggestion=self.suggestion,
        )
