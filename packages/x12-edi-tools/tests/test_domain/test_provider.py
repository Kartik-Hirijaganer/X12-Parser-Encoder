"""Tests for domain.provider."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from x12_edi_tools.domain.provider import (
    AttendingProvider,
    BillingProvider,
    ProviderAddress,
    ProviderEntityType,
    ProviderRole,
    ReferringProvider,
    RenderingProvider,
    ServiceFacility,
    validate_npi,
)

from ._builders import (
    SYNTHETIC_NPI_ATTENDING,
    SYNTHETIC_NPI_BILLING,
    SYNTHETIC_NPI_RENDERING,
    make_billing_provider,
    make_provider_address,
)


def test_validate_npi_accepts_valid_value() -> None:
    assert validate_npi(SYNTHETIC_NPI_BILLING) == SYNTHETIC_NPI_BILLING


@pytest.mark.parametrize(
    "bad_value, expected_msg",
    [
        ("12345", "must be exactly 10 digits"),
        ("abcdefghij", "must be exactly 10 digits"),
        ("1234567890", "fails the CMS Luhn checksum"),
    ],
)
def test_validate_npi_rejects_bad_values(bad_value: str, expected_msg: str) -> None:
    with pytest.raises(ValueError, match=expected_msg):
        validate_npi(bad_value)


def test_billing_provider_organization_path() -> None:
    provider = make_billing_provider(entity_type=ProviderEntityType.NON_PERSON)
    assert provider.organization_name is not None
    assert provider.role == ProviderRole.BILLING
    assert provider.tax_id_qualifier == "EI"


def test_billing_provider_person_path_requires_first_last() -> None:
    with pytest.raises(ValidationError, match="first_name and last_name"):
        BillingProvider(
            entity_type=ProviderEntityType.PERSON,
            npi=SYNTHETIC_NPI_BILLING,
            tax_id="123456789",
            address=make_provider_address(),
        )


def test_billing_provider_non_person_requires_organization() -> None:
    with pytest.raises(ValidationError, match="organization_name"):
        BillingProvider(
            entity_type=ProviderEntityType.NON_PERSON,
            npi=SYNTHETIC_NPI_BILLING,
            tax_id="123456789",
            address=make_provider_address(),
        )


def test_billing_provider_rejects_unknown_tax_qualifier() -> None:
    with pytest.raises(ValidationError, match="tax_id_qualifier"):
        BillingProvider(
            entity_type=ProviderEntityType.NON_PERSON,
            organization_name="Test",
            npi=SYNTHETIC_NPI_BILLING,
            tax_id="123456789",
            tax_id_qualifier="XX",
            address=make_provider_address(),
        )


def test_rendering_and_attending_roles_default_correctly() -> None:
    rendering = RenderingProvider(
        entity_type=ProviderEntityType.PERSON,
        npi=SYNTHETIC_NPI_RENDERING,
        first_name="Casey",
        last_name="Therapist",
    )
    assert rendering.role == ProviderRole.RENDERING
    attending = AttendingProvider(
        entity_type=ProviderEntityType.PERSON,
        npi=SYNTHETIC_NPI_ATTENDING,
        first_name="Alex",
        last_name="Doctor",
    )
    assert attending.role == ProviderRole.ATTENDING


def test_referring_provider_default_role() -> None:
    provider = ReferringProvider(
        entity_type=ProviderEntityType.PERSON,
        npi=SYNTHETIC_NPI_RENDERING,
        first_name="Jamie",
        last_name="Referrer",
    )
    assert provider.role == ProviderRole.REFERRING


def test_service_facility_constructs_cleanly() -> None:
    facility = ServiceFacility(
        name="Synthetic Outpatient Clinic",
        npi=SYNTHETIC_NPI_RENDERING,
        address=make_provider_address(),
    )
    assert facility.role == ProviderRole.SERVICE_FACILITY


def test_service_facility_rejects_bad_npi() -> None:
    with pytest.raises(ValidationError):
        ServiceFacility(
            name="Synthetic Clinic",
            npi="1234567890",  # bad checksum
            address=make_provider_address(),
        )


def test_provider_address_uppercases_state() -> None:
    addr = ProviderAddress(
        address_line_1="1 Main",
        city="Washington",
        state="dc",
        postal_code="20001",
    )
    assert addr.state == "DC"
