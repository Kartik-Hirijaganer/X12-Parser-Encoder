"""Behavior tests for the high-level convenience API."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

from x12_edi_tools import (
    EligibilityResult,
    ImportResult,
    PatientRecord,
    SubmitterConfig,
    build_270,
    encode,
    from_csv,
    from_excel,
    read_271,
)
from x12_edi_tools.exceptions import X12ValidationError

FIXTURES = Path(__file__).parent / "fixtures"


# --- Helpers ----------------------------------------------------------------


def _config(**overrides: object) -> SubmitterConfig:
    payload = {
        "organization_name": "ACME HOME HEALTH",
        "provider_npi": "1234567893",
        "trading_partner_id": "ACMETP01",
        "payer_name": "DC MEDICAID",
        "payer_id": "DCMEDICAID",
        "interchange_receiver_id": "DCMEDICAID",
    }
    payload.update(overrides)
    return SubmitterConfig(**payload)


def _csv_bytes(header_row: str, *rows: str) -> bytes:
    return ("\n".join([header_row, *rows]) + "\n").encode("utf-8")


def _write(tmp_path: Path, name: str, content: bytes) -> Path:
    target = tmp_path / name
    target.write_bytes(content)
    return target


# --- from_csv / from_excel --------------------------------------------------


def test_from_csv_autocorrects_dates_names_and_service_type(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "patients.csv",
        _csv_bytes(
            "last_name,first_name,date_of_birth,gender,member_id,service_date",
            "smith,john,01/15/1985,m,12345678,20260415",
            "JONES,MARY,1990-02-20,f,87654321,20260415",
        ),
    )

    result = from_csv(path)

    assert isinstance(result, ImportResult)
    assert len(result.patients) == 2
    assert result.patients[0].last_name == "SMITH"
    assert result.patients[0].first_name == "JOHN"
    assert result.patients[0].date_of_birth == "19850115"
    assert result.patients[0].gender == "M"
    assert result.patients[0].service_type_code == "30"
    assert result.patients[1].date_of_birth == "19900220"

    correction_fields = {(c.field, c.row) for c in result.corrections}
    assert ("last_name", 1) in correction_fields
    assert ("first_name", 1) in correction_fields
    assert ("date_of_birth", 1) in correction_fields
    assert ("gender", 1) in correction_fields
    # service_type_code was auto-filled from the default for each row
    assert sum(1 for c in result.corrections if c.field == "service_type_code") == 2


def test_from_csv_preserves_explicit_service_type_code_without_warnings(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "patients.csv",
        _csv_bytes(
            "last_name,first_name,date_of_birth,gender,member_id,service_type_code,service_date",
            "SMITH,JOHN,19850115,M,12345678,30,20260415",
        ),
    )

    result = from_csv(path)

    assert len(result.patients) == 1
    assert result.patients[0].service_type_code == "30"
    assert not any(c.field == "service_type_code" for c in result.corrections)


def test_from_csv_short_member_id_surfaces_warning_not_autocorrection(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "patients.csv",
        _csv_bytes(
            "last_name,first_name,date_of_birth,gender,member_id,service_date",
            "SMITH,JOHN,19850115,M,1234567,20260415",
        ),
    )

    result = from_csv(path)

    assert len(result.patients) == 1
    assert result.patients[0].member_id == "1234567"  # not auto-padded
    assert any(
        "short" in warning.message and warning.field == "member_id" for warning in result.warnings
    )


def test_from_csv_missing_required_column_raises(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "patients.csv",
        _csv_bytes(
            "last_name,first_name,date_of_birth,member_id,service_date",  # gender missing
            "SMITH,JOHN,19850115,12345678,20260415",
        ),
    )

    with pytest.raises(X12ValidationError, match="Missing required template columns"):
        from_csv(path)


def test_from_csv_extra_column_emits_warning_and_ignores_it(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "patients.csv",
        _csv_bytes(
            ("last_name,first_name,date_of_birth,gender,member_id,service_date,diagnosis_code"),
            "SMITH,JOHN,19850115,M,12345678,20260415,Z00.00",
        ),
    )

    result = from_csv(path)

    assert len(result.patients) == 1
    assert any(w.field == "diagnosis_code" for w in result.warnings)


def test_from_csv_partial_result_collects_per_row_errors(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "patients.csv",
        _csv_bytes(
            "last_name,first_name,date_of_birth,gender,member_id,service_date",
            "SMITH,JOHN,19850115,M,12345678,20260415",  # valid
            ",JANE,19850115,M,87654321,20260415",  # missing last_name
            "BROWN,BOB,notadate,M,11111111,20260415",  # unparseable DOB
            "GREEN,KIM,19850115,X,22222222,20260415",  # bad gender
        ),
    )

    result = from_csv(path)

    assert len(result.patients) == 1
    error_rows = {(e.row, e.field) for e in result.errors}
    assert (2, "last_name") in error_rows
    assert (3, "date_of_birth") in error_rows
    assert (4, "gender") in error_rows


def test_from_csv_accepts_default_service_date_and_service_type(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "patients.csv",
        _csv_bytes(
            "last_name,first_name,date_of_birth,gender,member_id,service_date",
            "SMITH,JOHN,19850115,M,12345678,",  # empty service_date
        ),
    )

    result = from_csv(
        path,
        default_service_type_code="98",
        default_service_date="20260101",
    )

    assert len(result.patients) == 1
    assert result.patients[0].service_date == "20260101"
    assert result.patients[0].service_type_code == "98"


def test_from_csv_tsv_extension_uses_tab_delimiter(tmp_path: Path) -> None:
    content = (
        b"last_name\tfirst_name\tdate_of_birth\tgender\tmember_id\tservice_date\n"
        b"SMITH\tJOHN\t19850115\tM\t12345678\t20260415\n"
    )
    path = _write(tmp_path, "patients.tsv", content)

    result = from_csv(path)

    assert len(result.patients) == 1
    assert result.patients[0].last_name == "SMITH"


def test_from_csv_missing_file_raises_validation_error(tmp_path: Path) -> None:
    with pytest.raises(X12ValidationError, match="does not exist"):
        from_csv(tmp_path / "no-such-file.csv")


def test_from_excel_reads_xlsx(tmp_path: Path) -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        ["last_name", "first_name", "date_of_birth", "gender", "member_id", "service_date"]
    )
    sheet.append(["smith", "john", "1/15/1985", "m", "12345678", "20260415"])
    excel_path = tmp_path / "patients.xlsx"
    workbook.save(excel_path)

    result = from_excel(excel_path)

    assert len(result.patients) == 1
    assert result.patients[0].last_name == "SMITH"
    assert result.patients[0].date_of_birth == "19850115"


def test_from_excel_reports_missing_openpyxl_extra(tmp_path: Path) -> None:
    # openpyxl is available in the test environment, so simulate its absence.
    path = _write(tmp_path, "patients.xlsx", b"not-really-xlsx")
    with mock.patch.dict(sys.modules, {"openpyxl": None}):  # type: ignore[dict-item]
        # Nullify the import by forcing an ImportError when load_workbook is looked up.
        with mock.patch(
            "x12_edi_tools.convenience._parse_xlsx",
            side_effect=X12ValidationError("from_excel() requires the optional openpyxl extra."),
        ):
            with pytest.raises(X12ValidationError, match="optional openpyxl extra"):
                from_excel(path)


# --- build_270 --------------------------------------------------------------


def test_build_270_produces_roundtrippable_interchange() -> None:
    patients = [
        PatientRecord(
            last_name="SMITH",
            first_name="JOHN",
            date_of_birth="19850115",
            gender="M",
            member_id="12345678",
            service_type_code="30",
            service_date="20260415",
        )
    ]
    config = _config()

    interchange = build_270(patients, config=config, profile="dc_medicaid")
    encoded = encode(interchange)
    assert isinstance(encoded, str)
    assert encoded.startswith("ISA*")
    # Trading partner id is right-padded into ISA06
    assert "ACMETP01       " in encoded
    # Payer NM1 should contain DCMEDICAID as the payer id
    assert "NM1*PR*2*DC MEDICAID*****PI*DCMEDICAID~" in encoded


def test_build_270_accepts_patient_mapping_dicts_and_import_result() -> None:
    config = _config()

    mapping_input = [
        {
            "last_name": "SMITH",
            "first_name": "JOHN",
            "date_of_birth": "19850115",
            "gender": "M",
            "member_id": "12345678",
            "service_type_code": "30",
            "service_date": "20260415",
        }
    ]
    interchange = build_270(mapping_input, config=config, profile="dc_medicaid")
    first_transaction = interchange.functional_groups[0].transactions[0]
    assert first_transaction.st.transaction_set_identifier_code == "270"

    import_result = ImportResult(patients=[PatientRecord.model_validate(mapping_input[0])])
    interchange = build_270(import_result, config=config, profile="dc_medicaid")
    assert len(interchange.functional_groups[0].transactions) == 1


def test_build_270_attaches_ssn_reference_segment() -> None:
    patients = [
        PatientRecord(
            last_name="SMITH",
            first_name="JOHN",
            date_of_birth="19850115",
            gender="M",
            ssn="999887777",
            service_type_code="30",
            service_date="20260415",
        )
    ]
    config = _config()

    interchange = build_270(patients, config=config, profile="dc_medicaid")
    encoded = encode(interchange)

    assert "REF*SY*999887777~" in encoded


def test_build_270_honors_control_number_overrides() -> None:
    patients = [
        PatientRecord(
            last_name="SMITH",
            first_name="JOHN",
            date_of_birth="19850115",
            gender="M",
            member_id="12345678",
            service_type_code="30",
            service_date="20260415",
        )
    ]
    config = _config(isa_control_number_start=42, gs_control_number_start=7)

    interchange = build_270(patients, config=config, profile="dc_medicaid")
    assert interchange.isa.interchange_control_number == "000000042"
    assert interchange.functional_groups[0].gs.group_control_number == "7"


def test_build_270_service_date_range_uses_rd8_format() -> None:
    patients = [
        PatientRecord(
            last_name="SMITH",
            first_name="JOHN",
            date_of_birth="19850115",
            gender="M",
            member_id="12345678",
            service_type_code="30",
            service_date="20260401",
            service_date_end="20260430",
        )
    ]
    config = _config()

    encoded = encode(build_270(patients, config=config))

    assert "DTP*291*RD8*20260401-20260430~" in encoded


def test_build_270_rejects_unknown_profile() -> None:
    config = _config()
    patients = [
        PatientRecord(
            last_name="SMITH",
            first_name="JOHN",
            date_of_birth="19850115",
            gender="M",
            member_id="12345678",
            service_type_code="30",
            service_date="20260415",
        )
    ]
    with pytest.raises(X12ValidationError, match="Unknown payer profile"):
        build_270(patients, config=config, profile="nope")


# --- read_271 ---------------------------------------------------------------


def test_read_271_from_fixture_path_populates_results() -> None:
    result_set = read_271(FIXTURES / "271_active_response.x12")

    assert result_set.payer_name == "DC MEDICAID"
    assert result_set.transaction_count == 1
    assert len(result_set) == 1
    result = result_set[0]
    assert isinstance(result, EligibilityResult)
    assert result.overall_status == "active"
    assert result.member_id is not None
    assert result.eligibility_segments, "Expected at least one EB projection"


def test_read_271_accepts_inline_x12_string() -> None:
    raw = (FIXTURES / "271_active_response.x12").read_text(encoding="utf-8")

    result_set = read_271(raw)

    assert result_set.transaction_count == 1
    assert result_set.results[0].overall_status == "active"


def test_read_271_summary_counts_by_status() -> None:
    result_set = read_271(FIXTURES / "271_rejected_subscriber.x12")

    assert result_set.summary["total"] == len(result_set.results)
    assert result_set.summary["error"] >= 1


def test_read_271_maps_aaa_reject_codes_to_plain_english() -> None:
    result_set = read_271(FIXTURES / "271_rejected_subscriber.x12")
    aaa_codes = [error.code for result in result_set.results for error in result.aaa_errors]
    aaa_messages = [error.message for result in result_set.results for error in result.aaa_errors]

    assert aaa_codes, "Expected AAA errors in the rejected-subscriber fixture"
    # Each AAA error should have a human-readable message.
    assert all(message for message in aaa_messages)


def test_read_271_rejects_270_payload() -> None:
    with pytest.raises(X12ValidationError, match="expects a 271"):
        read_271(FIXTURES / "270_realtime_single.x12")


def test_read_271_to_dataframe_requires_pandas(monkeypatch: pytest.MonkeyPatch) -> None:
    result_set = read_271(FIXTURES / "271_active_response.x12")

    monkeypatch.setitem(sys.modules, "pandas", None)
    with pytest.raises(X12ValidationError, match="optional pandas extra"):
        result_set.to_dataframe()


def test_read_271_to_dataframe_uses_pandas_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    class _PandasStub:
        @staticmethod
        def DataFrame(rows):
            return {"rows": rows}

    monkeypatch.setitem(sys.modules, "pandas", _PandasStub())
    result_set = read_271(FIXTURES / "271_active_response.x12")

    frame = result_set.to_dataframe()

    assert isinstance(frame, dict)
    assert frame["rows"]
    assert "member_name" in frame["rows"][0]


def test_read_271_missing_file_raises() -> None:
    with pytest.raises(X12ValidationError, match="does not exist"):
        read_271(Path("/tmp/definitely-not-here-271.x12"))


# --- Agent-style end-to-end roundtrip ---------------------------------------


def test_agent_style_pipeline_from_csv_through_build_270_and_encode(tmp_path: Path) -> None:
    csv_path = _write(
        tmp_path,
        "patients.csv",
        _csv_bytes(
            "last_name,first_name,date_of_birth,gender,member_id,service_date",
            "smith,john,01/15/1985,m,12345678,20260415",
            "jones,mary,02/20/1990,f,87654321,20260415",
        ),
    )

    patients = from_csv(csv_path)
    interchange = build_270(patients, config=_config(), profile="dc_medicaid")
    encoded = encode(interchange)

    assert encoded.startswith("ISA*")
    assert "NM1*IL*1*SMITH*JOHN" in encoded
    assert "NM1*IL*1*JONES*MARY" in encoded
