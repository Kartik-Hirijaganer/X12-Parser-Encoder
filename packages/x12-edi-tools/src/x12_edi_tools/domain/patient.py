"""Patient and Subscriber domain objects for 837 claim submission.

``Subscriber`` represents the insured party on a policy (loop 2010BA).
``Patient`` represents the person receiving services (loop 2010CA); when the
subscriber *is* the patient (``PatientRelationship.SELF``), no separate
``Patient`` record is required — builders detect this and collapse to 2010BA.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from x12_edi_tools.common.enums import GenderCode


class PatientRelationship(StrEnum):
    """SBR02 / PAT01 relationship codes (X12 code list 1069 subset).

    Only the codes meaningful to 837 home-health / ambulatory claim flows are
    encoded here. Additional codes can be added under a separate enum
    extension without touching existing callers.
    """

    SELF = "18"
    SPOUSE = "01"
    CHILD = "19"
    EMPLOYEE = "20"
    UNKNOWN = "21"
    ORGAN_DONOR = "39"
    CADAVER_DONOR = "40"
    LIFE_PARTNER = "53"
    OTHER_RELATIONSHIP = "G8"


class PatientAddress(BaseModel):
    """Patient / subscriber postal address."""

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


class _Person(BaseModel):
    """Shared name fields for subscribers and patients."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    first_name: Annotated[str, Field(min_length=1, max_length=35)]
    last_name: Annotated[str, Field(min_length=1, max_length=60)]
    middle_name: str | None = Field(default=None, max_length=25)
    name_suffix: str | None = Field(default=None, max_length=10)
    birth_date: date
    gender: GenderCode = GenderCode.UNKNOWN


class Subscriber(_Person):
    """Policy subscriber (insured party). Identified by the payer member ID."""

    member_id: Annotated[str, Field(min_length=1, max_length=80)]
    group_number: str | None = Field(default=None, max_length=50)
    relationship_to_insured: PatientRelationship = PatientRelationship.SELF
    address: PatientAddress | None = None
    ssn_last_four: str | None = Field(default=None, min_length=4, max_length=4)

    @field_validator("member_id")
    @classmethod
    def _member_id_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("member_id must not be blank")
        return value

    @field_validator("ssn_last_four")
    @classmethod
    def _ssn_digits(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.isdigit():
            raise ValueError("ssn_last_four must contain only digits")
        return value


class Patient(_Person):
    """Person receiving services when *not* the subscriber.

    When ``relationship_to_subscriber`` is :attr:`PatientRelationship.SELF`,
    builders should use the ``Subscriber`` directly (loop 2010BA) and skip
    the 2010CA loop. Domain-level validation enforces this invariant.
    """

    relationship_to_subscriber: PatientRelationship
    address: PatientAddress | None = None

    @field_validator("relationship_to_subscriber")
    @classmethod
    def _reject_self_as_distinct_patient(cls, value: PatientRelationship) -> PatientRelationship:
        if value == PatientRelationship.SELF:
            raise ValueError(
                "Patient represents a non-subscriber; use Subscriber directly when "
                "relationship is SELF."
            )
        return value


__all__ = [
    "Patient",
    "PatientAddress",
    "PatientRelationship",
    "Subscriber",
]
