"""Tests for domain.audit."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from x12_edi_tools.domain.audit import (
    AuditOperation,
    AuditOutcome,
    TransactionAudit,
)
from x12_edi_tools.domain.submission_batch import TransactionType


def _base_audit_kwargs() -> dict[str, object]:
    started = datetime(2026, 4, 19, 12, 0, 0, tzinfo=UTC)
    completed = started + timedelta(milliseconds=250)
    return {
        "correlation_id": "syn-corr-0001",
        "operation": AuditOperation.BUILD,
        "transaction_type": TransactionType.CLAIM_837I,
        "outcome": AuditOutcome.SUCCESS,
        "started_at": started,
        "completed_at": completed,
        "duration_ms": 250,
        "library_version": "0.2.0",
    }


def test_transaction_audit_happy_path() -> None:
    audit = TransactionAudit(**_base_audit_kwargs())
    assert audit.operation == AuditOperation.BUILD
    assert audit.outcome == AuditOutcome.SUCCESS
    assert audit.transaction_count == 0


def test_transaction_audit_rejects_negative_duration() -> None:
    kwargs = _base_audit_kwargs()
    kwargs["duration_ms"] = -1
    with pytest.raises(ValidationError):
        TransactionAudit(**kwargs)


def test_transaction_audit_rejects_inverted_timestamps() -> None:
    kwargs = _base_audit_kwargs()
    kwargs["completed_at"] = kwargs["started_at"]  # type: ignore[assignment]
    kwargs["started_at"] = datetime(2026, 4, 19, 12, 0, 1, tzinfo=UTC)
    with pytest.raises(ValidationError, match="completed_at"):
        TransactionAudit(**kwargs)


def test_transaction_audit_flags_duration_mismatch() -> None:
    kwargs = _base_audit_kwargs()
    kwargs["duration_ms"] = 10_000  # 10s, but only 250ms elapsed
    with pytest.raises(ValidationError, match="duration_ms"):
        TransactionAudit(**kwargs)


@pytest.mark.parametrize("correlation_id", ["bad id!", "with space", "emoji🙂"])
def test_transaction_audit_rejects_bad_correlation_id(correlation_id: str) -> None:
    kwargs = _base_audit_kwargs()
    kwargs["correlation_id"] = correlation_id
    with pytest.raises(ValidationError, match="correlation_id"):
        TransactionAudit(**kwargs)


def test_transaction_audit_permits_dash_and_underscore() -> None:
    kwargs = _base_audit_kwargs()
    kwargs["correlation_id"] = "syn_corr-001"
    audit = TransactionAudit(**kwargs)
    assert audit.correlation_id == "syn_corr-001"


def test_transaction_audit_aggregated_counts() -> None:
    kwargs = _base_audit_kwargs()
    kwargs.update(
        transaction_count=5,
        segment_count=250,
        claim_count=5,
        validation_error_count=0,
        validation_warning_count=2,
        validation_info_count=4,
        payer_profile="dc_medicaid",
    )
    audit = TransactionAudit(**kwargs)
    assert audit.segment_count == 250
    assert audit.payer_profile == "dc_medicaid"


def test_audit_outcome_values() -> None:
    assert {o.value for o in AuditOutcome} == {"success", "partial", "failed"}


def test_audit_operation_values() -> None:
    assert {o.value for o in AuditOperation} == {
        "build",
        "parse",
        "validate",
        "encode",
        "read",
    }
