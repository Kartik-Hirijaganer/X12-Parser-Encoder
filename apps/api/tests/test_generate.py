from __future__ import annotations

import base64
import io
import zipfile

from fastapi.testclient import TestClient


def _patients(count: int) -> list[dict[str, str]]:
    return [
        {
            "last_name": f"DOE{index}",
            "first_name": f"PATIENT{index}",
            "date_of_birth": "19900101",
            "gender": "F",
            "member_id": f"{12345000 + index}",
            "service_type_code": "30",
            "service_date": "20260412",
        }
        for index in range(count)
    ]


def test_generate_single_patient_returns_x12(
    client: TestClient, config_payload: dict[str, object]
) -> None:
    response = client.post(
        "/api/v1/generate",
        json={"config": config_payload, "patients": _patients(1)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["x12_content"].startswith("ISA*")
    assert payload["transaction_count"] == 1
    assert payload["control_numbers"]["isa13"]
    assert payload["download_file_name"].endswith(f"{payload['control_numbers']['isa13']}.x12")
    assert payload["batch_summary_file_name"].endswith("_summary.txt")
    assert "Submission Batch Summary" in payload["batch_summary_text"]
    assert f"Record count: {payload['transaction_count']}" in payload["batch_summary_text"]


def test_generate_maps_config_values_into_output(
    client: TestClient, config_payload: dict[str, object]
) -> None:
    config_payload["usageIndicator"] = "P"

    response = client.post(
        "/api/v1/generate",
        json={"config": config_payload, "patients": _patients(1)},
    )

    assert response.status_code == 200
    x12_content = response.json()["x12_content"]
    assert "*ACMEHOMEHLTH   *ZZ*DCMEDICAID" in x12_content
    assert "NM1*1P*2*ACME HOME HEALTH" in x12_content
    assert "*0*P*:" in x12_content


def test_generate_requires_non_empty_patients(
    client: TestClient, config_payload: dict[str, object]
) -> None:
    response = client.post(
        "/api/v1/generate",
        json={"config": config_payload, "patients": []},
    )

    assert response.status_code == 422


def test_generate_rejects_invalid_npi(
    client: TestClient, config_payload: dict[str, object]
) -> None:
    config_payload["providerNpi"] = "1234567890"

    response = client.post(
        "/api/v1/generate",
        json={"config": config_payload, "patients": _patients(1)},
    )

    assert response.status_code == 422


def test_generate_auto_splits_into_zip_archive(
    client: TestClient, config_payload: dict[str, object]
) -> None:
    config_payload["maxBatchSize"] = 2
    response = client.post(
        "/api/v1/generate",
        json={"config": config_payload, "patients": _patients(3)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["split_count"] == 2
    assert payload["x12_content"] is None
    assert payload["download_file_name"].endswith(".zip")
    archive = base64.b64decode(payload["zip_content_base64"])
    with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
        first_file = payload["archive_entries"][0]["file_name"]
        second_file = payload["archive_entries"][1]["file_name"]
        assert first_file in zip_file.namelist()
        assert second_file in zip_file.namelist()
        assert payload["batch_summary_file_name"] in zip_file.namelist()
        assert "manifest.json" in zip_file.namelist()


def test_generate_respects_isa_control_number_start(
    client: TestClient, config_payload: dict[str, object]
) -> None:
    config_payload["isaControlNumberStart"] = 42
    config_payload["gsControlNumberStart"] = 42

    response = client.post(
        "/api/v1/generate",
        json={"config": config_payload, "patients": _patients(1)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["control_numbers"]["isa13"] == "000000042"
    assert payload["control_numbers"]["gs06"] == "42"
