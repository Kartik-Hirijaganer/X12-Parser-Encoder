"""Schemas for profile endpoints."""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.common import ProfileInfo


class ProfilesResponse(ApiModel):
    profiles: list[ProfileInfo] = Field(default_factory=list)


class ProfileDefaultsResponse(ApiModel):
    payer_name: str
    payer_id: str
    interchange_receiver_id: str
    receiver_id_qualifier: str
    default_service_type_code: str
    max_batch_size: int
