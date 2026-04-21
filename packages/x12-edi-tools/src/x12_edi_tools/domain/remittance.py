"""Remittance (835) domain projection.

The library projects a parsed 835 transaction into this shape via
``readers/remittance_835.py``. The objects here are deliberately flat so
downstream consumers (posting logic, denial dashboards) do not need to walk
X12 loops. Monetary totals are reconciled at model-validation time — any
CLP/SVC group whose payer adjustments + paid amount do not equal the
billed charge raises a :class:`ValueError` rather than producing a silent
inconsistency.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from x12_edi_tools.domain.adjustment import (
    Adjustment,
    CARCRARCMessage,
)

MoneyAmount = Annotated[
    Decimal,
    Field(
        max_digits=18,
        decimal_places=2,
        ge=Decimal("-99999999999999.99"),
        le=Decimal("99999999999999.99"),
    ),
]
PositiveMoneyAmount = Annotated[
    Decimal,
    Field(max_digits=18, decimal_places=2, ge=Decimal("0")),
]


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class PaymentMethodCode(StrEnum):
    """BPR04 payment method code."""

    ACH = "ACH"
    CHECK = "CHK"
    FEDERAL_RESERVE_FUNDS_TRANSFER = "FWT"
    NON_PAYMENT = "NON"
    BOOK_ENTRY = "BOP"


class ClaimStatusCode(StrEnum):
    """CLP02 claim status code (X12 code list 1029)."""

    PROCESSED_AS_PRIMARY = "1"
    PROCESSED_AS_SECONDARY = "2"
    PROCESSED_AS_TERTIARY = "3"
    DENIED = "4"
    PROCESSED_AS_PRIMARY_FORWARDED = "19"
    PROCESSED_AS_SECONDARY_FORWARDED = "20"
    PROCESSED_AS_TERTIARY_FORWARDED = "21"
    REVERSAL_OF_PREVIOUS_PAYMENT = "22"
    NOT_OUR_CLAIM_FORWARDED = "23"
    PREDETERMINATION_PRICING_ONLY = "25"


class ClaimFilingIndicator(StrEnum):
    """CLP06 claim filing indicator (subset)."""

    MEDICARE_PART_B = "MB"
    MEDICAID = "MC"
    COMMERCIAL_INSURANCE = "CI"
    BLUE_CROSS_BLUE_SHIELD = "BL"
    HMO = "HM"
    PREFERRED_PROVIDER_ORGANIZATION = "12"
    SELF_PAY = "09"
    AUTOMOBILE_MEDICAL = "AM"
    CHAMPUS = "CH"
    OTHER = "11"


class ProviderAdjustmentReason(StrEnum):
    """PLB03-1 / PLB05-1 provider-level adjustment reason codes (subset)."""

    ACCELERATED_PAYMENT = "AP"
    ADVANCE_PAYMENT = "AP2"
    FORWARDING_BALANCE = "FB"
    INTEREST = "L6"
    LATE_CLAIM_FILING_REDUCTION = "50"
    ORIGINATION_FEE = "OF"
    OVERPAYMENT_RECOVERY = "WO"
    REFUND = "RF"
    CAPITATION_PAYMENT = "CT"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class RemittancePayment(BaseModel):
    """BPR payment header: method, amount, effective date, and trace."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    payment_method: PaymentMethodCode
    payment_amount: MoneyAmount
    payment_date: date
    trace_number: Annotated[str, Field(min_length=1, max_length=80)]
    trace_originator_id: str | None = Field(default=None, max_length=50)
    credit_debit_flag: Annotated[str, Field(min_length=1, max_length=1)] = "C"

    sender_bank_id: str | None = Field(default=None, max_length=12)
    sender_account: str | None = Field(default=None, max_length=35)
    receiver_bank_id: str | None = Field(default=None, max_length=12)
    receiver_account: str | None = Field(default=None, max_length=35)

    @field_validator("credit_debit_flag")
    @classmethod
    def _validate_cd_flag(cls, value: str) -> str:
        value = value.upper()
        if value not in {"C", "D"}:
            raise ValueError("credit_debit_flag must be 'C' (credit) or 'D' (debit)")
        return value


class ProviderLevelAdjustment(BaseModel):
    """PLB provider-level adjustment entry (not tied to a single claim)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    reason_code: ProviderAdjustmentReason
    amount: MoneyAmount
    reference_id: str | None = Field(default=None, max_length=50)
    fiscal_period_end: date | None = None


class RemittanceServiceLine(BaseModel):
    """Service-line adjudication (SVC / CAS / DTM / REF / AMT / LQ).

    Lines with ``paid_amount == 0`` are valid — full-denial lines carry the
    denial CAS groups and a zero paid amount rather than being omitted.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    procedure_code: Annotated[str, Field(min_length=1, max_length=48)]
    procedure_code_qualifier: Annotated[str, Field(max_length=3)] = "HC"
    modifiers: list[str] = Field(default_factory=list, max_length=4)
    charge_amount: PositiveMoneyAmount
    paid_amount: MoneyAmount
    allowed_amount: MoneyAmount | None = None
    units_paid: Decimal | None = Field(default=None, max_digits=15, decimal_places=3)
    units_billed: Decimal | None = Field(default=None, max_digits=15, decimal_places=3)
    revenue_code: str | None = Field(default=None, min_length=3, max_length=4)
    service_date: date | None = None
    line_control_number: str | None = Field(default=None, max_length=50)

    adjustments: list[Adjustment] = Field(default_factory=list)
    remark_codes: list[CARCRARCMessage] = Field(default_factory=list)

    @field_validator("modifiers")
    @classmethod
    def _modifiers_shape(cls, value: list[str]) -> list[str]:
        result: list[str] = []
        for modifier in value:
            stripped = modifier.strip()
            if len(stripped) != 2:
                raise ValueError("each modifier must be exactly 2 characters")
            result.append(stripped.upper())
        return result


class RemittanceClaim(BaseModel):
    """CLP claim-level adjudication plus its service lines.

    ``billed_amount`` and ``paid_amount`` are expressed as Decimal with two
    decimal places. A structural invariant — billed = paid + patient
    responsibility + total CAS adjustments — is enforced unless the claim is
    a reversal (``ClaimStatusCode.REVERSAL_OF_PREVIOUS_PAYMENT``) where
    amounts may be negative and the constraint is relaxed.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    patient_control_number: Annotated[str, Field(min_length=1, max_length=38)]
    status_code: ClaimStatusCode
    billed_amount: MoneyAmount
    paid_amount: MoneyAmount
    patient_responsibility: MoneyAmount = Decimal("0")
    claim_filing_indicator: ClaimFilingIndicator | None = None
    payer_claim_control_number: str | None = Field(default=None, max_length=50)

    patient_first_name: str | None = Field(default=None, max_length=35)
    patient_last_name: str | None = Field(default=None, max_length=60)
    payer_member_id: str | None = Field(default=None, max_length=80)

    facility_type_code: str | None = Field(default=None, max_length=3)
    claim_frequency_code: str | None = Field(default=None, max_length=1)

    diagnosis_related_group: str | None = Field(default=None, max_length=10)
    drg_weight: Decimal | None = Field(default=None, max_digits=10, decimal_places=4)

    received_date: date | None = None
    statement_period_start: date | None = None
    statement_period_end: date | None = None

    claim_adjustments: list[Adjustment] = Field(default_factory=list)
    service_lines: list[RemittanceServiceLine] = Field(default_factory=list)
    remark_codes: list[CARCRARCMessage] = Field(default_factory=list)

    @model_validator(mode="after")
    def _reconcile_totals(self) -> RemittanceClaim:
        if self.status_code == ClaimStatusCode.REVERSAL_OF_PREVIOUS_PAYMENT:
            return self
        adjustment_total = sum((adj.amount for adj in self.claim_adjustments), Decimal("0"))
        expected = (
            self.paid_amount.quantize(Decimal("0.01"))
            + self.patient_responsibility.quantize(Decimal("0.01"))
            + adjustment_total.quantize(Decimal("0.01"))
        )
        if expected != self.billed_amount.quantize(Decimal("0.01")):
            raise ValueError(
                f"remittance claim {self.patient_control_number}: billed "
                f"{self.billed_amount} does not reconcile to paid {self.paid_amount} "
                f"+ patient_responsibility {self.patient_responsibility} + CAS "
                f"{adjustment_total}"
            )
        return self

    @property
    def is_denied(self) -> bool:
        """Shortcut for callers that only care about denial vs. paid outcomes."""

        return self.status_code == ClaimStatusCode.DENIED or self.paid_amount <= 0


class Remittance(BaseModel):
    """Top-level 835 projection representing one ST..SE remittance transaction."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    transaction_set_control_number: Annotated[str, Field(min_length=1, max_length=15)]
    payer_identifier: Annotated[str, Field(min_length=1, max_length=80)]
    payer_name: Annotated[str, Field(min_length=1, max_length=60)]
    payee_identifier: Annotated[str, Field(min_length=1, max_length=80)]
    payee_name: Annotated[str, Field(min_length=1, max_length=60)]

    production_date: date
    payment: RemittancePayment
    claims: list[RemittanceClaim] = Field(default_factory=list)
    provider_adjustments: list[ProviderLevelAdjustment] = Field(default_factory=list)

    @property
    def total_billed(self) -> Decimal:
        return sum((claim.billed_amount for claim in self.claims), Decimal("0"))

    @property
    def total_paid(self) -> Decimal:
        return sum((claim.paid_amount for claim in self.claims), Decimal("0"))

    @property
    def total_provider_adjustments(self) -> Decimal:
        return sum((adj.amount for adj in self.provider_adjustments), Decimal("0"))


__all__ = [
    "ClaimFilingIndicator",
    "ClaimStatusCode",
    "PaymentMethodCode",
    "ProviderAdjustmentReason",
    "ProviderLevelAdjustment",
    "Remittance",
    "RemittanceClaim",
    "RemittancePayment",
    "RemittanceServiceLine",
]
