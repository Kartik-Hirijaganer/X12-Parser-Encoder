"""Tests for domain.acknowledgement scaffolding."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from x12_edi_tools.domain.acknowledgement import (
    Acknowledgement,
    AcknowledgementError,
    AcknowledgementKind,
    AcknowledgementStatus,
)


def test_acknowledgement_error_defaults_to_error_severity() -> None:
    err = AcknowledgementError(code="E001", message="Bad segment count")
    assert err.severity == "error"


@pytest.mark.parametrize("severity", ["info", "warning", "error", "fatal"])
def test_acknowledgement_error_severity_values(severity: str) -> None:
    err = AcknowledgementError(code="E001", message="m", severity=severity)
    assert err.severity == severity


def test_acknowledgement_error_rejects_unknown_severity() -> None:
    with pytest.raises(ValidationError):
        AcknowledgementError(code="E001", message="m", severity="critical")


def test_acknowledgement_kind_enum_values() -> None:
    assert AcknowledgementKind("TA1") == AcknowledgementKind.TA1
    assert AcknowledgementKind("999") == AcknowledgementKind.FUNCTIONAL_999
    assert AcknowledgementKind("824") == AcknowledgementKind.APPLICATION_824
    assert AcknowledgementKind("BRR") == AcknowledgementKind.BUSINESS_REJECT_REPORT


def test_acknowledgement_roundtrip() -> None:
    ack = Acknowledgement(
        kind=AcknowledgementKind.FUNCTIONAL_999,
        status=AcknowledgementStatus.ACCEPTED_WITH_ERRORS,
        received_at=datetime(2026, 4, 19, 12, 0, tzinfo=UTC),
        interchange_control_number="000000001",
        gs_control_number="0001",
        st_control_numbers=["0001", "0002"],
        errors=[
            AcknowledgementError(
                code="IK304",
                message="Missing required element",
                segment_id="NM1",
                element_position=3,
                st_control_number="0001",
            ),
        ],
    )
    assert ack.kind == AcknowledgementKind.FUNCTIONAL_999
    assert len(ack.errors) == 1
    assert ack.errors[0].segment_id == "NM1"


def test_acknowledgement_status_enum_values() -> None:
    values = {status.value for status in AcknowledgementStatus}
    assert values == {
        "accepted",
        "accepted_with_errors",
        "rejected",
        "partially_accepted",
    }
