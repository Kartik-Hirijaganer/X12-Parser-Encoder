from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import fixture_text


def test_validate_valid_270_returns_is_valid(client: TestClient) -> None:
    response = client.post(
        "/api/v1/validate",
        files={
            "file": (
                "valid.x12",
                fixture_text("270_realtime_single.x12").encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["is_valid"] is True


def test_validate_wrong_isa08_returns_suggestion(client: TestClient) -> None:
    invalid = fixture_text("270_realtime_single.x12").replace(
        "DCMEDICAID     ", "OTHERPAYER     ", 1
    )
    response = client.post(
        "/api/v1/validate",
        files={"file": ("invalid.x12", invalid.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_valid"] is False
    assert any(issue["code"] == "DCM_INVALID_ISA08" for issue in payload["issues"])


def test_validate_garbled_text_returns_error(client: TestClient) -> None:
    response = client.post(
        "/api/v1/validate",
        files={"file": ("garbled.x12", b"not actually x12", "text/plain")},
    )

    assert response.status_code == 400


def test_parse_271_summarizes_active_results(client: TestClient) -> None:
    response = client.post(
        "/api/v1/parse",
        files={
            "file": (
                "271.x12",
                fixture_text("271_active_response.x12").encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["active"] == 1
    assert payload["results"][0]["overall_status"] == "active"


def test_parse_271_extracts_aaa_and_benefit_entities(client: TestClient) -> None:
    rejected = client.post(
        "/api/v1/parse",
        files={
            "file": (
                "271.x12",
                fixture_text("271_rejected_subscriber.x12").encode("utf-8"),
                "text/plain",
            )
        },
    )
    wrapped = client.post(
        "/api/v1/parse",
        files={
            "file": (
                "271.x12",
                fixture_text("271_ls_le_wrapper.x12").encode("utf-8"),
                "text/plain",
            )
        },
    )
    multi_eb = client.post(
        "/api/v1/parse",
        files={
            "file": (
                "271.x12",
                fixture_text("271_multiple_eb_segments.x12").encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert rejected.status_code == 200
    assert rejected.json()["results"][0]["overall_status"] == "error"
    assert rejected.json()["results"][0]["aaa_errors"][0]["code"] == "72"
    assert wrapped.json()["results"][0]["benefit_entities"][0]["identifier"] == "PLAN123"
    assert multi_eb.json()["results"][0]["eligibility_segments"][1]["monetary_amount"] == "5.00"
