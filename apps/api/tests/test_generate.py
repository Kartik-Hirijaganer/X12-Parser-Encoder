from __future__ import annotations

import base64
import io
import zipfile
from datetime import datetime

from app.schemas.common import PatientRecord
from app.services.generator import _build_interchanges
from fastapi.testclient import TestClient
from x12_edi_tools import parse
from x12_edi_tools.config import SubmitterConfig


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


def _segment_fields(x12_content: str, segment_id: str) -> list[str]:
    return next(
        segment.split("*")
        for segment in x12_content.split("~")
        if segment.startswith(f"{segment_id}*")
    )


def _subscriber_loops(x12_content: str):
    interchange = parse(x12_content).interchange
    return [
        subscriber_loop
        for group in interchange.functional_groups
        for transaction in group.transactions
        for receiver_loop in transaction.loop_2000a.loop_2000b
        for subscriber_loop in receiver_loop.loop_2000c
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
    assert payload["download_file_name"].endswith(f"{payload['control_numbers']['isa13']}.txt")
    assert payload["batch_summary_file_name"].endswith("_summary.txt")
    assert "Submission Batch Summary" in payload["batch_summary_text"]
    assert f"Record count: {payload['transaction_count']}" in payload["batch_summary_text"]
    x12_content = payload["x12_content"]
    dmg_index = x12_content.index("DMG*D8*19900101*F~")
    dtp_index = x12_content.index("DTP*291*D8*20260412~")
    eq_index = x12_content.index("EQ*30~")
    assert dmg_index < dtp_index < eq_index
    assert "EQ*30~DTP*291*D8*20260412~" not in x12_content


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
        assert first_file.endswith(".txt")
        assert second_file.endswith(".txt")
        assert first_file in zip_file.namelist()
        assert second_file in zip_file.namelist()
        assert payload["batch_summary_file_name"] in zip_file.namelist()
        assert "manifest.json" in zip_file.namelist()


def test_build_interchanges_uses_configured_control_number_starts_per_batch() -> None:
    config = SubmitterConfig(
        organization_name="Acme Home Health",
        provider_npi="1234567893",
        trading_partner_id="ACMEHOMEHLTH",
        payer_name="DC MEDICAID",
        payer_id="DCMEDICAID",
        interchange_receiver_id="DCMEDICAID",
        default_service_type_code="30",
        max_batch_size=2,
        isa_control_number_start=42,
        gs_control_number_start=7,
    )
    patients = [PatientRecord(**patient) for patient in _patients(3)]

    interchanges = _build_interchanges(
        patients=patients,
        config=config,
        payer_name=config.payer_name,
        payer_id=config.payer_id,
        now=datetime(2026, 4, 12, 21, 0),
    )

    assert [item.isa.interchange_control_number for item in interchanges] == [
        "000000042",
        "000000043",
    ]
    assert [item.iea.interchange_control_number for item in interchanges] == [
        "000000042",
        "000000043",
    ]
    assert [item.functional_groups[0].gs.group_control_number for item in interchanges] == [
        "7",
        "8",
    ]
    assert [item.functional_groups[0].ge.group_control_number for item in interchanges] == [
        "7",
        "8",
    ]


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
    x12_content = payload["x12_content"]
    assert x12_content is not None
    isa = _segment_fields(x12_content, "ISA")
    gs = _segment_fields(x12_content, "GS")
    ge = _segment_fields(x12_content, "GE")
    iea = _segment_fields(x12_content, "IEA")
    assert payload["control_numbers"]["isa13"] == "000000042"
    assert payload["control_numbers"]["gs06"] == "42"
    assert isa[13] == "000000042"
    assert iea[2] == "000000042"
    assert gs[6] == "42"
    assert ge[2] == "42"


def test_generate_respects_control_number_start_across_split_archive(
    client: TestClient, config_payload: dict[str, object]
) -> None:
    config_payload["maxBatchSize"] = 2
    config_payload["isaControlNumberStart"] = 42
    config_payload["gsControlNumberStart"] = 42

    response = client.post(
        "/api/v1/generate",
        json={"config": config_payload, "patients": _patients(3)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["split_count"] == 2
    assert payload["control_numbers"]["isa13"] == "000000042"
    assert payload["control_numbers"]["gs06"] == "42"
    assert payload["archive_entries"][0]["control_numbers"]["isa13"] == "000000042"
    assert payload["archive_entries"][0]["control_numbers"]["gs06"] == "42"
    assert payload["archive_entries"][1]["control_numbers"]["isa13"] == "000000043"
    assert payload["archive_entries"][1]["control_numbers"]["gs06"] == "43"

    archive = base64.b64decode(payload["zip_content_base64"])
    with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
        for entry, expected_isa, expected_gs in zip(
            payload["archive_entries"],
            ("000000042", "000000043"),
            ("42", "43"),
            strict=True,
        ):
            x12_content = zip_file.read(entry["file_name"]).decode("utf-8")
            assert _segment_fields(x12_content, "ISA")[13] == expected_isa
            assert _segment_fields(x12_content, "IEA")[2] == expected_isa
            assert _segment_fields(x12_content, "GS")[6] == expected_gs
            assert _segment_fields(x12_content, "GE")[2] == expected_gs


def test_generate_gainwell_regression_places_single_dtp291_in_2100c_and_sequences_icn(
    client: TestClient, config_payload: dict[str, object]
) -> None:
    config_payload["maxBatchSize"] = 1
    config_payload["isaControlNumberStart"] = 42
    config_payload["gsControlNumberStart"] = 42

    response = client.post(
        "/api/v1/generate",
        json={"config": config_payload, "patients": _patients(2)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["split_count"] == 2
    assert payload["control_numbers"]["isa13"] == "000000042"
    assert payload["archive_entries"][0]["control_numbers"]["isa13"] == "000000042"
    assert payload["archive_entries"][1]["control_numbers"]["isa13"] == "000000043"

    archive = base64.b64decode(payload["zip_content_base64"])
    with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
        for entry, expected_isa, expected_gs in zip(
            payload["archive_entries"],
            ("000000042", "000000043"),
            ("42", "43"),
            strict=True,
        ):
            x12_content = zip_file.read(entry["file_name"]).decode("utf-8")
            assert _segment_fields(x12_content, "ISA")[13] == expected_isa
            assert _segment_fields(x12_content, "IEA")[2] == expected_isa
            assert _segment_fields(x12_content, "GS")[6] == expected_gs
            assert _segment_fields(x12_content, "GE")[2] == expected_gs

            subscriber_loops = _subscriber_loops(x12_content)
            assert len(subscriber_loops) == 1
            for subscriber_loop in subscriber_loops:
                dtp291_2100c = [
                    dtp
                    for dtp in subscriber_loop.loop_2100c.dtp_segments
                    if dtp.date_time_qualifier == "291"
                ]
                dtp291_2110c = [
                    dtp
                    for inquiry_loop in subscriber_loop.loop_2110c
                    for dtp in inquiry_loop.dtp_segments
                    if dtp.date_time_qualifier == "291"
                ]

                assert len(dtp291_2100c) == 1
                assert dtp291_2110c == []
                assert all(
                    inquiry_loop.dtp_segments == [] for inquiry_loop in subscriber_loop.loop_2110c
                )
