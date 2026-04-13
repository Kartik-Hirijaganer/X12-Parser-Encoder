"""Validator public exports."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from x12_edi_tools.validator.base import (
    SnipLevel,
    ValidationError,
    ValidationResult,
    ValidationRule,
)

if TYPE_CHECKING:
    from x12_edi_tools.models.transactions import Interchange
    from x12_edi_tools.payers.base import PayerProfile


def validate(
    interchange: Interchange,
    *,
    levels: Iterable[int | str | SnipLevel] | None = None,
    profile: str | PayerProfile | None = None,
    custom_rules: Sequence[ValidationRule] | None = None,
    correlation_id: str | None = None,
) -> ValidationResult:
    """Lazy public wrapper to avoid validator/payer import cycles."""

    from x12_edi_tools.validator.x12_validator import validate as _validate

    return _validate(
        interchange,
        levels=levels,
        profile=profile,
        custom_rules=custom_rules,
        correlation_id=correlation_id,
    )


__all__ = [
    "SnipLevel",
    "ValidationError",
    "ValidationResult",
    "ValidationRule",
    "validate",
]
