"""Tests for domain.adjustment."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from x12_edi_tools.domain.adjustment import (
    Adjustment,
    AdjustmentGroupCode,
    CARCRARCMessage,
    ClaimAdjustmentReasonCode,
    RemarkCodeType,
    RemittanceAdviceRemarkCode,
)

# --------- CARC --------------------------------------------------------------


@pytest.mark.parametrize("value", ["45", "A1", "B13", "W1", "253", "n3"])
def test_carc_accepts_valid_formats(value: str) -> None:
    code = ClaimAdjustmentReasonCode(value=value)
    assert code.value == value.upper()


@pytest.mark.parametrize("value", ["", "45A9", "!!"])
def test_carc_rejects_invalid_formats(value: str) -> None:
    with pytest.raises(ValidationError):
        ClaimAdjustmentReasonCode(value=value)


# --------- RARC --------------------------------------------------------------


@pytest.mark.parametrize("value", ["N130", "M86", "MA04", "n130"])
def test_rarc_accepts_valid_formats(value: str) -> None:
    code = RemittanceAdviceRemarkCode(value=value)
    assert code.value == value.upper()


@pytest.mark.parametrize("value", ["P1", "X99", "130"])
def test_rarc_rejects_invalid_formats(value: str) -> None:
    with pytest.raises(ValidationError):
        RemittanceAdviceRemarkCode(value=value)


# --------- CARCRARCMessage ---------------------------------------------------


def test_carc_rarc_message_uppercases_code() -> None:
    msg = CARCRARCMessage(
        code="n130",
        description="Consultant services are not covered",
        code_type=RemarkCodeType.RARC,
    )
    assert msg.code == "N130"
    assert msg.code_type == RemarkCodeType.RARC


# --------- Adjustment -------------------------------------------------------


def test_adjustment_full_shape() -> None:
    adjustment = Adjustment(
        group_code=AdjustmentGroupCode.CONTRACTUAL_OBLIGATIONS,
        reason_code=ClaimAdjustmentReasonCode(value="45"),
        amount=Decimal("15.00"),
        quantity=Decimal("1"),
        remark_codes=[RemittanceAdviceRemarkCode(value="N130")],
    )
    assert adjustment.group_code == AdjustmentGroupCode.CONTRACTUAL_OBLIGATIONS
    assert adjustment.reason_code.value == "45"
    assert len(adjustment.remark_codes) == 1


def test_adjustment_rejects_non_decimal_money() -> None:
    with pytest.raises(ValidationError):
        Adjustment(
            group_code=AdjustmentGroupCode.PATIENT_RESPONSIBILITY,
            reason_code=ClaimAdjustmentReasonCode(value="1"),
            amount=Decimal("1.005"),  # three decimals
        )


def test_carc_rarc_code_enum_roundtrip() -> None:
    assert RemarkCodeType("CARC") == RemarkCodeType.CARC
    assert RemarkCodeType("RARC") == RemarkCodeType.RARC
