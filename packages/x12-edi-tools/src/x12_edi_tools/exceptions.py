"""Shared exception types for the X12 library."""


class X12Error(Exception):
    """Base exception for library errors."""


class ConfigurationError(X12Error):
    """Raised when submitter or runtime configuration is invalid."""
