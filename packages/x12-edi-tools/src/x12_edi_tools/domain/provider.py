"""Provider domain objects for 837 claim submission.

Covers the billing, rendering, attending, referring, supervising, and service
facility roles. All NPIs are validated against the standard Luhn checksum
(ISO 7812) used by CMS; state codes are uppercased for consistency with the
X12 code set.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProviderRole(StrEnum):
    """NM101 entity-identifier codes for provider roles used by 837 flows."""

    BILLING = "85"
    PAY_TO = "87"
    RENDERING = "82"
    ATTENDING = "71"
    OPERATING = "72"
    OTHER_OPERATING = "ZZ"
    REFERRING = "DN"
    SUPERVISING = "DQ"
    ORDERING = "DK"
    SERVICE_FACILITY = "77"


class ProviderEntityType(StrEnum):
    """NM102 entity-type qualifier."""

    PERSON = "1"
    NON_PERSON = "2"


def _npi_checksum_ok(npi: str) -> bool:
    """Validate a 10-digit NPI using the CMS-specified Luhn variant.

    The algorithm prepends the healthcare industry prefix ``80840`` to the
    first nine digits, runs a standard Luhn against the 14-digit string, and
    compares the result against the NPI's tenth digit.
    """

    body = "80840" + npi[:9]
    total = 0
    for index, character in enumerate(reversed(body), start=1):
        digit = int(character)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    expected = (10 - (total % 10)) % 10
    return expected == int(npi[-1])


def validate_npi(value: str) -> str:
    """Return ``value`` if it is a well-formed, checksum-valid NPI."""

    if len(value) != 10 or not value.isdigit():
        raise ValueError("npi must be exactly 10 digits")
    if not _npi_checksum_ok(value):
        raise ValueError("npi fails the CMS Luhn checksum")
    return value


class ProviderAddress(BaseModel):
    """Postal address for a provider or service facility."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    address_line_1: Annotated[str, Field(min_length=1, max_length=55)]
    address_line_2: str | None = Field(default=None, max_length=55)
    city: Annotated[str, Field(min_length=1, max_length=30)]
    state: Annotated[str, Field(min_length=2, max_length=2)]
    postal_code: Annotated[str, Field(min_length=3, max_length=15)]
    country_code: str | None = Field(default=None, max_length=3)

    @field_validator("state")
    @classmethod
    def _state_upper(cls, value: str) -> str:
        return value.upper()


class _ProviderBase(BaseModel):
    """Shared provider fields (name, NPI, taxonomy)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    entity_type: ProviderEntityType
    npi: Annotated[str, Field(min_length=10, max_length=10)]
    organization_name: str | None = Field(default=None, max_length=60)
    first_name: str | None = Field(default=None, max_length=35)
    last_name: str | None = Field(default=None, max_length=60)
    middle_name: str | None = Field(default=None, max_length=25)
    name_suffix: str | None = Field(default=None, max_length=10)
    taxonomy_code: str | None = Field(default=None, min_length=10, max_length=10)

    @field_validator("npi")
    @classmethod
    def _validate_npi(cls, value: str) -> str:
        return validate_npi(value)

    @model_validator(mode="after")
    def _validate_name_by_entity(self) -> _ProviderBase:
        if self.entity_type == ProviderEntityType.NON_PERSON:
            if not self.organization_name:
                raise ValueError(
                    "organization_name is required when entity_type is NON_PERSON"
                )
        else:
            if not (self.first_name and self.last_name):
                raise ValueError(
                    "first_name and last_name are required when entity_type is PERSON"
                )
        return self


class BillingProvider(_ProviderBase):
    """Loop 2000A / 2010AA — the billing provider submitting the claim."""

    role: ProviderRole = ProviderRole.BILLING
    tax_id: Annotated[str, Field(min_length=9, max_length=20)]
    tax_id_qualifier: Annotated[str, Field(min_length=2, max_length=2)] = "EI"
    address: ProviderAddress
    pay_to_address: ProviderAddress | None = None
    contact_name: str | None = Field(default=None, max_length=60)
    contact_phone: str | None = Field(default=None, max_length=20)
    contact_email: str | None = Field(default=None, max_length=80)

    @field_validator("tax_id_qualifier")
    @classmethod
    def _tax_id_qualifier_allowed(cls, value: str) -> str:
        if value not in {"EI", "SY"}:
            raise ValueError("tax_id_qualifier must be 'EI' (EIN) or 'SY' (SSN)")
        return value


class RenderingProvider(_ProviderBase):
    """Loop 2310B / 2420A — individual clinician who rendered the service."""

    role: ProviderRole = ProviderRole.RENDERING


class AttendingProvider(_ProviderBase):
    """Loop 2310A — attending physician on institutional claims (837I)."""

    role: ProviderRole = ProviderRole.ATTENDING


class ReferringProvider(_ProviderBase):
    """Loop 2310A (837P) / 2310F — referring provider."""

    role: ProviderRole = ProviderRole.REFERRING


class ServiceFacility(BaseModel):
    """Loop 2310C / 2310E — physical location where services were rendered."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=60)]
    npi: Annotated[str, Field(min_length=10, max_length=10)]
    address: ProviderAddress
    role: ProviderRole = ProviderRole.SERVICE_FACILITY
    facility_type_code: str | None = Field(default=None, max_length=2)

    @field_validator("npi")
    @classmethod
    def _validate_npi(cls, value: str) -> str:
        return validate_npi(value)


__all__ = [
    "AttendingProvider",
    "BillingProvider",
    "ProviderAddress",
    "ProviderEntityType",
    "ProviderRole",
    "ReferringProvider",
    "RenderingProvider",
    "ServiceFacility",
    "validate_npi",
]
