"""Non-PHI audit record for a build or parse operation.

``TransactionAudit`` is what the library returns to observability sinks.
It intentionally excludes raw payloads, patient names, member identifiers,
and filenames — only counts, durations, status, and correlation IDs. This
mirrors the rule in ``_logging.build_log_extra`` and the safety guidance
in ``CLAUDE.md``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from x12_edi_tools.domain.submission_batch import TransactionType


class AuditOutcome(StrEnum):
    """High-level disposition of a build/parse operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class AuditOperation(StrEnum):
    """Which side of the library pipeline produced this audit record."""

    BUILD = "build"
    PARSE = "parse"
    VALIDATE = "validate"
    ENCODE = "encode"
    READ = "read"


class TransactionAudit(BaseModel):
    """Observability record for a single library invocation.

    Guaranteed non-PHI. Reviewer gate: every field here must be safe to
    emit into application logs without redaction. If a future reviewer
    feels tempted to add ``filename``, ``member_id``, or ``raw_segment``,
    the answer is no — add it to a caller-owned record instead.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    correlation_id: Annotated[str, Field(min_length=1, max_length=64)]
    operation: AuditOperation
    transaction_type: TransactionType
    outcome: AuditOutcome

    started_at: datetime
    completed_at: datetime
    duration_ms: int = Field(ge=0)

    transaction_count: int = Field(default=0, ge=0)
    segment_count: int = Field(default=0, ge=0)
    claim_count: int = Field(default=0, ge=0)

    validation_error_count: int = Field(default=0, ge=0)
    validation_warning_count: int = Field(default=0, ge=0)
    validation_info_count: int = Field(default=0, ge=0)

    library_version: Annotated[str, Field(min_length=1, max_length=32)]
    payer_profile: str | None = Field(default=None, max_length=64)

    @field_validator("correlation_id")
    @classmethod
    def _correlation_ascii(cls, value: str) -> str:
        if not value.isascii() or not value.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "correlation_id must be ASCII alphanumeric (dashes / underscores allowed)"
            )
        return value

    @model_validator(mode="after")
    def _temporal_ordering(self) -> TransactionAudit:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must not precede started_at")
        measured = int((self.completed_at - self.started_at).total_seconds() * 1000)
        if self.duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")
        if measured > 0 and abs(measured - self.duration_ms) > 2000:
            raise ValueError(
                "duration_ms must be consistent with started_at/completed_at "
                "(tolerance 2s)"
            )
        return self


__all__ = [
    "AuditOperation",
    "AuditOutcome",
    "TransactionAudit",
]
