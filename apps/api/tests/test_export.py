from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import load_workbook


def test_export_xlsx_omits_parser_issues_sheet_for_clean_payload(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/export/xlsx", json=_export_payload())

    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content))
    assert "Parser Issues" not in workbook.sheetnames


def test_export_xlsx_includes_parser_issues_sheet_when_present(
    client: TestClient,
) -> None:
    payload = _export_payload()
    payload["parser_issue_count"] = 1
    payload["parser_issues"] = [
        {
            "transaction_index": 1,
            "transaction_control_number": "0002",
            "segment_id": "NM1",
            "location": "segment_position:999",
            "message": "Invalid benefit entity.",
            "severity": "error",
        }
    ]

    response = client.post("/api/v1/export/xlsx", json=payload)

    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content))
    assert "Parser Issues" in workbook.sheetnames
    sheet = workbook["Parser Issues"]
    assert sheet["B2"].value == "0002"
    assert sheet["E2"].value == "Invalid benefit entity."


def test_export_validation_xlsx_emits_three_sheets_with_matching_rows(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/export/validation/xlsx", json=_validation_payload())

    assert response.status_code == 200
    workbook = load_workbook(BytesIO(response.content))
    assert workbook.sheetnames == ["Summary", "Per-Patient", "Issues"]
    assert workbook["Summary"]["B5"].value == 3
    assert workbook["Per-Patient"].max_row == 4
    assert workbook["Issues"].max_row == 2
    assert workbook["Per-Patient"]["F3"].value == "invalid"
    assert workbook["Issues"]["C2"].value == "DCM_INVALID_PAYER_NAME"


def _export_payload() -> dict[str, object]:
    return {
        "filename": "eligibility.xlsx",
        "payer_name": "DC MEDICAID",
        "summary": {
            "total": 1,
            "active": 1,
            "inactive": 0,
            "error": 0,
            "not_found": 0,
            "unknown": 0,
        },
        "results": [
            {
                "member_name": "DOE, JOHN",
                "member_id": "12345678",
                "overall_status": "active",
                "status_reason": "Coverage on file",
                "st_control_number": "0001",
                "trace_number": "TRACE0001",
                "eligibility_segments": [
                    {
                        "eligibility_code": "1",
                        "service_type_code": "30",
                        "service_type_codes": ["30"],
                        "plan_coverage_description": "MEDICAID",
                    }
                ],
                "benefit_entities": [
                    {
                        "entity_identifier_code": "P5",
                        "name": "PLAN SPONSOR",
                        "contacts": ["SUPPORT (TE:8665550001)"],
                    }
                ],
                "aaa_errors": [],
            }
        ],
    }


def _validation_payload() -> dict[str, object]:
    return {
        "filename": "validation.xlsx",
        "is_valid": False,
        "error_count": 1,
        "warning_count": 0,
        "issues": [
            {
                "severity": "error",
                "level": "dc_medicaid",
                "code": "DCM_INVALID_PAYER_NAME",
                "message": "Invalid payer name.",
                "transaction_index": 1,
                "transaction_control_number": "0002",
            }
        ],
        "patients": [
            {
                "index": 0,
                "transaction_control_number": "0001",
                "member_name": "DOE, PATIENT",
                "member_id": "000123450",
                "service_date": "20260412",
                "status": "valid",
                "error_count": 0,
                "warning_count": 0,
                "issues": [],
            },
            {
                "index": 1,
                "transaction_control_number": "0002",
                "member_name": "DOE, JANE",
                "member_id": "000123451",
                "service_date": "20260412",
                "status": "invalid",
                "error_count": 1,
                "warning_count": 0,
                "issues": [
                    {
                        "severity": "error",
                        "level": "dc_medicaid",
                        "code": "DCM_INVALID_PAYER_NAME",
                        "message": "Invalid payer name.",
                        "transaction_index": 1,
                        "transaction_control_number": "0002",
                    }
                ],
            },
            {
                "index": 2,
                "transaction_control_number": "0003",
                "member_name": "DOE, JACK",
                "member_id": "000123452",
                "service_date": "20260412",
                "status": "valid",
                "error_count": 0,
                "warning_count": 0,
                "issues": [],
            },
        ],
        "summary": {
            "total_patients": 3,
            "valid_patients": 2,
            "invalid_patients": 1,
        },
    }
