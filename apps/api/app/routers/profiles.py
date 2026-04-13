"""Payer profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.profiles import ProfileDefaultsResponse, ProfilesResponse
from app.services.profiles import available_profiles, profile_defaults

router = APIRouter(tags=["profiles"])


@router.get("/profiles", response_model=ProfilesResponse)
async def list_profile_metadata() -> ProfilesResponse:
    """List all built-in payer profiles."""

    return ProfilesResponse(profiles=available_profiles())


@router.get("/profiles/{name}/defaults", response_model=ProfileDefaultsResponse)
async def get_profile_defaults(name: str) -> ProfileDefaultsResponse:
    """Return the default configuration values for a payer profile."""

    defaults = profile_defaults(name)
    return ProfileDefaultsResponse(
        payer_name=str(defaults["payer_name"]),
        payer_id=str(defaults["payer_id"]),
        interchange_receiver_id=str(defaults["interchange_receiver_id"]),
        receiver_id_qualifier=str(defaults["receiver_id_qualifier"]),
        default_service_type_code=str(defaults["default_service_type_code"]),
        max_batch_size=int(defaults["max_batch_size"]),
    )
