from __future__ import annotations

import re

import pytest
from app.services import parser as parser_service
from fastapi.testclient import TestClient
from x12_edi_tools import parse as parse_x12
from x12_edi_tools.exceptions import TransactionParseError

from tests.helpers import fixture_text


def test_parse_reconciliation_mismatch_returns_200_and_increments_counter(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_fixture = fixture_text("271_active_response.x12")
    parsed = parse_x12(raw_fixture, strict=False, on_error="collect")
    parser_error = TransactionParseError(
        transaction_index=1,
        st_control_number="0002",
        segment_position=999,
        segment_id="NM1",
        raw_segment="NM1*BAD",
        error="invalid_nm1",
        message="Invalid benefit entity.",
        suggestion="Review NM1 benefit entity values.",
    )

    def fake_parse(*args: object, **kwargs: object) -> object:
        parsed.errors = [parser_error]
        return parsed

    monkeypatch.setattr(parser_service, "parse", fake_parse)
    raw_with_extra_source_transactions = f"{raw_fixture}\nST*271*0002~\nST*271*0003~"
    before = _mismatch_counter_value(client)

    response = client.post(
        "/api/v1/parse",
        files={
            "file": (
                "271.x12",
                raw_with_extra_source_transactions.encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_transaction_count"] == 3
    assert payload["parsed_result_count"] == 1
    assert payload["parser_issue_count"] == 1
    assert payload["transaction_count"] == 3
    assert payload["parser_issues"][0]["transaction_control_number"] == "0002"
    assert _mismatch_counter_value(client) == before + 1


def _mismatch_counter_value(client: TestClient) -> float:
    response = client.get("/metrics")
    assert response.status_code == 200
    match = re.search(
        r'parser_accounting_mismatch_total\{path="/api/v1/parse"\}\s+([0-9.]+)',
        response.text,
    )
    assert match is not None
    return float(match.group(1))
