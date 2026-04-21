"""Payer profile protocol definitions.

Extended in Phase 0 of the 837I/837P/835 plan to carry SNIP 7 metadata, a
``build_validation_context`` factory hook, and per-transaction overrides. The
revised ``validate`` signature accepts an optional ``ValidationContext`` so
existing call sites keep compiling; Phase 4 wires the executor that requires it.
See plan \u00a72.5 and \u00a72.11.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from x12_edi_tools.models.transactions import Interchange
from x12_edi_tools.validator.context import (
    MemberRegistryLookup,
    ProviderRegistryLookup,
    ValidationContext,
)

if TYPE_CHECKING:
    from x12_edi_tools.validator.base import ValidationError


class PayerProfile(Protocol):
    """Protocol for payer-specific defaults, validation, and SNIP 7 wiring."""

    name: str
    snip7_enabled: bool

    def get_defaults(self) -> dict[str, object]:
        """Return payer defaults suitable for UI/config auto-fill."""

    def validate(
        self,
        interchange: Interchange,
        *,
        context: ValidationContext | None = None,
    ) -> Sequence[ValidationError]:
        """Return payer-specific validation issues.

        ``context`` is keyword-only and defaults to ``None`` so existing call sites
        remain valid during the Phase 0 \u2192 Phase 4 transition. Phase 4 promotes the
        argument to required at the orchestration layer.
        """

    def build_validation_context(
        self,
        *,
        provider_lookup: ProviderRegistryLookup | None = None,
        member_lookup: MemberRegistryLookup | None = None,
        correlation_id: str | None = None,
    ) -> ValidationContext:
        """Compose a ``ValidationContext`` for this payer's SNIP 7 executor.

        DC Medicaid (CG \u00a73.2) raises ``PayerConfigurationError`` when either lookup
        is ``None``. Other payers may return a partial context and let SNIP 7 skip
        with warnings.
        """

    def get_claim_defaults(self, transaction: str) -> dict[str, object]:
        """Return per-transaction packaging defaults (frequency, TOB, POS, signature)."""

    def get_remit_overrides(self) -> dict[str, object]:
        """Return payer-specific CARC/RARC mappings, PLB handling hints, etc."""
