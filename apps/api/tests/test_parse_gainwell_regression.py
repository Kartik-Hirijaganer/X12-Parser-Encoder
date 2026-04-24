"""Cross-layer regression gate for /api/v1/parse against the Gainwell 271 fixture."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import fixture_text

EXPECTED_TRANSACTIONS = 153
EXPECTED_ACTIVE = 136
EXPECTED_ERROR = 12
EXPECTED_NOT_FOUND = 1
EXPECTED_UNKNOWN = 4
EXPECTED_INACTIVE = 0


def _post_gainwell_271(client: TestClient) -> dict[str, object]:
    edi = fixture_text("gainwell_271_redacted.edi")
    response = client.post(
        "/api/v1/parse",
        files={"file": ("gainwell_271_redacted.edi", edi.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 200
    return response.json()


def test_parse_gainwell_271_preserves_every_source_transaction(
    client: TestClient,
) -> None:
    payload = _post_gainwell_271(client)

    assert payload["sourceTransactionCount"] == EXPECTED_TRANSACTIONS
    assert payload["parsedResultCount"] == EXPECTED_TRANSACTIONS
    assert payload["parserIssueCount"] == 0
    assert payload["parserIssues"] == []
    assert payload["transactionCount"] == EXPECTED_TRANSACTIONS
    assert len(payload["results"]) == EXPECTED_TRANSACTIONS


def test_parse_gainwell_271_summary_matches_expected_status_distribution(
    client: TestClient,
) -> None:
    payload = _post_gainwell_271(client)
    summary = payload["summary"]

    assert summary["total"] == EXPECTED_TRANSACTIONS
    assert summary["active"] == EXPECTED_ACTIVE
    assert summary["inactive"] == EXPECTED_INACTIVE
    assert summary["error"] == EXPECTED_ERROR
    assert summary["notFound"] == EXPECTED_NOT_FOUND
    assert summary["unknown"] == EXPECTED_UNKNOWN
    assert (
        summary["active"]
        + summary["inactive"]
        + summary["error"]
        + summary["notFound"]
        + summary["unknown"]
        == summary["total"]
    )


def test_parse_gainwell_271_projects_2120c_entities_and_reasons(
    client: TestClient,
) -> None:
    payload = _post_gainwell_271(client)

    active_rows = [row for row in payload["results"] if row["overallStatus"] == "active"]
    assert active_rows, "Expected at least one active row in the Gainwell fixture."

    first_active = active_rows[0]
    assert first_active["statusReason"] == "Coverage on file"
    assert first_active["stControlNumber"]
    assert first_active["traceNumber"]
    assert first_active["eligibilitySegments"][0]["serviceTypeCodes"] == [
        "30",
        "1",
        "35",
        "47",
        "48",
        "50",
        "86",
        "88",
        "AL",
        "MH",
    ]

    plan_sponsors = [
        entity
        for entity in first_active["benefitEntities"]
        if entity.get("entityIdentifierCode") == "P5"
    ]
    assert plan_sponsors, "Expected a P5 plan sponsor on the first active row."
    plan_sponsor = plan_sponsors[0]
    assert plan_sponsor["name"] is not None
    assert plan_sponsor["contacts"], "Expected PER contacts on the 2120C plan sponsor."
