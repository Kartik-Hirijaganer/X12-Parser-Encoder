"""Shared request and response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, field_validator
from x12_edi_tools.config import SubmitterConfig

from app.schemas.base import ApiModel


def _npi_is_valid(value: str) -> bool:
    if len(value) != 10 or not value.isdigit():
        return False

    digits = [int(char) for char in f"80840{value}"][::-1]
    checksum = 0
    for index, digit in enumerate(digits):
        if index % 2 == 1:
            doubled = digit * 2
            checksum += (doubled // 10) + (doubled % 10)
        else:
            checksum += digit
    return checksum % 10 == 0


class ApiSubmitterConfig(ApiModel):
    """API-facing config model compatible with snake_case and camelCase payloads."""

    organization_name: str = Field(
        validation_alias=AliasChoices("organization_name", "organizationName")
    )
    provider_npi: str = Field(validation_alias=AliasChoices("provider_npi", "providerNpi"))
    provider_entity_type: str = Field(
        default="2",
        validation_alias=AliasChoices("provider_entity_type", "providerEntityType"),
    )
    trading_partner_id: str = Field(
        validation_alias=AliasChoices("trading_partner_id", "tradingPartnerId")
    )
    provider_taxonomy_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("provider_taxonomy_code", "providerTaxonomyCode"),
    )
    contact_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("contact_name", "contactName"),
    )
    contact_phone: str | None = Field(
        default=None,
        validation_alias=AliasChoices("contact_phone", "contactPhone"),
    )
    contact_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("contact_email", "contactEmail"),
    )
    payer_name: str = Field(validation_alias=AliasChoices("payer_name", "payerName"))
    payer_id: str = Field(validation_alias=AliasChoices("payer_id", "payerId"))
    interchange_receiver_id: str = Field(
        validation_alias=AliasChoices("interchange_receiver_id", "interchangeReceiverId")
    )
    receiver_id_qualifier: str = Field(
        default="ZZ",
        validation_alias=AliasChoices("receiver_id_qualifier", "receiverIdQualifier"),
    )
    sender_id_qualifier: str = Field(
        default="ZZ",
        validation_alias=AliasChoices("sender_id_qualifier", "senderIdQualifier"),
    )
    usage_indicator: str = Field(
        default="T",
        validation_alias=AliasChoices("usage_indicator", "usageIndicator"),
    )
    acknowledgment_requested: str = Field(
        default="0",
        validation_alias=AliasChoices(
            "acknowledgment_requested",
            "acknowledgmentRequested",
        ),
    )
    default_service_type_code: str = Field(
        default="30",
        validation_alias=AliasChoices("default_service_type_code", "defaultServiceTypeCode"),
    )
    default_service_date: str | None = Field(
        default=None,
        validation_alias=AliasChoices("default_service_date", "defaultServiceDate"),
    )
    max_batch_size: int = Field(
        default=5000,
        ge=1,
        validation_alias=AliasChoices("max_batch_size", "maxBatchSize"),
    )
    isa_control_number_start: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("isa_control_number_start", "isaControlNumberStart"),
    )
    gs_control_number_start: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("gs_control_number_start", "gsControlNumberStart"),
    )
    st_control_number_start: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("st_control_number_start", "stControlNumberStart"),
    )

    @field_validator("provider_npi")
    @classmethod
    def validate_provider_npi(cls, value: str) -> str:
        normalized = value.strip()
        if not _npi_is_valid(normalized):
            raise ValueError("provider_npi must be a valid 10-digit NPI (Luhn check failed)")
        return normalized

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
    def validate_acknowledgment_requested(cls, value: str) -> str:
        if value not in {"0", "1"}:
            raise ValueError("acknowledgment_requested must be '0' or '1'")
        return value

    @field_validator("default_service_date")
    @classmethod
    def normalize_default_service_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if len(normalized) != 8 or not normalized.isdigit():
            raise ValueError("default_service_date must be YYYYMMDD when provided")
        return normalized

    def to_library_model(self) -> SubmitterConfig:
        """Convert the API payload into the library config model."""

        return SubmitterConfig(**self.model_dump())


class Correction(ApiModel):
    row: int
    field: str
    original_value: str | None = None
    corrected_value: str | None = None
    message: str


class WarningMessage(ApiModel):
    row: int | None = None
    field: str | None = None
    message: str
    suggestion: str | None = None


class RowError(ApiModel):
    row: int
    field: str | None = None
    message: str
    suggestion: str | None = None


class PatientRecord(ApiModel):
    last_name: str
    first_name: str
    date_of_birth: str
    gender: str
    member_id: str | None = None
    ssn: str | None = None
    service_type_code: str
    service_date: str
    service_date_end: str | None = None


class ControlNumbers(ApiModel):
    isa13: str | None = None
    gs06: str | None = None
    st02_range: list[str] = Field(default_factory=list)


class ArchiveEntry(ApiModel):
    file_name: str
    record_range_start: int
    record_range_end: int
    control_numbers: ControlNumbers


class ValidationIssue(ApiModel):
    severity: str
    level: str
    code: str
    message: str
    location: str | None = None
    segment_id: str | None = None
    element: str | None = None
    suggestion: str | None = None
    profile: str | None = None
    transaction_index: int | None = None
    transaction_control_number: str | None = None


class ProfileInfo(ApiModel):
    name: str
    display_name: str
    description: str


class EligibilitySegment(ApiModel):
    eligibility_code: str
    service_type_code: str | None = None
    service_type_codes: list[str] = Field(default_factory=list)
    coverage_level_code: str | None = None
    insurance_type_code: str | None = None
    plan_coverage_description: str | None = None
    monetary_amount: str | None = None
    quantity: str | None = None
    in_plan_network_indicator: str | None = None


class BenefitEntity(ApiModel):
    loop_identifier: str | None = None
    qualifier: str | None = None
    identifier: str | None = None
    description: str | None = None
    entity_identifier_code: str | None = None
    name: str | None = None
    contacts: list[str] = Field(default_factory=list)


class AAAError(ApiModel):
    code: str
    message: str
    follow_up_action_code: str | None = None
    suggestion: str | None = None


class EligibilitySummary(ApiModel):
    total: int
    active: int
    inactive: int
    error: int
    not_found: int = 0
    unknown: int


class EligibilityResult(ApiModel):
    member_name: str
    member_id: str | None = None
    overall_status: str
    status_reason: str | None = None
    st_control_number: str | None = None
    trace_number: str | None = None
    eligibility_segments: list[EligibilitySegment] = Field(default_factory=list)
    benefit_entities: list[BenefitEntity] = Field(default_factory=list)
    aaa_errors: list[AAAError] = Field(default_factory=list)


JsonObject = dict[str, Any]
