"""Payer profile exports and built-in registry."""

from __future__ import annotations

from x12_edi_tools.exceptions import X12ValidationError
from x12_edi_tools.payers.base import PayerProfile
from x12_edi_tools.payers.dc_medicaid import DCMedicaidProfile

_REGISTERED_PROFILES: dict[str, PayerProfile] = {
    "dc_medicaid": DCMedicaidProfile(),
}


def get_profile(profile: str) -> PayerProfile:
    """Resolve a built-in payer profile by name."""

    normalized = profile.strip().lower()
    try:
        return _REGISTERED_PROFILES[normalized]
    except KeyError as exc:
        raise X12ValidationError(f"Unknown payer profile '{profile}'") from exc


def list_profiles() -> list[str]:
    """Return the registered built-in payer profile names."""

    return sorted(_REGISTERED_PROFILES)


__all__ = [
    "DCMedicaidProfile",
    "PayerProfile",
    "get_profile",
    "list_profiles",
]
