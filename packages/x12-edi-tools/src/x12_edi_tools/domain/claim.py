"""Claim domain objects covering both institutional (837I) and professional
(837P) submission shapes.

The top-level :class:`Claim` is a discriminated model keyed on
:attr:`Claim.claim_type` so the same domain object can be dispatched to
``build_837i`` or ``build_837p`` without duplicate upstream schemas. Shape
differences between the two transaction sets (type-of-bill vs. place-of-
service, revenue code vs. procedure code, attending-required vs. rendering-
required) are enforced by :class:`Claim` / :class:`ClaimLine` model
validators, not by separate classes.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from x12_edi_tools.domain.patient import Patient, PatientRelationship, Subscriber
from x12_edi_tools.domain.payer import Payer
from x12_edi_tools.domain.provider import (
    AttendingProvider,
    BillingProvider,
    ReferringProvider,
    RenderingProvider,
    ServiceFacility,
)

# ---------------------------------------------------------------------------
# Shared money / quantity types
# ---------------------------------------------------------------------------

MoneyAmount = Annotated[
    Decimal,
    Field(
        max_digits=18,
        decimal_places=2,
        ge=Decimal("-99999999999999.99"),
        le=Decimal("99999999999999.99"),
    ),
]
"""Two-decimal-place currency amount. Negative permitted for reversals."""

PositiveMoneyAmount = Annotated[
    Decimal,
    Field(max_digits=18, decimal_places=2, ge=Decimal("0")),
]

UnitQuantity = Annotated[
    Decimal,
    Field(max_digits=15, decimal_places=3, ge=Decimal("0")),
]


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ClaimType(StrEnum):
    """CLM05-3 / claim-family discriminator.

    The values match the letter codes used internally by the library (not the
    CLM05-1 Facility Code Value). ``INSTITUTIONAL`` → 837I, ``PROFESSIONAL``
    → 837P.
    """

    INSTITUTIONAL = "I"
    PROFESSIONAL = "P"


class ClaimFrequencyCode(StrEnum):
    """CLM05-3 claim frequency type code (NUBC code list subset)."""

    ORIGINAL = "1"
    INTERIM_FIRST = "2"
    INTERIM_CONTINUING = "3"
    INTERIM_LAST = "4"
    LATE_CHARGE = "5"
    REPLACEMENT = "7"
    VOID = "8"


class BenefitsAssignmentCode(StrEnum):
    """CLM08 assignment-of-benefits indicator."""

    YES = "Y"
    NO = "N"
    NOT_APPLICABLE = "W"


class ReleaseOfInformationCode(StrEnum):
    """CLM09 release-of-information code."""

    AUTHORIZED = "Y"
    INFORMED_CONSENT = "I"
    SIGNED_STATEMENT_NOT_OBTAINED = "N"


class ClaimSupportingInfoCategory(StrEnum):
    """HI01-1 code list categories used in 2300 HI segments."""

    PRINCIPAL_DIAGNOSIS = "ABK"
    OTHER_DIAGNOSIS = "ABF"
    ADMITTING_DIAGNOSIS = "ABJ"
    PATIENT_REASON_FOR_VISIT = "APR"
    EXTERNAL_CAUSE_OF_INJURY = "ABN"
    VALUE = "BE"
    OCCURRENCE = "BH"
    OCCURRENCE_SPAN = "BI"
    CONDITION = "BG"
    TREATMENT_CODE = "BJ"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class DateRange(BaseModel):
    """Inclusive date range used for statement and service periods."""

    model_config = ConfigDict(extra="forbid")

    start: date
    end: date

    @model_validator(mode="after")
    def _end_not_before_start(self) -> DateRange:
        if self.end < self.start:
            raise ValueError("DateRange.end must not be before DateRange.start")
        return self


class ClaimSupportingInfo(BaseModel):
    """Entry in an HI segment (diagnoses, value codes, occurrence codes, etc.).

    ``category`` determines how ``code`` is interpreted — a principal
    diagnosis uses the ICD-10 code system while a value code carries a
    numeric dollar amount in ``amount``.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    category: ClaimSupportingInfoCategory
    code: Annotated[str, Field(min_length=1, max_length=30)]
    amount: MoneyAmount | None = None
    occurred_on: date | None = None
    quantity: UnitQuantity | None = None
    present_on_admission: Annotated[str, Field(max_length=1)] | None = None


class ClaimAdjustment(BaseModel):
    """CAS-level adjustment applied at the claim (not service-line) level.

    Service-line CAS adjustments live on :class:`ClaimLine.adjustments` using
    :class:`x12_edi_tools.domain.adjustment.Adjustment` — the two are kept
    separate so that a claim-level total can be validated against the sum of
    the lines.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    group_code: Annotated[str, Field(min_length=2, max_length=2)]
    reason_code: Annotated[str, Field(min_length=1, max_length=5)]
    amount: MoneyAmount
    quantity: UnitQuantity | None = None

    @field_validator("group_code")
    @classmethod
    def _group_code_upper(cls, value: str) -> str:
        value = value.upper()
        if value not in {"CO", "CR", "OA", "PI", "PR"}:
            raise ValueError("group_code must be one of CO, CR, OA, PI, PR (X12 adjustment groups)")
        return value


class ClaimLine(BaseModel):
    """One detail line on a claim.

    837I lines are keyed by revenue code (``revenue_code``) while 837P lines
    are keyed by HCPCS / CPT procedure code (``procedure_code``). The
    ``line_type`` discriminator is validated against :class:`Claim.claim_type`
    at :class:`Claim` level so mismatches fail fast.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    line_number: Annotated[int, Field(ge=1, le=999_999)]
    line_type: ClaimType

    # 837I: revenue_code is required; procedure_code is optional (HCPCS).
    # 837P: procedure_code is required; revenue_code must be None.
    revenue_code: str | None = Field(default=None, min_length=3, max_length=4)
    procedure_code: str | None = Field(default=None, min_length=1, max_length=48)
    procedure_code_qualifier: Annotated[str, Field(max_length=2)] | None = None
    modifiers: list[str] = Field(default_factory=list, max_length=4)

    charge_amount: PositiveMoneyAmount
    units: UnitQuantity = Decimal("1")
    unit_basis: Annotated[str, Field(min_length=2, max_length=2)] = "UN"
    service_date: date | None = None
    service_date_range: DateRange | None = None

    place_of_service: str | None = Field(default=None, min_length=2, max_length=2)
    diagnosis_pointers: list[int] = Field(default_factory=list, max_length=4)
    rendering_provider: RenderingProvider | None = None

    note: str | None = Field(default=None, max_length=80)
    adjustments: list[ClaimAdjustment] = Field(default_factory=list)

    @field_validator("modifiers")
    @classmethod
    def _modifiers_shape(cls, value: list[str]) -> list[str]:
        for modifier in value:
            stripped = modifier.strip()
            if not (2 <= len(stripped) <= 2):
                raise ValueError("each modifier must be exactly 2 characters")
        return [m.strip().upper() for m in value]

    @field_validator("diagnosis_pointers")
    @classmethod
    def _pointer_bounds(cls, value: list[int]) -> list[int]:
        for pointer in value:
            if not 1 <= pointer <= 12:
                raise ValueError("diagnosis_pointers must reference HI entries 1-12")
        return value

    @model_validator(mode="after")
    def _shape_by_line_type(self) -> ClaimLine:
        if self.line_type == ClaimType.INSTITUTIONAL:
            if self.revenue_code is None:
                raise ValueError("institutional lines require a revenue_code")
            if self.place_of_service is not None:
                raise ValueError(
                    "place_of_service is professional-only; use CL1 type-of-bill for 837I"
                )
        else:  # PROFESSIONAL
            if self.procedure_code is None:
                raise ValueError("professional lines require a procedure_code")
            if self.revenue_code is not None:
                raise ValueError("revenue_code is institutional-only; omit on 837P lines")
        if self.service_date is None and self.service_date_range is None:
            raise ValueError("either service_date or service_date_range is required")
        return self


class Claim(BaseModel):
    """Single claim (one CLM segment) regardless of institutional/professional.

    Total-charge validation ensures the claim-level CLM02 value equals the
    sum of line charges (to two decimal places). Line numbers must be a
    contiguous 1..N sequence to preserve LX ordering on encode.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    claim_id: Annotated[str, Field(min_length=1, max_length=38)]
    claim_type: ClaimType
    total_charge: PositiveMoneyAmount
    frequency_code: ClaimFrequencyCode = ClaimFrequencyCode.ORIGINAL

    billing_provider: BillingProvider
    subscriber: Subscriber
    patient: Patient | None = None
    payer: Payer

    attending_provider: AttendingProvider | None = None
    referring_provider: ReferringProvider | None = None
    service_facility: ServiceFacility | None = None

    statement_period: DateRange | None = None
    admission_date: date | None = None
    discharge_date: date | None = None
    admission_type_code: str | None = Field(default=None, min_length=1, max_length=1)
    admission_source_code: str | None = Field(default=None, min_length=1, max_length=1)
    patient_status_code: str | None = Field(default=None, min_length=2, max_length=2)

    type_of_bill: str | None = Field(default=None, min_length=3, max_length=4)
    place_of_service: str | None = Field(default=None, min_length=2, max_length=2)

    assignment_of_benefits: BenefitsAssignmentCode = BenefitsAssignmentCode.YES
    release_of_information: ReleaseOfInformationCode = ReleaseOfInformationCode.AUTHORIZED
    signature_on_file: bool = True

    prior_authorization_number: str | None = Field(default=None, max_length=50)
    referral_number: str | None = Field(default=None, max_length=50)
    medical_record_number: str | None = Field(default=None, max_length=50)

    supporting_info: list[ClaimSupportingInfo] = Field(default_factory=list)
    adjustments: list[ClaimAdjustment] = Field(default_factory=list)
    lines: list[ClaimLine] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=80)

    @field_validator("claim_id")
    @classmethod
    def _claim_id_basic(cls, value: str) -> str:
        if any(ch in value for ch in ("*", "~", ":", "^", "|")):
            raise ValueError("claim_id must not contain X12 delimiter characters (*, ~, :, ^, |)")
        return value

    @model_validator(mode="after")
    def _validate_claim(self) -> Claim:
        # Line-type consistency with claim-type.
        for line in self.lines:
            if line.line_type != self.claim_type:
                raise ValueError(
                    f"line {line.line_number} has line_type={line.line_type.value}, "
                    f"expected {self.claim_type.value} to match claim_type"
                )

        # Contiguous 1..N line numbering.
        expected = list(range(1, len(self.lines) + 1))
        actual = [line.line_number for line in self.lines]
        if actual != expected:
            raise ValueError("line_number sequence must be contiguous 1..N in declaration order")

        # Total-charge reconciliation (2-decimal).
        line_sum = sum((line.charge_amount for line in self.lines), Decimal("0"))
        if line_sum.quantize(Decimal("0.01")) != self.total_charge.quantize(Decimal("0.01")):
            raise ValueError(
                f"total_charge {self.total_charge} does not equal sum of line charges {line_sum}"
            )

        # Transaction-specific required fields.
        if self.claim_type == ClaimType.INSTITUTIONAL:
            if self.type_of_bill is None:
                raise ValueError("837I claims require type_of_bill")
            if self.attending_provider is None:
                raise ValueError("837I claims require an attending_provider per CG §3.2 (SNIP 5)")
            if self.statement_period is None:
                raise ValueError("837I claims require statement_period dates")
        else:
            if self.place_of_service is None:
                raise ValueError("837P claims require place_of_service")

        # Patient is required when subscriber is not the patient.
        sub_relation = self.subscriber.relationship_to_insured
        if sub_relation != PatientRelationship.SELF and self.patient is None:
            raise ValueError("patient is required when subscriber.relationship_to_insured != SELF")

        # Admission / discharge coherence when both are present.
        if (
            self.admission_date is not None
            and self.discharge_date is not None
            and self.discharge_date < self.admission_date
        ):
            raise ValueError("discharge_date must not precede admission_date")

        return self

    @property
    def is_replacement(self) -> bool:
        """True when the claim frequency indicates a corrected/replacement submission."""

        return self.frequency_code == ClaimFrequencyCode.REPLACEMENT

    @property
    def is_void(self) -> bool:
        """True when the claim frequency indicates a void submission."""

        return self.frequency_code == ClaimFrequencyCode.VOID


__all__ = [
    "BenefitsAssignmentCode",
    "Claim",
    "ClaimAdjustment",
    "ClaimFrequencyCode",
    "ClaimLine",
    "ClaimSupportingInfo",
    "ClaimSupportingInfoCategory",
    "ClaimType",
    "DateRange",
    "MoneyAmount",
    "PositiveMoneyAmount",
    "ReleaseOfInformationCode",
    "UnitQuantity",
]
