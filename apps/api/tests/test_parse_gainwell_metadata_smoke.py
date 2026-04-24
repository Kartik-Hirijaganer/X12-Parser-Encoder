"""Opt-in smoke gate for the real April 22, 2026 Gainwell 271 response.

The source file can contain PHI, so this test only runs when X12_METADATA_DIR
points at a local metadata directory. The committed redacted fixture remains the
regular CI gate.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.metadata_smoke

REAL_271_FILENAME = "Upload-271-Response-DCTPID000783-20260422-4251655-005010X279A1.edi"
EXPECTED_TRANSACTIONS = 153
EXPECTED_AAA_71 = 4
EXPECTED_AAA_73 = 9
EXPECTED_AAA_75 = 0
EXPECTED_ERROR = EXPECTED_AAA_71 + EXPECTED_AAA_73
EXPECTED_INACTIVE = 0
EXPECTED_NOT_FOUND = 0
EXPECTED_ACTIVE_OR_UNKNOWN = EXPECTED_TRANSACTIONS - EXPECTED_ERROR
MAX_EXPECTED_UNKNOWN = 4


def _metadata_271_path() -> Path:
    metadata_dir = os.environ.get("X12_METADATA_DIR")
    if metadata_dir is None:
        pytest.skip("Set X12_METADATA_DIR to run the Gainwell real-file smoke test.")

    path = Path(metadata_dir).expanduser() / REAL_271_FILENAME
    if not path.is_file():
        pytest.skip(f"{REAL_271_FILENAME} is not present in X12_METADATA_DIR.")
    return path


def _aaa_reject_reason_counts(raw_x12: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for segment in raw_x12.split("~"):
        elements = segment.strip().split("*")
        if len(elements) <= 3 or elements[0] != "AAA":
            continue
        code = elements[3]
        counts[code] = counts.get(code, 0) + 1
    return counts


def test_real_gainwell_271_matches_smoke_oracle(client: TestClient) -> None:
    path = _metadata_271_path()
    raw_x12 = path.read_text(encoding="utf-8")

    raw_aaa_counts = _aaa_reject_reason_counts(raw_x12)
    assert raw_x12.count("ST*271*") == EXPECTED_TRANSACTIONS
    assert raw_aaa_counts.get("71", 0) == EXPECTED_AAA_71
    assert raw_aaa_counts.get("73", 0) == EXPECTED_AAA_73
    assert raw_aaa_counts.get("75", 0) == EXPECTED_AAA_75

    response = client.post(
        "/api/v1/parse",
        files={"file": (path.name, raw_x12.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]

    assert payload["sourceTransactionCount"] == EXPECTED_TRANSACTIONS
    assert payload["parsedResultCount"] == EXPECTED_TRANSACTIONS
    assert payload["parserIssueCount"] == 0
    assert payload["parserIssues"] == []
    assert len(payload["results"]) == EXPECTED_TRANSACTIONS

    assert summary["total"] == EXPECTED_TRANSACTIONS
    assert summary["inactive"] == EXPECTED_INACTIVE
    assert summary["error"] == EXPECTED_ERROR
    assert summary["notFound"] == EXPECTED_NOT_FOUND
    assert 0 <= summary["unknown"] <= MAX_EXPECTED_UNKNOWN
    assert summary["active"] + summary["unknown"] == EXPECTED_ACTIVE_OR_UNKNOWN
