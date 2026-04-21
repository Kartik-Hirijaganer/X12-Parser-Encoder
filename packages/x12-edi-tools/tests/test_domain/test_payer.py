"""Tests for domain.payer."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from x12_edi_tools.domain.payer import (
    Payer,
    PayerAddress,
    PayerIdQualifier,
    PayerResponsibility,
)


def test_payer_address_uppercases_state() -> None:
    address = PayerAddress(
        address_line_1="1 Main St",
        city="Washington",
        state="dc",
        postal_code="20001",
    )
    assert address.state == "DC"


def test_payer_accepts_minimum_required_fields() -> None:
    payer = Payer(name="DC Medicaid", payer_id="DCMEDICAID")
    assert payer.responsibility == PayerResponsibility.PRIMARY
    assert payer.payer_id_qualifier == PayerIdQualifier.PAYOR_IDENTIFICATION
    assert payer.claim_filing_indicator_code == "MC"


def test_payer_rejects_blank_id() -> None:
    with pytest.raises(ValidationError):
        Payer(name="DC Medicaid", payer_id="   ")


def test_payer_with_address_validates_nested() -> None:
    payer = Payer(
        name="DC Medicaid",
        payer_id="DCMEDICAID",
        address=PayerAddress(
            address_line_1="441 4th St NW",
            city="Washington",
            state="DC",
            postal_code="20001",
        ),
        contact_name="Claims Intake",
        contact_phone="2025551234",
    )
    assert payer.address is not None
    assert payer.address.state == "DC"


def test_payer_responsibility_enum_roundtrip() -> None:
    assert PayerResponsibility("P") == PayerResponsibility.PRIMARY
    assert PayerResponsibility("S") == PayerResponsibility.SECONDARY
    assert PayerResponsibility("T") == PayerResponsibility.TERTIARY
