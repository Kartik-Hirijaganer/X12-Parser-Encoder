"""Tests for domain.claim."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from x12_edi_tools.domain.claim import (
    BenefitsAssignmentCode,
    Claim,
    ClaimAdjustment,
    ClaimFrequencyCode,
    ClaimLine,
    ClaimSupportingInfo,
    ClaimSupportingInfoCategory,
    ClaimType,
    DateRange,
    ReleaseOfInformationCode,
)
from x12_edi_tools.domain.patient import PatientRelationship

from ._builders import (
    make_attending_provider,
    make_billing_provider,
    make_institutional_claim,
    make_institutional_line,
    make_patient,
    make_payer,
    make_professional_claim,
    make_professional_line,
    make_subscriber,
)

# --------- ClaimSupportingInfo -----------------------------------------------


def test_supporting_info_accepts_principal_diagnosis() -> None:
    info = ClaimSupportingInfo(
        category=ClaimSupportingInfoCategory.PRINCIPAL_DIAGNOSIS,
        code="R5182",
    )
    assert info.category == ClaimSupportingInfoCategory.PRINCIPAL_DIAGNOSIS


def test_supporting_info_value_code_with_amount() -> None:
    info = ClaimSupportingInfo(
        category=ClaimSupportingInfoCategory.VALUE,
        code="A2",
        amount=Decimal("25.00"),
    )
    assert info.amount == Decimal("25.00")


# --------- DateRange ---------------------------------------------------------


def test_date_range_requires_end_not_before_start() -> None:
    with pytest.raises(ValidationError, match="end must not be before"):
        DateRange(start=date(2026, 2, 10), end=date(2026, 2, 1))


def test_date_range_same_day_ok() -> None:
    DateRange(start=date(2026, 2, 1), end=date(2026, 2, 1))


# --------- ClaimAdjustment ---------------------------------------------------


def test_claim_adjustment_normalizes_group_code() -> None:
    adj = ClaimAdjustment(
        group_code="co",
        reason_code="45",
        amount=Decimal("10.00"),
    )
    assert adj.group_code == "CO"


def test_claim_adjustment_rejects_unknown_group() -> None:
    with pytest.raises(ValidationError):
        ClaimAdjustment(group_code="ZZ", reason_code="45", amount=Decimal("10.00"))


# --------- ClaimLine ---------------------------------------------------------


def test_institutional_line_happy_path() -> None:
    line = make_institutional_line()
    assert line.line_type == ClaimType.INSTITUTIONAL
    assert line.revenue_code == "0420"


def test_institutional_line_rejects_place_of_service() -> None:
    with pytest.raises(ValidationError, match="place_of_service is professional-only"):
        ClaimLine(
            line_number=1,
            line_type=ClaimType.INSTITUTIONAL,
            revenue_code="0420",
            charge_amount=Decimal("100.00"),
            service_date=date(2026, 2, 1),
            place_of_service="11",
        )


def test_professional_line_rejects_revenue_code() -> None:
    with pytest.raises(ValidationError, match="revenue_code is institutional-only"):
        ClaimLine(
            line_number=1,
            line_type=ClaimType.PROFESSIONAL,
            procedure_code="99213",
            revenue_code="0420",
            charge_amount=Decimal("100.00"),
            service_date=date(2026, 2, 1),
            place_of_service="11",
        )


def test_institutional_line_requires_revenue_code() -> None:
    with pytest.raises(ValidationError, match="revenue_code"):
        ClaimLine(
            line_number=1,
            line_type=ClaimType.INSTITUTIONAL,
            charge_amount=Decimal("100.00"),
            service_date=date(2026, 2, 1),
        )


def test_professional_line_requires_procedure_code() -> None:
    with pytest.raises(ValidationError, match="procedure_code"):
        ClaimLine(
            line_number=1,
            line_type=ClaimType.PROFESSIONAL,
            charge_amount=Decimal("100.00"),
            service_date=date(2026, 2, 1),
            place_of_service="11",
        )


def test_line_requires_service_date_or_range() -> None:
    with pytest.raises(ValidationError, match="service_date"):
        ClaimLine(
            line_number=1,
            line_type=ClaimType.PROFESSIONAL,
            procedure_code="99213",
            charge_amount=Decimal("100.00"),
            place_of_service="11",
        )


def test_line_modifier_shape_validation() -> None:
    with pytest.raises(ValidationError, match="modifier"):
        ClaimLine(
            line_number=1,
            line_type=ClaimType.PROFESSIONAL,
            procedure_code="99213",
            charge_amount=Decimal("100.00"),
            service_date=date(2026, 2, 1),
            place_of_service="11",
            modifiers=["longmodifier"],
        )
    line = ClaimLine(
        line_number=1,
        line_type=ClaimType.PROFESSIONAL,
        procedure_code="99213",
        charge_amount=Decimal("100.00"),
        service_date=date(2026, 2, 1),
        place_of_service="11",
        modifiers=["  25 ", "59"],
    )
    assert line.modifiers == ["25", "59"]


def test_line_diagnosis_pointer_bounds() -> None:
    with pytest.raises(ValidationError, match="diagnosis_pointers"):
        ClaimLine(
            line_number=1,
            line_type=ClaimType.PROFESSIONAL,
            procedure_code="99213",
            charge_amount=Decimal("100.00"),
            service_date=date(2026, 2, 1),
            place_of_service="11",
            diagnosis_pointers=[0, 15],
        )


def test_line_service_date_range_accepted() -> None:
    line = ClaimLine(
        line_number=1,
        line_type=ClaimType.INSTITUTIONAL,
        revenue_code="0420",
        charge_amount=Decimal("100.00"),
        service_date_range=DateRange(start=date(2026, 2, 1), end=date(2026, 2, 7)),
    )
    assert line.service_date_range is not None


# --------- Claim -------------------------------------------------------------


def test_institutional_claim_happy_path() -> None:
    claim = make_institutional_claim()
    assert claim.claim_type == ClaimType.INSTITUTIONAL
    assert claim.assignment_of_benefits == BenefitsAssignmentCode.YES
    assert claim.release_of_information == ReleaseOfInformationCode.AUTHORIZED
    assert not claim.is_replacement
    assert not claim.is_void


def test_professional_claim_happy_path() -> None:
    claim = make_professional_claim()
    assert claim.claim_type == ClaimType.PROFESSIONAL


def test_claim_total_reconciles_with_lines() -> None:
    with pytest.raises(ValidationError, match="does not equal sum of line charges"):
        Claim(
            claim_id="SYN-837I-0001",
            claim_type=ClaimType.INSTITUTIONAL,
            total_charge=Decimal("999.99"),
            billing_provider=make_billing_provider(),
            attending_provider=make_attending_provider(),
            subscriber=make_subscriber(),
            payer=make_payer(),
            type_of_bill="0322",
            statement_period=DateRange(start=date(2026, 2, 1), end=date(2026, 2, 7)),
            lines=[make_institutional_line()],
        )


def test_claim_rejects_delimiter_in_id() -> None:
    with pytest.raises(ValidationError, match="delimiter characters"):
        make_institutional_claim(claim_id="BAD*ID")


def test_claim_line_numbers_must_be_contiguous() -> None:
    lines = [
        make_institutional_line(line_number=1, charge=Decimal("100.00")),
        make_institutional_line(line_number=3, charge=Decimal("50.00")),
    ]
    with pytest.raises(ValidationError, match="contiguous 1..N"):
        Claim(
            claim_id="SYN-837I-0002",
            claim_type=ClaimType.INSTITUTIONAL,
            total_charge=Decimal("150.00"),
            billing_provider=make_billing_provider(),
            attending_provider=make_attending_provider(),
            subscriber=make_subscriber(),
            payer=make_payer(),
            type_of_bill="0322",
            statement_period=DateRange(start=date(2026, 2, 1), end=date(2026, 2, 7)),
            lines=lines,
        )


def test_claim_line_type_must_match_claim_type() -> None:
    with pytest.raises(ValidationError, match="expected I to match claim_type"):
        Claim(
            claim_id="SYN-BAD",
            claim_type=ClaimType.INSTITUTIONAL,
            total_charge=Decimal("100.00"),
            billing_provider=make_billing_provider(),
            attending_provider=make_attending_provider(),
            subscriber=make_subscriber(),
            payer=make_payer(),
            type_of_bill="0322",
            statement_period=DateRange(start=date(2026, 2, 1), end=date(2026, 2, 7)),
            lines=[make_professional_line()],
        )


def test_institutional_claim_requires_type_of_bill() -> None:
    with pytest.raises(ValidationError, match="type_of_bill"):
        Claim(
            claim_id="SYN-837I-0003",
            claim_type=ClaimType.INSTITUTIONAL,
            total_charge=Decimal("150.00"),
            billing_provider=make_billing_provider(),
            attending_provider=make_attending_provider(),
            subscriber=make_subscriber(),
            payer=make_payer(),
            statement_period=DateRange(start=date(2026, 2, 1), end=date(2026, 2, 7)),
            lines=[make_institutional_line()],
        )


def test_institutional_claim_requires_attending_provider() -> None:
    with pytest.raises(ValidationError, match="attending_provider"):
        Claim(
            claim_id="SYN-837I-0004",
            claim_type=ClaimType.INSTITUTIONAL,
            total_charge=Decimal("150.00"),
            billing_provider=make_billing_provider(),
            subscriber=make_subscriber(),
            payer=make_payer(),
            type_of_bill="0322",
            statement_period=DateRange(start=date(2026, 2, 1), end=date(2026, 2, 7)),
            lines=[make_institutional_line()],
        )


def test_institutional_claim_requires_statement_period() -> None:
    with pytest.raises(ValidationError, match="statement_period"):
        Claim(
            claim_id="SYN-837I-0005",
            claim_type=ClaimType.INSTITUTIONAL,
            total_charge=Decimal("150.00"),
            billing_provider=make_billing_provider(),
            attending_provider=make_attending_provider(),
            subscriber=make_subscriber(),
            payer=make_payer(),
            type_of_bill="0322",
            lines=[make_institutional_line()],
        )


def test_professional_claim_requires_place_of_service() -> None:
    with pytest.raises(ValidationError, match="place_of_service"):
        Claim(
            claim_id="SYN-837P-0002",
            claim_type=ClaimType.PROFESSIONAL,
            total_charge=Decimal("95.00"),
            billing_provider=make_billing_provider(),
            subscriber=make_subscriber(),
            payer=make_payer(),
            lines=[make_professional_line()],
        )


def test_claim_requires_patient_when_subscriber_not_self() -> None:
    sub = make_subscriber(relationship=PatientRelationship.CHILD)
    with pytest.raises(ValidationError, match="patient is required"):
        Claim(
            claim_id="SYN-837P-PAT",
            claim_type=ClaimType.PROFESSIONAL,
            total_charge=Decimal("95.00"),
            billing_provider=make_billing_provider(),
            subscriber=sub,
            payer=make_payer(),
            place_of_service="11",
            lines=[make_professional_line()],
        )


def test_claim_with_patient_accepted_when_subscriber_not_self() -> None:
    sub = make_subscriber(relationship=PatientRelationship.CHILD)
    Claim(
        claim_id="SYN-837P-PAT-OK",
        claim_type=ClaimType.PROFESSIONAL,
        total_charge=Decimal("95.00"),
        billing_provider=make_billing_provider(),
        subscriber=sub,
        patient=make_patient(),
        payer=make_payer(),
        place_of_service="11",
        lines=[make_professional_line()],
    )


def test_claim_rejects_discharge_before_admission() -> None:
    with pytest.raises(ValidationError, match="discharge_date"):
        Claim(
            claim_id="SYN-DISCH-BAD",
            claim_type=ClaimType.INSTITUTIONAL,
            total_charge=Decimal("150.00"),
            billing_provider=make_billing_provider(),
            attending_provider=make_attending_provider(),
            subscriber=make_subscriber(),
            payer=make_payer(),
            type_of_bill="0322",
            statement_period=DateRange(start=date(2026, 2, 1), end=date(2026, 2, 10)),
            admission_date=date(2026, 2, 10),
            discharge_date=date(2026, 2, 1),
            lines=[make_institutional_line()],
        )


def test_claim_replacement_and_void_shortcuts() -> None:
    base = make_institutional_claim()
    data = base.model_dump()
    data["frequency_code"] = ClaimFrequencyCode.REPLACEMENT
    replacement = Claim(**data)
    assert replacement.is_replacement

    data["frequency_code"] = ClaimFrequencyCode.VOID
    void = Claim(**data)
    assert void.is_void


def test_claim_multi_line_totals_reconcile() -> None:
    lines = [
        make_institutional_line(line_number=1, charge=Decimal("100.00")),
        make_institutional_line(
            line_number=2,
            revenue_code="0450",
            charge=Decimal("225.75"),
        ),
    ]
    claim = make_institutional_claim(claim_id="SYN-837I-MULTI", lines=lines)
    assert claim.total_charge == Decimal("325.75")


def test_claim_decimal_rounding_two_places() -> None:
    """Line charges summing to a three-decimal value must equal two-decimal total."""

    # 100.001 + 200.002 = 300.003 rounded to 300.00 does not reconcile; library
    # enforces two-decimal precision at line charge level (PositiveMoneyAmount).
    with pytest.raises(ValidationError):
        make_institutional_line(charge=Decimal("100.001"))
