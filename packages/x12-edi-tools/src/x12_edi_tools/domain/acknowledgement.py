"""Acknowledgement scaffolds covering TA1, 999, 824, and BRR.

This module deliberately ships as a *scaffold* — the transaction parsers
for TA1 / 999 / 824 / BRR land in a later phase. The shape defined here is
the projection those parsers will populate, and is kept stable so that
``POST /api/v1/acks/ingest`` (documented-but-501 in Phase 6) can carry a
real request schema from day one per CG Table 1 (DC Medicaid).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class AcknowledgementKind(StrEnum):
    """The four ack formats DC Medicaid emits (CG Table 1)."""

    TA1 = "TA1"
    FUNCTIONAL_999 = "999"
    APPLICATION_824 = "824"
    BUSINESS_REJECT_REPORT = "BRR"


class AcknowledgementStatus(StrEnum):
    """Normalized outcome across all four ack formats."""

    ACCEPTED = "accepted"
    ACCEPTED_WITH_ERRORS = "accepted_with_errors"
    REJECTED = "rejected"
    PARTIALLY_ACCEPTED = "partially_accepted"


class AcknowledgementError(BaseModel):
    """One reported defect inside an acknowledgement.

    Keeping this as a flat dataclass-style model means the same error type
    serves TA1 (envelope-level), 999 (transaction-level), 824 (application
    edit), and BRR (business-reject) without format-specific subclasses.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: Annotated[str, Field(min_length=1, max_length=16)]
    severity: str = Field(default="error", pattern="^(info|warning|error|fatal)$")
    message: Annotated[str, Field(min_length=1, max_length=255)]
    segment_id: str | None = Field(default=None, max_length=3)
    element_position: int | None = Field(default=None, ge=1)
    st_control_number: str | None = Field(default=None, max_length=15)
    reference: str | None = Field(default=None, max_length=80)


class Acknowledgement(BaseModel):
    """Generic acknowledgement projection.

    ``kind`` discriminates the source format; ``errors`` is flattened across
    all reported defects. Callers match remittance + ack flows by the
    ``(interchange_control_number, gs_control_number, st_control_numbers)``
    triple.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    kind: AcknowledgementKind
    status: AcknowledgementStatus
    received_at: datetime
    interchange_control_number: Annotated[str, Field(min_length=1, max_length=15)]
    gs_control_number: str | None = Field(default=None, max_length=15)
    st_control_numbers: list[str] = Field(default_factory=list)
    errors: list[AcknowledgementError] = Field(default_factory=list)
    raw_document_id: str | None = Field(default=None, max_length=120)


__all__ = [
    "Acknowledgement",
    "AcknowledgementError",
    "AcknowledgementKind",
    "AcknowledgementStatus",
]
