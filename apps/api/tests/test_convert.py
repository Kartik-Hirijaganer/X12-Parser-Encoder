from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import build_xlsx_bytes


def test_convert_valid_xlsx_returns_normalized_patients(
    client: TestClient,
    config_payload: dict[str, object],
) -> None:
    workbook = build_xlsx_bytes(
        [
            "last_name",
            "first_name",
            "date_of_birth",
            "gender",
            "member_id",
            "service_type_code",
            "service_date",
        ],
        [["smith", "john", "01/15/1985", "m", "12345678", "", "2026-04-12"]],
    )

    response = client.post(
        "/api/v1/convert",
        files={
            "file": (
                "patients.xlsx",
                workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"config": __import__("json").dumps(config_payload)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recordCount"] == 1
    assert payload["patients"][0]["lastName"] == "SMITH"
    assert payload["patients"][0]["firstName"] == "JOHN"
    assert payload["patients"][0]["dateOfBirth"] == "19850115"
    assert payload["patients"][0]["serviceTypeCode"] == "30"


def test_convert_missing_required_column_returns_actionable_error(
    client: TestClient,
) -> None:
    workbook = build_xlsx_bytes(
        ["first_name", "date_of_birth", "gender", "member_id", "service_date"],
        [["John", "19850115", "M", "12345678", "20260412"]],
    )

    response = client.post(
        "/api/v1/convert",
        files={
            "file": (
                "patients.xlsx",
                workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "BAD_REQUEST"
    assert "missingColumns" in payload["details"]
    assert "last_name" in payload["details"]["missingColumns"]


def test_convert_extra_columns_are_ignored_with_warning(client: TestClient) -> None:
    csv_payload = (
        "last_name,first_name,date_of_birth,gender,member_id,service_date,extra_column\n"
        "SMITH,JOHN,19850115,M,12345678,20260412,ignored\n"
    )
    response = client.post(
        "/api/v1/convert",
        files={"file": ("patients.csv", csv_payload.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recordCount"] == 1
    assert payload["warnings"][0]["field"] == "extra_column"


def test_convert_rejects_unsupported_file_type(client: TestClient) -> None:
    response = client.post(
        "/api/v1/convert",
        files={"file": ("patients.pdf", b"%PDF", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Unsupported file type."


def test_convert_empty_xlsx_returns_zero_records(client: TestClient) -> None:
    workbook = build_xlsx_bytes([], [])

    response = client.post(
        "/api/v1/convert",
        files={
            "file": (
                "patients.xlsx",
                workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["recordCount"] == 0


def test_convert_short_member_id_warns_and_partial_errors_are_preserved(
    client: TestClient,
) -> None:
    workbook = build_xlsx_bytes(
        [
            "last_name",
            "first_name",
            "date_of_birth",
            "gender",
            "member_id",
            "service_type_code",
            "service_date",
        ],
        [
            ["SMITH", "JOHN", "19850115", "M", "1234567", "30", "20260412"],
            ["BROKEN", "ROW", "not-a-date", "M", "12345678", "30", "20260412"],
        ],
    )

    response = client.post(
        "/api/v1/convert",
        files={
            "file": (
                "patients.xlsx",
                workbook,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recordCount"] == 1
    assert len(payload["errors"]) == 1
    assert payload["warnings"][0]["field"] == "member_id"
    assert payload["warnings"][0]["row"] == 2
