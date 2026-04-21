"""Tests for domain.submission_batch."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from x12_edi_tools.domain.submission_batch import (
    ArchiveEntry,
    ControlNumbers,
    SubmissionBatch,
    TransactionType,
)

from ._builders import (
    make_archive_entry,
    make_control_numbers,
    make_submission_batch,
)


def test_control_numbers_rejects_non_digit_isa() -> None:
    with pytest.raises(ValidationError):
        ControlNumbers(isa="abc", gs="0001")


def test_control_numbers_rejects_non_digit_gs() -> None:
    with pytest.raises(ValidationError):
        ControlNumbers(isa="000000001", gs="abc")


def test_control_numbers_validates_st_map() -> None:
    with pytest.raises(ValidationError):
        ControlNumbers(isa="000000001", gs="0001", st={"claim": "notnum"})
    with pytest.raises(ValidationError):
        ControlNumbers(isa="000000001", gs="0001", st={"": "0001"})


def test_control_numbers_frozen() -> None:
    control = make_control_numbers()
    with pytest.raises(ValidationError):
        control.isa = "999999999"  # type: ignore[misc]


def test_archive_entry_requires_hex_digest() -> None:
    with pytest.raises(ValidationError):
        ArchiveEntry(
            filename="CLM.edi",
            transaction_type=TransactionType.CLAIM_837I,
            content_hash="zzzz" * 16,
            size_bytes=10,
            created_at=datetime(2026, 4, 19, 12, 0, tzinfo=UTC),
            interchange_control_number="000000001",
        )


def test_archive_entry_lowercases_hex_digest() -> None:
    entry = make_archive_entry()
    assert entry.content_hash == "a" * 64
    assert entry.content_hash_algorithm == "sha256"


def test_submission_batch_happy_path() -> None:
    batch = make_submission_batch()
    assert batch.claim_count == 1
    assert batch.transaction_type == TransactionType.CLAIM_837I
    assert len(batch.archive_entries) == 1


def test_submission_batch_archive_type_must_match() -> None:
    control = make_control_numbers()
    bad_entry = make_archive_entry(
        transaction_type=TransactionType.CLAIM_837P,
        interchange=control.isa,
    )
    with pytest.raises(ValidationError, match="transaction_type"):
        SubmissionBatch(
            batch_id="BATCH",
            transaction_type=TransactionType.CLAIM_837I,
            control_numbers=control,
            created_at=datetime(2026, 4, 19, 12, 0, tzinfo=UTC),
            transaction_count=1,
            claim_count=1,
            total_charge_amount=Decimal("100.00"),
            archive_entries=[bad_entry],
        )


def test_submission_batch_archive_interchange_must_match() -> None:
    control = make_control_numbers()
    mismatched_entry = make_archive_entry(interchange="999999999")
    with pytest.raises(ValidationError, match="interchange_control_number"):
        SubmissionBatch(
            batch_id="BATCH",
            transaction_type=TransactionType.CLAIM_837I,
            control_numbers=control,
            created_at=datetime(2026, 4, 19, 12, 0, tzinfo=UTC),
            transaction_count=1,
            claim_count=1,
            total_charge_amount=Decimal("100.00"),
            archive_entries=[mismatched_entry],
        )


def test_submission_batch_without_archive_entries() -> None:
    control = make_control_numbers()
    batch = SubmissionBatch(
        batch_id="BATCH",
        transaction_type=TransactionType.CLAIM_837I,
        control_numbers=control,
        created_at=datetime(2026, 4, 19, 12, 0, tzinfo=UTC),
        transaction_count=0,
        claim_count=0,
    )
    assert batch.total_charge_amount == Decimal("0")
    assert batch.archive_entries == []


def test_transaction_type_values() -> None:
    assert TransactionType("270").value == "270"
    assert TransactionType("271").value == "271"
    assert TransactionType("837I").value == "837I"
    assert TransactionType("837P").value == "837P"
    assert TransactionType("835").value == "835"
