"""Synthetic-data builders shared across the test_domain suite.

Every identifier uses the ``SYNTHETIC_*`` marker or a well-known test-range
value so the conftest safety sweep for PHI passes. NPIs are computed against
the CMS Luhn check and come from a fixed pool.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from x12_edi_tools.common.enums import GenderCode
from x12_edi_tools.domain.adjustment import (
    Adjustment,
    AdjustmentGroupCode,
    ClaimAdjustmentReasonCode,
)
from x12_edi_tools.domain.claim import (
    BenefitsAssignmentCode,
    Claim,
    ClaimFrequencyCode,
    ClaimLine,
    ClaimType,
    DateRange,
)
from x12_edi_tools.domain.patient import (
    Patient,
    PatientAddress,
    PatientRelationship,
    Subscriber,
)
from x12_edi_tools.domain.payer import Payer, PayerAddress, PayerResponsibility
from x12_edi_tools.domain.provider import (
    AttendingProvider,
    BillingProvider,
    ProviderAddress,
    ProviderEntityType,
    RenderingProvider,
)
from x12_edi_tools.domain.remittance import (
    ClaimFilingIndicator,
    ClaimStatusCode,
    PaymentMethodCode,
    Remittance,
    RemittanceClaim,
    RemittancePayment,
    RemittanceServiceLine,
)
from x12_edi_tools.domain.submission_batch import (
    ArchiveEntry,
    ControlNumbers,
    SubmissionBatch,
    TransactionType,
)

# Pre-computed Luhn-valid synthetic NPIs (body "80840" + first 9 digits).
SYNTHETIC_NPI_BILLING = "1234567893"
SYNTHETIC_NPI_RENDERING = "9876543213"
SYNTHETIC_NPI_ATTENDING = "1111111112"


def make_provider_address() -> ProviderAddress:
    return ProviderAddress(
        address_line_1="100 Test Clinic Way",
        city="Washington",
        state="DC",
        postal_code="20001",
    )


def make_billing_provider(
    *,
    entity_type: ProviderEntityType = ProviderEntityType.NON_PERSON,
    npi: str = SYNTHETIC_NPI_BILLING,
) -> BillingProvider:
    kwargs: dict[str, object] = {
        "entity_type": entity_type,
        "npi": npi,
        "tax_id": "123456789",
        "tax_id_qualifier": "EI",
        "address": make_provider_address(),
    }
    if entity_type == ProviderEntityType.NON_PERSON:
        kwargs["organization_name"] = "Synthetic Home Health LLC"
    else:
        kwargs["first_name"] = "Jordan"
        kwargs["last_name"] = "Provider"
    return BillingProvider(**kwargs)


def make_attending_provider() -> AttendingProvider:
    return AttendingProvider(
        entity_type=ProviderEntityType.PERSON,
        npi=SYNTHETIC_NPI_ATTENDING,
        first_name="Alex",
        last_name="Clinician",
    )


def make_rendering_provider() -> RenderingProvider:
    return RenderingProvider(
        entity_type=ProviderEntityType.PERSON,
        npi=SYNTHETIC_NPI_RENDERING,
        first_name="Casey",
        last_name="Therapist",
    )


def make_patient_address() -> PatientAddress:
    return PatientAddress(
        address_line_1="200 Test Patient St",
        city="Washington",
        state="DC",
        postal_code="20002",
    )


def make_subscriber(
    *,
    relationship: PatientRelationship = PatientRelationship.SELF,
    member_id: str = "SYNTHETIC_MEMBER_001",
) -> Subscriber:
    return Subscriber(
        first_name="Test",
        last_name="Subscriber",
        birth_date=date(1970, 1, 1),
        gender=GenderCode.UNKNOWN,
        member_id=member_id,
        relationship_to_insured=relationship,
        address=make_patient_address(),
    )


def make_patient() -> Patient:
    return Patient(
        first_name="Dependent",
        last_name="Subscriber",
        birth_date=date(2015, 6, 1),
        gender=GenderCode.UNKNOWN,
        relationship_to_subscriber=PatientRelationship.CHILD,
        address=make_patient_address(),
    )


def make_payer() -> Payer:
    return Payer(
        name="DC Medicaid",
        payer_id="DCMEDICAID",
        responsibility=PayerResponsibility.PRIMARY,
        claim_filing_indicator_code="MC",
        address=PayerAddress(
            address_line_1="441 4th St NW",
            city="Washington",
            state="DC",
            postal_code="20001",
        ),
    )


def make_institutional_line(
    *,
    line_number: int = 1,
    revenue_code: str = "0420",
    charge: Decimal = Decimal("150.00"),
) -> ClaimLine:
    return ClaimLine(
        line_number=line_number,
        line_type=ClaimType.INSTITUTIONAL,
        revenue_code=revenue_code,
        procedure_code="97110",
        procedure_code_qualifier="HC",
        charge_amount=charge,
        units=Decimal("1"),
        unit_basis="UN",
        service_date=date(2026, 2, 1),
        diagnosis_pointers=[1],
    )


def make_professional_line(
    *,
    line_number: int = 1,
    procedure_code: str = "99213",
    charge: Decimal = Decimal("95.00"),
) -> ClaimLine:
    return ClaimLine(
        line_number=line_number,
        line_type=ClaimType.PROFESSIONAL,
        procedure_code=procedure_code,
        procedure_code_qualifier="HC",
        charge_amount=charge,
        units=Decimal("1"),
        unit_basis="UN",
        service_date=date(2026, 2, 1),
        place_of_service="11",
        diagnosis_pointers=[1],
    )


def make_institutional_claim(
    *,
    claim_id: str = "SYN-837I-0001",
    lines: list[ClaimLine] | None = None,
) -> Claim:
    lines = lines or [make_institutional_line()]
    total = sum((line.charge_amount for line in lines), Decimal("0"))
    return Claim(
        claim_id=claim_id,
        claim_type=ClaimType.INSTITUTIONAL,
        total_charge=total,
        frequency_code=ClaimFrequencyCode.ORIGINAL,
        billing_provider=make_billing_provider(),
        attending_provider=make_attending_provider(),
        subscriber=make_subscriber(),
        payer=make_payer(),
        type_of_bill="0322",
        statement_period=DateRange(start=date(2026, 2, 1), end=date(2026, 2, 7)),
        admission_date=date(2026, 2, 1),
        patient_status_code="30",
        assignment_of_benefits=BenefitsAssignmentCode.YES,
        lines=lines,
    )


def make_professional_claim(
    *,
    claim_id: str = "SYN-837P-0001",
    lines: list[ClaimLine] | None = None,
) -> Claim:
    lines = lines or [make_professional_line()]
    total = sum((line.charge_amount for line in lines), Decimal("0"))
    return Claim(
        claim_id=claim_id,
        claim_type=ClaimType.PROFESSIONAL,
        total_charge=total,
        billing_provider=make_billing_provider(),
        subscriber=make_subscriber(),
        payer=make_payer(),
        place_of_service="11",
        lines=lines,
    )


def make_carc(value: str = "45") -> ClaimAdjustmentReasonCode:
    return ClaimAdjustmentReasonCode(value=value)


def make_adjustment(
    *,
    group: AdjustmentGroupCode = AdjustmentGroupCode.CONTRACTUAL_OBLIGATIONS,
    reason: str = "45",
    amount: Decimal = Decimal("10.00"),
) -> Adjustment:
    return Adjustment(
        group_code=group,
        reason_code=make_carc(reason),
        amount=amount,
    )


def make_remittance_payment(amount: Decimal = Decimal("90.00")) -> RemittancePayment:
    return RemittancePayment(
        payment_method=PaymentMethodCode.ACH,
        payment_amount=amount,
        payment_date=date(2026, 3, 1),
        trace_number="SYNTHETIC-TRACE-0001",
        credit_debit_flag="C",
    )


def make_remittance_service_line(
    *,
    charge: Decimal = Decimal("100.00"),
    paid: Decimal = Decimal("90.00"),
    procedure_code: str = "99213",
) -> RemittanceServiceLine:
    return RemittanceServiceLine(
        procedure_code=procedure_code,
        charge_amount=charge,
        paid_amount=paid,
        allowed_amount=paid,
        units_paid=Decimal("1"),
        units_billed=Decimal("1"),
    )


def make_remittance_claim(
    *,
    billed: Decimal = Decimal("100.00"),
    paid: Decimal = Decimal("90.00"),
    patient_resp: Decimal = Decimal("0"),
    adjustments: list[Adjustment] | None = None,
    service_lines: list[RemittanceServiceLine] | None = None,
) -> RemittanceClaim:
    adjustments = (
        adjustments
        if adjustments is not None
        else [make_adjustment(amount=billed - paid - patient_resp)]
    )
    return RemittanceClaim(
        patient_control_number="SYN-CLAIM-001",
        status_code=ClaimStatusCode.PROCESSED_AS_PRIMARY,
        billed_amount=billed,
        paid_amount=paid,
        patient_responsibility=patient_resp,
        claim_filing_indicator=ClaimFilingIndicator.MEDICAID,
        claim_adjustments=adjustments,
        service_lines=service_lines or [make_remittance_service_line()],
    )


def make_remittance() -> Remittance:
    return Remittance(
        transaction_set_control_number="0001",
        payer_identifier="DCMEDICAID",
        payer_name="DC Medicaid",
        payee_identifier=SYNTHETIC_NPI_BILLING,
        payee_name="Synthetic Home Health LLC",
        production_date=date(2026, 3, 1),
        payment=make_remittance_payment(),
        claims=[make_remittance_claim()],
    )


def make_control_numbers() -> ControlNumbers:
    return ControlNumbers(
        isa="000000001",
        gs="0001",
        st={"SYN-837I-0001": "0001"},
    )


def make_archive_entry(
    *,
    transaction_type: TransactionType = TransactionType.CLAIM_837I,
    interchange: str = "000000001",
) -> ArchiveEntry:
    return ArchiveEntry(
        filename="CLM-SYN-001-20260419.edi",
        transaction_type=transaction_type,
        content_hash="a" * 64,
        size_bytes=1024,
        created_at=datetime(2026, 4, 19, 12, 0, tzinfo=UTC),
        interchange_control_number=interchange,
    )


def make_submission_batch() -> SubmissionBatch:
    control = make_control_numbers()
    return SubmissionBatch(
        batch_id="SYN-BATCH-0001",
        transaction_type=TransactionType.CLAIM_837I,
        control_numbers=control,
        created_at=datetime(2026, 4, 19, 12, 0, tzinfo=UTC),
        transaction_count=1,
        claim_count=1,
        total_charge_amount=Decimal("150.00"),
        archive_entries=[
            make_archive_entry(interchange=control.isa),
        ],
        correlation_id="synthetic-corr-0001",
    )
