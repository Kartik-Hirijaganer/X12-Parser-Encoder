"""Payer profile helpers."""

from __future__ import annotations

from typing import cast

from fastapi import HTTPException, status
from x12_edi_tools.payers import get_profile, list_profiles

from app.schemas.common import ProfileInfo


def available_profiles() -> list[ProfileInfo]:
    """Return available built-in payer profiles."""

    profiles: list[ProfileInfo] = []
    for name in list_profiles():
        profile = get_profile(name)
        defaults = profile.get_defaults()
        display_name = str(defaults.get("payer_name", name.replace("_", " ").title()))
        profiles.append(
            ProfileInfo(
                name=name,
                display_name=display_name.title(),
                description=f"{display_name.title()} eligibility profile.",
            )
        )
    return profiles


def profile_defaults(name: str) -> dict[str, str | int]:
    """Return defaults for one built-in payer profile."""

    try:
        defaults = get_profile(name).get_defaults()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Unknown payer profile '{name}'."},
        ) from exc
    return {
        "payer_name": str(defaults["payer_name"]),
        "payer_id": str(defaults["payer_id"]),
        "interchange_receiver_id": str(defaults["interchange_receiver_id"]),
        "receiver_id_qualifier": str(defaults["receiver_id_qualifier"]),
        "default_service_type_code": str(defaults["default_service_type_code"]),
        "max_batch_size": int(cast(int | str, defaults["max_batch_size"])),
    }
