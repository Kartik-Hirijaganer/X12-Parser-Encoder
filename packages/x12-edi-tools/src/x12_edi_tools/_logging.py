"""Shared logging helpers for PHI-safe library observability."""

from __future__ import annotations

import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    """Return a standard library logger without configuring handlers."""

    return logging.getLogger(name)


def build_log_extra(
    *,
    correlation_id: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Build a compact ``extra`` payload that omits unset values."""

    payload = {key: value for key, value in fields.items() if value is not None}
    if correlation_id is not None:
        payload["correlation_id"] = correlation_id
    return payload
