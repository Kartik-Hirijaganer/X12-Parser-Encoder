from __future__ import annotations

from app.schemas.common import ValidationIssue
from app.schemas.validate import PatientValidationRow, ValidateResponse, ValidationSummary


def test_validate_response_round_trips_with_patient_rows() -> None:
    response = ValidateResponse(
        filename="batch.x12",
        is_valid=False,
        error_count=1,
        warning_count=0,
        issues=[
            ValidationIssue(
                severity="error",
                level="dc_medicaid",
                code="DCM_INVALID_PAYER_NAME",
                message="Invalid payer name.",
                transaction_index=1,
                transaction_control_number="0002",
            )
        ],
        patients=[
            PatientValidationRow(
                index=0,
                transaction_control_number="0001",
                member_name="DOE, PATIENT",
                member_id="000123450",
                service_date="20260412",
                status="valid",
                error_count=0,
                warning_count=0,
            ),
            PatientValidationRow(
                index=1,
                transaction_control_number="0002",
                member_name="DOE, JANE",
                member_id="000123451",
                service_date="20260412",
                status="invalid",
                error_count=1,
                warning_count=0,
                issues=[
                    ValidationIssue(
                        severity="error",
                        level="dc_medicaid",
                        code="DCM_INVALID_PAYER_NAME",
                        message="Invalid payer name.",
                        transaction_index=1,
                        transaction_control_number="0002",
                    )
                ],
            ),
            PatientValidationRow(
                index=2,
                transaction_control_number="0003",
                member_name="DOE, JACK",
                member_id="000123452",
                service_date="20260412",
                status="valid",
                error_count=0,
                warning_count=0,
            ),
        ],
        summary=ValidationSummary(total_patients=3, valid_patients=2, invalid_patients=1),
    )

    round_tripped = ValidateResponse.model_validate_json(response.model_dump_json())

    assert round_tripped.summary is not None
    assert round_tripped.summary.total_patients == 3
    assert round_tripped.patients[1].status == "invalid"
    assert round_tripped.issues[0].transaction_control_number == "0002"
