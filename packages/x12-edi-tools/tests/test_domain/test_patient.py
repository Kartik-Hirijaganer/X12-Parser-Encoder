"""Tests for domain.patient."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from x12_edi_tools.common.enums import GenderCode
from x12_edi_tools.domain.patient import (
    Patient,
    PatientAddress,
    PatientRelationship,
    Subscriber,
)


def test_subscriber_defaults_relationship_to_self() -> None:
    subscriber = Subscriber(
        first_name="Test",
        last_name="Subscriber",
        birth_date=date(1980, 1, 1),
        member_id="MEMBER001",
    )
    assert subscriber.relationship_to_insured == PatientRelationship.SELF
    assert subscriber.gender == GenderCode.UNKNOWN


def test_subscriber_rejects_blank_member_id() -> None:
    with pytest.raises(ValidationError):
        Subscriber(
            first_name="Test",
            last_name="Subscriber",
            birth_date=date(1980, 1, 1),
            member_id="   ",
        )


def test_subscriber_ssn_last_four_requires_digits() -> None:
    with pytest.raises(ValidationError):
        Subscriber(
            first_name="Test",
            last_name="Subscriber",
            birth_date=date(1980, 1, 1),
            member_id="MEMBER001",
            ssn_last_four="abcd",
        )
    sub = Subscriber(
        first_name="Test",
        last_name="Subscriber",
        birth_date=date(1980, 1, 1),
        member_id="MEMBER001",
        ssn_last_four="1234",
    )
    assert sub.ssn_last_four == "1234"


def test_patient_rejects_self_relationship() -> None:
    with pytest.raises(ValidationError):
        Patient(
            first_name="Dependent",
            last_name="Person",
            birth_date=date(2015, 6, 1),
            relationship_to_subscriber=PatientRelationship.SELF,
        )


def test_patient_accepts_non_self_relationship() -> None:
    patient = Patient(
        first_name="Dependent",
        last_name="Person",
        birth_date=date(2015, 6, 1),
        relationship_to_subscriber=PatientRelationship.CHILD,
    )
    assert patient.relationship_to_subscriber == PatientRelationship.CHILD


def test_patient_address_normalizes_state() -> None:
    addr = PatientAddress(
        address_line_1="123 Main",
        city="Washington",
        state="dc",
        postal_code="20001",
    )
    assert addr.state == "DC"
