"""Submission batch domain objects.

Represents what a caller needs to record after building a claim batch: the
per-envelope control numbers for their outbound ledger, an archive manifest
describing the wire-format artifact(s), and summary totals (counts only —
no PHI) useful for observability.

The library itself remains stateless: builders return these objects so the
caller can persist them in their own store.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TransactionType(StrEnum):
    """Transaction family identifiers used in submission batches."""

    ELIGIBILITY_270 = "270"
    ELIGIBILITY_271 = "271"
    CLAIM_837I = "837I"
    CLAIM_837P = "837P"
    REMITTANCE_835 = "835"


class ControlNumbers(BaseModel):
    """Per-envelope + per-transaction control numbers produced by a build.

    ``isa`` is the ISA13 interchange control number. ``gs`` is the GS06
    functional-group control number. ``st`` maps each ST02 control number
    to its claim identifier so callers can cross-reference remittance
    returns back to the submission without holding on to the raw X12.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid", frozen=True)

    isa: Annotated[str, Field(min_length=1, max_length=9)]
    gs: Annotated[str, Field(min_length=1, max_length=9)]
    st: dict[str, str] = Field(default_factory=dict)

    @field_validator("isa", "gs")
    @classmethod
    def _digits_only(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("control numbers must be numeric strings")
        return value

    @field_validator("st")
    @classmethod
    def _st_values_numeric(cls, value: dict[str, str]) -> dict[str, str]:
        for claim_id, control in value.items():
            if not claim_id:
                raise ValueError("ST control-number map key must not be empty")
            if not control.isdigit():
                raise ValueError(
                    f"ST control number for {claim_id!r} must be a numeric string"
                )
        return value


class ArchiveEntry(BaseModel):
    """Manifest record describing one serialized X12 artifact.

    Callers write the raw payload to their own storage (S3, local disk,
    etc.); the library only produces the metadata needed to track that
    payload. ``filename`` follows the CG A.4 template when a DC Medicaid
    profile supplies one; otherwise it is a caller-chosen identifier.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    filename: Annotated[str, Field(min_length=1, max_length=255)]
    transaction_type: TransactionType
    content_hash: Annotated[str, Field(min_length=32, max_length=128)]
    content_hash_algorithm: Annotated[str, Field(min_length=2, max_length=16)] = "sha256"
    size_bytes: int = Field(ge=0)
    created_at: datetime
    interchange_control_number: Annotated[str, Field(min_length=1, max_length=9)]

    @field_validator("content_hash")
    @classmethod
    def _hash_hex(cls, value: str) -> str:
        value = value.lower()
        if not all(ch in "0123456789abcdef" for ch in value):
            raise ValueError("content_hash must be a lowercase hex digest")
        return value


class SubmissionBatch(BaseModel):
    """Envelope-level manifest returned from a build.

    Carries everything a caller needs to reconcile against subsequent
    acknowledgements and remittance: control numbers, counts, totals, and
    archive pointers. No PHI / no raw payloads.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    batch_id: Annotated[str, Field(min_length=1, max_length=64)]
    transaction_type: TransactionType
    control_numbers: ControlNumbers
    created_at: datetime
    transaction_count: int = Field(ge=0)
    claim_count: int = Field(ge=0)
    total_charge_amount: Annotated[
        Decimal,
        Field(
            max_digits=20,
            decimal_places=2,
            ge=Decimal("0"),
        ),
    ] = Decimal("0")
    archive_entries: list[ArchiveEntry] = Field(default_factory=list)
    correlation_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _archive_matches_type(self) -> SubmissionBatch:
        for entry in self.archive_entries:
            if entry.transaction_type != self.transaction_type:
                raise ValueError(
                    "archive_entries transaction_type must match the batch "
                    "transaction_type"
                )
            if entry.interchange_control_number != self.control_numbers.isa:
                raise ValueError(
                    "archive_entries interchange_control_number must match "
                    "control_numbers.isa"
                )
        return self


__all__ = [
    "ArchiveEntry",
    "ControlNumbers",
    "SubmissionBatch",
    "TransactionType",
]
