"""Shared exception types for the X12 library."""

from __future__ import annotations

from dataclasses import dataclass


class X12Error(Exception):
    """Base exception for library errors."""


class ConfigurationError(X12Error):
    """Raised when submitter or runtime configuration is invalid."""


class X12ParseError(X12Error):
    """Raised when raw X12 content cannot be parsed into typed models."""


class X12EncodeError(X12Error):
    """Raised when typed X12 models cannot be encoded to raw text."""


class X12ValidationError(X12Error):
    """Raised when a typed X12 model fails semantic validation."""


@dataclass(slots=True)
class TransactionParseError:
    """Transaction-scoped parse failure used by ``on_error='collect'`` paths."""

    transaction_index: int
    st_control_number: str | None
    segment_position: int
    segment_id: str | None
    raw_segment: str
    error: str
    message: str
    suggestion: str | None = None
