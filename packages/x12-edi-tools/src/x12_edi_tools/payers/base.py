"""Payer profile protocol definitions."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from x12_edi_tools.models.transactions import Interchange

if TYPE_CHECKING:
    from x12_edi_tools.validator.base import ValidationError


class PayerProfile(Protocol):
    """Thin protocol for payer-specific validation and defaults."""

    name: str

    def validate(self, interchange: Interchange) -> Sequence[ValidationError]:
        """Return payer-specific validation issues."""

    def get_defaults(self) -> dict[str, object]:
        """Return payer defaults suitable for UI/config auto-fill."""
