"""Adjustment domain objects shared by 837 and 835 flows.

CAS adjustment groups (CO/PR/OA/PI/CR) convey why a payer reduced the paid
amount below the billed amount. CARC (Claim Adjustment Reason Code) values
live under the X12 code set 139; RARC (Remittance Advice Remark Code) values
live under code set 411 and always appear alongside a CARC via MIA/MOA or
LQ segments.
"""

from __future__ import annotations

import re
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Shared money / quantity aliases (duplicated here rather than imported from
# domain.claim to avoid a cross-file import cycle if 837 work changes claim
# definitions mid-phase).
# ---------------------------------------------------------------------------

AdjustmentAmount = Annotated[
    Decimal,
    Field(
        max_digits=18,
        decimal_places=2,
        ge=Decimal("-99999999999999.99"),
        le=Decimal("99999999999999.99"),
    ),
]
AdjustmentQuantity = Annotated[Decimal, Field(max_digits=15, decimal_places=3)]


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AdjustmentGroupCode(StrEnum):
    """CAS01 / CAS04 / … adjustment group qualifier (X12 code set 1032)."""

    CONTRACTUAL_OBLIGATIONS = "CO"
    CORRECTION_AND_REVERSAL = "CR"
    OTHER_ADJUSTMENTS = "OA"
    PAYER_INITIATED = "PI"
    PATIENT_RESPONSIBILITY = "PR"


class RemarkCodeType(StrEnum):
    """Internal discriminator for CARC vs. RARC in :class:`CARCRARCMessage`."""

    CARC = "CARC"
    RARC = "RARC"


# ---------------------------------------------------------------------------
# Code-format helpers
# ---------------------------------------------------------------------------

_CARC_RE = re.compile(r"^[A-Za-z]?\d{1,4}[A-Za-z]?$")
"""CARC values are 1-4 digits, optionally prefixed or suffixed with a letter.

Examples: ``45``, ``A1``, ``B13``, ``W1``, ``253``.
"""

_RARC_RE = re.compile(r"^(N\d{1,3}|M\d{1,3}|MA\d{1,3})$")
"""RARC values match the ``N###``, ``M###``, or ``MA###`` patterns.

Examples: ``N130``, ``M86``, ``MA04``.
"""


class ClaimAdjustmentReasonCode(BaseModel):
    """CARC — X12 code set 139 (Claim Adjustment Reason Codes)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid", frozen=True)

    value: Annotated[str, Field(min_length=1, max_length=5)]

    @field_validator("value")
    @classmethod
    def _validate_format(cls, value: str) -> str:
        value = value.upper()
        if not _CARC_RE.match(value):
            raise ValueError(f"CARC {value!r} is not a valid Claim Adjustment Reason Code format")
        return value


class RemittanceAdviceRemarkCode(BaseModel):
    """RARC — X12 code set 411 (Remittance Advice Remark Codes)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid", frozen=True)

    value: Annotated[str, Field(min_length=2, max_length=5)]

    @field_validator("value")
    @classmethod
    def _validate_format(cls, value: str) -> str:
        value = value.upper()
        if not _RARC_RE.match(value):
            raise ValueError(f"RARC {value!r} is not a valid Remittance Advice Remark Code format")
        return value


class CARCRARCMessage(BaseModel):
    """Associates a CARC or RARC code with a human-readable description.

    Used when projecting 835 CAS groups into a caller-friendly denial/remark
    representation. The payer/library never ships the full CMS code table
    inline; descriptions are supplied by the caller or fetched from the CMS
    crosswalk at runtime.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: str = Field(min_length=1, max_length=5)
    description: str = Field(min_length=1, max_length=255)
    code_type: RemarkCodeType

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        return value.upper()


# ---------------------------------------------------------------------------
# Adjustment
# ---------------------------------------------------------------------------


class Adjustment(BaseModel):
    """One CAS element triplet (reason, amount, quantity) within a group.

    A single CAS segment repeats this triplet up to six times; callers
    represent that by supplying a list of :class:`Adjustment` objects all
    sharing the same ``group_code``.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    group_code: AdjustmentGroupCode
    reason_code: ClaimAdjustmentReasonCode
    amount: AdjustmentAmount
    quantity: AdjustmentQuantity | None = None
    remark_codes: list[RemittanceAdviceRemarkCode] = Field(default_factory=list)


__all__ = [
    "Adjustment",
    "AdjustmentAmount",
    "AdjustmentGroupCode",
    "AdjustmentQuantity",
    "CARCRARCMessage",
    "ClaimAdjustmentReasonCode",
    "RemarkCodeType",
    "RemittanceAdviceRemarkCode",
]
