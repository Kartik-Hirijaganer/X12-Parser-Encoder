"""Validation context contracts shared across SNIP levels and payer profiles.

Phase 0 scaffolds the dataclass and the two registry-lookup ``Protocol`` types so
every downstream phase can code against a stable shape. Phase 4 adds the SNIP 7
executor that consumes the context; Phase 5 implements DC Medicaid's
``build_validation_context`` override that promotes missing lookups to errors
(CG \u00a73.2). See \u00a72.11 of the 837I/837P/835 implementation plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProviderRegistryLookup(Protocol):
    """Caller-supplied callable that resolves whether an NPI is enrolled with the payer."""

    def __call__(self, npi: str, taxonomy: str | None = None) -> bool: ...


@runtime_checkable
class MemberRegistryLookup(Protocol):
    """Caller-supplied callable that resolves whether a member is on file with the payer."""

    def __call__(self, member_id: str, birth_date: str | None = None) -> bool: ...


@dataclass(frozen=True, slots=True)
class ValidationContext:
    """Injected dependencies for optional validation levels (currently SNIP 7).

    Every field is ``Optional``. A level that needs a dependency is skipped (with a
    ``warning`` ``ValidationError`` carrying code ``X12-SNIP7-SKIPPED-NO-LOOKUP``) if the
    dependency is absent. Payer profiles may promote that warning to an error via their
    ``build_validation_context(raise_on_missing=True)`` override (DC Medicaid does this).
    """

    provider_lookup: ProviderRegistryLookup | None = None
    member_lookup: MemberRegistryLookup | None = None
    correlation_id: str | None = None
