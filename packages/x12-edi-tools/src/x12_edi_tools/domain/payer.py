"""Payer domain objects (X12-agnostic).

Business objects representing the payer entity on a claim or remittance.
These are wire-format independent; ``builders/`` translate them into
NM1/N3/N4/PER segments at encode time.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PayerResponsibility(StrEnum):
    """SBR01 payer responsibility sequence for 837 claims."""

    PRIMARY = "P"
    SECONDARY = "S"
    TERTIARY = "T"


class PayerIdQualifier(StrEnum):
    """NM108 qualifier for the payer identifier on claims / remittance."""

    PAYOR_IDENTIFICATION = "PI"
    CMS_PLAN_ID = "XV"


class PayerAddress(BaseModel):
    """Postal address for a payer. All fields are non-PHI reference data."""

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


class Payer(BaseModel):
    """Payer / insurance carrier identity used by 837 and 835 flows."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=60)]
    payer_id: Annotated[str, Field(min_length=1, max_length=80)]
    payer_id_qualifier: PayerIdQualifier = PayerIdQualifier.PAYOR_IDENTIFICATION
    responsibility: PayerResponsibility = PayerResponsibility.PRIMARY
    claim_filing_indicator_code: Annotated[str, Field(min_length=1, max_length=2)] = "MC"
    group_number: str | None = Field(default=None, max_length=50)
    group_name: str | None = Field(default=None, max_length=60)
    address: PayerAddress | None = None
    contact_name: str | None = Field(default=None, max_length=60)
    contact_phone: str | None = Field(default=None, max_length=20)

    @field_validator("payer_id")
    @classmethod
    def _reject_whitespace_payer_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("payer_id must not be blank")
        return value


__all__ = [
    "Payer",
    "PayerAddress",
    "PayerIdQualifier",
    "PayerResponsibility",
]
