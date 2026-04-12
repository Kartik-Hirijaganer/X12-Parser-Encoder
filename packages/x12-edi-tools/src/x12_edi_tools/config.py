"""Configuration models shared by the library and applications."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubmitterConfig(BaseModel):
    """Provider, payer, envelope, and transaction defaults for 270 generation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    organization_name: str = Field(min_length=1)
    provider_npi: str = Field(min_length=10, max_length=10)
    provider_entity_type: str = "2"
    trading_partner_id: str = Field(min_length=1, max_length=15)
    provider_taxonomy_code: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None

    payer_name: str = Field(min_length=1)
    payer_id: str = Field(min_length=1)
    interchange_receiver_id: str = Field(min_length=1, max_length=15)
    receiver_id_qualifier: str = Field(default="ZZ", min_length=2, max_length=2)

    sender_id_qualifier: str = Field(default="ZZ", min_length=2, max_length=2)
    usage_indicator: str = Field(default="T", min_length=1, max_length=1)
    acknowledgment_requested: str = Field(default="0", min_length=1, max_length=1)

    default_service_type_code: str = Field(default="30", min_length=1)
    default_service_date: str | None = None
    max_batch_size: int = Field(default=5000, ge=1)

    isa_control_number_start: int | None = Field(default=None, ge=1)
    gs_control_number_start: int | None = Field(default=None, ge=1)
    st_control_number_start: int | None = Field(default=None, ge=1)

    @field_validator("provider_npi")
    @classmethod
    def validate_provider_npi(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("provider_npi must contain only digits")
        return value

    @field_validator("provider_entity_type")
    @classmethod
    def validate_provider_entity_type(cls, value: str) -> str:
        if value not in {"1", "2"}:
            raise ValueError("provider_entity_type must be '1' or '2'")
        return value

    @field_validator("usage_indicator")
    @classmethod
    def validate_usage_indicator(cls, value: str) -> str:
        if value not in {"T", "P"}:
            raise ValueError("usage_indicator must be 'T' or 'P'")
        return value

    @field_validator("acknowledgment_requested")
    @classmethod
    def validate_ack_requested(cls, value: str) -> str:
        if value not in {"0", "1"}:
            raise ValueError("acknowledgment_requested must be '0' or '1'")
        return value
