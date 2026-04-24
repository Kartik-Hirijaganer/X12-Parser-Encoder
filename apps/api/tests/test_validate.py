from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import fixture_text


def test_validate_projects_three_patient_rows_with_transaction_issue(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/validate",
        files={
            "file": (
                "three-patient.x12",
                _three_transaction_270_with_bad_second().encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {
        "total_patients": 3,
        "valid_patients": 2,
        "invalid_patients": 1,
    }
    assert len(payload["patients"]) == 3
    assert payload["patients"][1]["status"] == "invalid"
    assert payload["patients"][1]["transaction_control_number"] == "0002"
    assert payload["patients"][1]["issues"][0]["code"] == "DCM_INVALID_PAYER_NAME"
    assert payload["patients"][2]["status"] == "valid"


def _three_transaction_270_with_bad_second() -> str:
    raw = fixture_text("270_batch_multi.x12")
    prefix, second_marker, remainder = raw.partition("ST*270*0002*005010X279A1~")
    second_body, ge_marker, trailer = remainder.partition("GE*2*2~")
    second_transaction = f"{second_marker}{second_body}"
    bad_second_transaction = second_transaction.replace(
        "NM1*PR*2*DC MEDICAID",
        "NM1*PR*2*WRONG PAYER",
        1,
    )
    third_transaction = (
        second_transaction.replace("0002", "0003")
        .replace("TRACE0002", "TRACE0003")
        .replace("10001235", "10001236")
        .replace("1206", "1207")
        .replace("DOE*JANE", "DOE*JACK")
        .replace("000123451", "000123452")
    )
    updated_ge = ge_marker.replace("2", "3", 1)
    return f"{prefix}{bad_second_transaction}{third_transaction}{updated_ge}{trailer}"
