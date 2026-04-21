"""Tests for domain.remittance."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from x12_edi_tools.domain.adjustment import (
    Adjustment,
    AdjustmentGroupCode,
    ClaimAdjustmentReasonCode,
)
from x12_edi_tools.domain.remittance import (
    ClaimFilingIndicator,
    ClaimStatusCode,
    PaymentMethodCode,
    ProviderAdjustmentReason,
    ProviderLevelAdjustment,
    Remittance,
    RemittanceClaim,
    RemittancePayment,
    RemittanceServiceLine,
)

from ._builders import (
    SYNTHETIC_NPI_BILLING,
    make_adjustment,
    make_remittance,
    make_remittance_claim,
    make_remittance_payment,
    make_remittance_service_line,
)

# --------- RemittancePayment ------------------------------------------------


def test_remittance_payment_happy_path() -> None:
    payment = make_remittance_payment(amount=Decimal("250.00"))
    assert payment.payment_method == PaymentMethodCode.ACH
    assert payment.credit_debit_flag == "C"


def test_remittance_payment_rejects_bad_flag() -> None:
    with pytest.raises(ValidationError):
        RemittancePayment(
            payment_method=PaymentMethodCode.ACH,
            payment_amount=Decimal("100.00"),
            payment_date=date(2026, 3, 1),
            trace_number="TRACE01",
            credit_debit_flag="X",
        )


def test_remittance_payment_normalizes_flag() -> None:
    payment = RemittancePayment(
        payment_method=PaymentMethodCode.CHECK,
        payment_amount=Decimal("100.00"),
        payment_date=date(2026, 3, 1),
        trace_number="TRACE01",
        credit_debit_flag="d",
    )
    assert payment.credit_debit_flag == "D"


# --------- RemittanceServiceLine --------------------------------------------


def test_service_line_modifier_validation() -> None:
    with pytest.raises(ValidationError, match="modifier"):
        RemittanceServiceLine(
            procedure_code="99213",
            charge_amount=Decimal("100.00"),
            paid_amount=Decimal("90.00"),
            modifiers=["XYZ"],
        )


def test_service_line_modifier_normalization() -> None:
    line = RemittanceServiceLine(
        procedure_code="99213",
        charge_amount=Decimal("100.00"),
        paid_amount=Decimal("90.00"),
        modifiers=["  25 ", "59"],
    )
    assert line.modifiers == ["25", "59"]


def test_service_line_allows_full_denial() -> None:
    line = make_remittance_service_line(charge=Decimal("100.00"), paid=Decimal("0"))
    assert line.paid_amount == Decimal("0")


# --------- RemittanceClaim --------------------------------------------------


def test_remittance_claim_reconciles() -> None:
    claim = make_remittance_claim(
        billed=Decimal("100.00"),
        paid=Decimal("90.00"),
        patient_resp=Decimal("0"),
    )
    assert claim.billed_amount == Decimal("100.00")
    assert claim.claim_filing_indicator == ClaimFilingIndicator.MEDICAID
    assert not claim.is_denied


def test_remittance_claim_reconciles_with_patient_responsibility() -> None:
    claim = make_remittance_claim(
        billed=Decimal("100.00"),
        paid=Decimal("70.00"),
        patient_resp=Decimal("20.00"),
        adjustments=[
            make_adjustment(
                group=AdjustmentGroupCode.CONTRACTUAL_OBLIGATIONS,
                amount=Decimal("10.00"),
            )
        ],
    )
    assert claim.patient_responsibility == Decimal("20.00")


def test_remittance_claim_rejects_imbalanced_totals() -> None:
    with pytest.raises(ValidationError, match="does not reconcile"):
        RemittanceClaim(
            patient_control_number="BAD",
            status_code=ClaimStatusCode.PROCESSED_AS_PRIMARY,
            billed_amount=Decimal("100.00"),
            paid_amount=Decimal("50.00"),
            patient_responsibility=Decimal("0"),
            claim_adjustments=[],
        )


def test_remittance_claim_allows_reversal_imbalance() -> None:
    """Reversals legitimately have negative amounts that don't reconcile."""

    claim = RemittanceClaim(
        patient_control_number="REV-001",
        status_code=ClaimStatusCode.REVERSAL_OF_PREVIOUS_PAYMENT,
        billed_amount=Decimal("0"),
        paid_amount=Decimal("-50.00"),
        patient_responsibility=Decimal("0"),
        claim_adjustments=[],
    )
    assert claim.paid_amount == Decimal("-50.00")


def test_remittance_claim_is_denied_when_status_denied() -> None:
    claim = RemittanceClaim(
        patient_control_number="DEN-001",
        status_code=ClaimStatusCode.DENIED,
        billed_amount=Decimal("100.00"),
        paid_amount=Decimal("0"),
        patient_responsibility=Decimal("0"),
        claim_adjustments=[
            Adjustment(
                group_code=AdjustmentGroupCode.CONTRACTUAL_OBLIGATIONS,
                reason_code=ClaimAdjustmentReasonCode(value="29"),
                amount=Decimal("100.00"),
            )
        ],
    )
    assert claim.is_denied


# --------- ProviderLevelAdjustment ------------------------------------------


def test_provider_level_adjustment() -> None:
    plb = ProviderLevelAdjustment(
        reason_code=ProviderAdjustmentReason.INTEREST,
        amount=Decimal("5.00"),
        reference_id="INT-2026Q1",
        fiscal_period_end=date(2026, 3, 31),
    )
    assert plb.reason_code == ProviderAdjustmentReason.INTEREST


# --------- Remittance (top-level) -------------------------------------------


def test_remittance_aggregates() -> None:
    remit = make_remittance()
    assert remit.total_billed == Decimal("100.00")
    assert remit.total_paid == Decimal("90.00")
    assert remit.total_provider_adjustments == Decimal("0")
    assert remit.payer_name == "DC Medicaid"


def test_remittance_with_provider_level_adjustments() -> None:
    remit = Remittance(
        transaction_set_control_number="0002",
        payer_identifier="DCMEDICAID",
        payer_name="DC Medicaid",
        payee_identifier=SYNTHETIC_NPI_BILLING,
        payee_name="Synthetic Home Health LLC",
        production_date=date(2026, 3, 1),
        payment=make_remittance_payment(),
        claims=[make_remittance_claim()],
        provider_adjustments=[
            ProviderLevelAdjustment(
                reason_code=ProviderAdjustmentReason.INTEREST,
                amount=Decimal("10.00"),
            ),
            ProviderLevelAdjustment(
                reason_code=ProviderAdjustmentReason.FORWARDING_BALANCE,
                amount=Decimal("-5.00"),
            ),
        ],
    )
    assert remit.total_provider_adjustments == Decimal("5.00")
