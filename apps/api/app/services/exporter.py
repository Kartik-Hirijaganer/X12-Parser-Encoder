"""Excel export services."""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook  # type: ignore[import-untyped]
from openpyxl.styles import Font  # type: ignore[import-untyped]

from app.core.logging import get_logger
from app.core.metrics import observe_record_count
from app.schemas.common import EligibilityResult
from app.schemas.export import ExportWorkbookRequest
from app.schemas.validate import ValidateResponse, ValidationSummary

logger = get_logger(__name__)


def build_workbook_bytes(
    payload: ExportWorkbookRequest,
    *,
    correlation_id: str | None = None,
    metrics_path: str = "/api/v1/export/xlsx",
) -> bytes:
    """Render parsed eligibility results into an Excel workbook."""

    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    summary_sheet["A1"] = "Payer"
    summary_sheet["B1"] = payload.payer_name or ""
    summary_sheet["A2"] = "Total"
    summary_sheet["B2"] = payload.summary.total
    summary_sheet["A3"] = "Active"
    summary_sheet["B3"] = payload.summary.active
    summary_sheet["A4"] = "Inactive"
    summary_sheet["B4"] = payload.summary.inactive
    summary_sheet["A5"] = "Error"
    summary_sheet["B5"] = payload.summary.error
    summary_sheet["A6"] = "Not Found"
    summary_sheet["B6"] = payload.summary.not_found
    summary_sheet["A7"] = "Unknown"
    summary_sheet["B7"] = payload.summary.unknown
    for cell in summary_sheet["A"][:7]:
        cell.font = Font(bold=True)

    results_sheet = workbook.create_sheet("Eligibility Results")
    headers = [
        "member_name",
        "member_id",
        "overall_status",
        "status_reason",
        "primary_plan_summary",
        "all_eb01_codes",
        "all_eb03_service_types",
        "benefit_entity_names",
        "contact_summaries",
        "aaa_codes",
        "st_control_number",
        "primary_trn",
    ]
    results_sheet.append(headers)
    for cell in results_sheet[1]:
        cell.font = Font(bold=True)
    results_sheet.freeze_panes = "A2"

    for result in payload.results:
        results_sheet.append(
            [
                result.member_name,
                result.member_id,
                result.overall_status,
                result.status_reason,
                _primary_plan_summary(result),
                _all_eb01_codes(result),
                _all_eb03_service_types(result),
                _benefit_entity_names(result),
                _contact_summaries(result),
                _aaa_codes(result),
                result.st_control_number,
                result.trace_number,
            ]
        )

    issue_count = payload.parser_issue_count or len(payload.parser_issues)
    if issue_count > 0:
        issues_sheet = workbook.create_sheet("Parser Issues")
        issues_sheet.append(
            [
                "transaction_index",
                "transaction_control_number",
                "segment_id",
                "location",
                "message",
                "severity",
            ]
        )
        for cell in issues_sheet[1]:
            cell.font = Font(bold=True)
        issues_sheet.freeze_panes = "A2"
        for issue in payload.parser_issues:
            issues_sheet.append(
                [
                    issue.transaction_index,
                    issue.transaction_control_number,
                    issue.segment_id,
                    issue.location,
                    issue.message,
                    issue.severity,
                ]
            )

    output = BytesIO()
    workbook.save(output)
    observe_record_count(path=metrics_path, operation="export_rows", count=len(payload.results))
    workbook_bytes = output.getvalue()
    logger.info(
        "export_workbook_completed",
        extra={
            "correlation_id": correlation_id,
            "path": metrics_path,
            "result_count": len(payload.results),
            "workbook_bytes": len(workbook_bytes),
        },
    )
    return workbook_bytes


def build_validation_workbook_bytes(
    payload: ValidateResponse,
    *,
    correlation_id: str | None = None,
    metrics_path: str = "/api/v1/export/validation/xlsx",
) -> bytes:
    """Render validation results into a three-sheet Excel workbook."""

    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"

    summary = payload.summary or _validation_summary_from_patients(payload)
    summary_rows = [
        ("filename", payload.filename),
        ("is_valid", payload.is_valid),
        ("error_count", payload.error_count),
        ("warning_count", payload.warning_count),
        ("total_patients", summary.total_patients),
        ("valid_patients", summary.valid_patients),
        ("invalid_patients", summary.invalid_patients),
    ]
    for row in summary_rows:
        summary_sheet.append(row)
    for cell in summary_sheet["A"][: len(summary_rows)]:
        cell.font = Font(bold=True)

    patient_sheet = workbook.create_sheet("Per-Patient")
    patient_headers = [
        "index",
        "transaction_control_number",
        "member_name",
        "member_id",
        "service_date",
        "status",
        "error_count",
        "warning_count",
    ]
    patient_sheet.append(patient_headers)
    for cell in patient_sheet[1]:
        cell.font = Font(bold=True)
    patient_sheet.freeze_panes = "A2"
    for patient in payload.patients:
        patient_sheet.append(
            [
                patient.index,
                patient.transaction_control_number,
                patient.member_name,
                patient.member_id,
                patient.service_date,
                patient.status,
                patient.error_count,
                patient.warning_count,
            ]
        )

    issues_sheet = workbook.create_sheet("Issues")
    issue_headers = [
        "severity",
        "level",
        "code",
        "message",
        "location",
        "segment_id",
        "element",
        "suggestion",
        "profile",
        "transaction_index",
        "transaction_control_number",
    ]
    issues_sheet.append(issue_headers)
    for cell in issues_sheet[1]:
        cell.font = Font(bold=True)
    issues_sheet.freeze_panes = "A2"
    for issue in payload.issues:
        issues_sheet.append(
            [
                issue.severity,
                issue.level,
                issue.code,
                issue.message,
                issue.location,
                issue.segment_id,
                issue.element,
                issue.suggestion,
                issue.profile,
                issue.transaction_index,
                issue.transaction_control_number,
            ]
        )

    output = BytesIO()
    workbook.save(output)
    observe_record_count(
        path=metrics_path,
        operation="validation_export_rows",
        count=len(payload.patients),
    )
    workbook_bytes = output.getvalue()
    logger.info(
        "validation_export_workbook_completed",
        extra={
            "correlation_id": correlation_id,
            "path": metrics_path,
            "patient_count": len(payload.patients),
            "issue_count": len(payload.issues),
            "workbook_bytes": len(workbook_bytes),
        },
    )
    return workbook_bytes


def _validation_summary_from_patients(payload: ValidateResponse) -> ValidationSummary:
    valid_patients = sum(1 for patient in payload.patients if patient.status == "valid")
    invalid_patients = sum(1 for patient in payload.patients if patient.status == "invalid")
    return ValidationSummary(
        total_patients=len(payload.patients),
        valid_patients=valid_patients,
        invalid_patients=invalid_patients,
    )


def _primary_plan_summary(result: EligibilityResult) -> str | None:
    for segment in result.eligibility_segments:
        if segment.plan_coverage_description:
            return segment.plan_coverage_description
    return None


def _all_eb01_codes(result: EligibilityResult) -> str:
    return ", ".join(segment.eligibility_code for segment in result.eligibility_segments)


def _all_eb03_service_types(result: EligibilityResult) -> str:
    service_types: list[str] = []
    for segment in result.eligibility_segments:
        if segment.service_type_codes:
            service_types.extend(segment.service_type_codes)
        elif segment.service_type_code:
            service_types.append(segment.service_type_code)
    return ", ".join(service_types)


def _benefit_entity_names(result: EligibilityResult) -> str:
    names: list[str] = []
    for entity in result.benefit_entities:
        name = entity.name or entity.description or entity.identifier
        if name:
            names.append(name)
    return ", ".join(names)


def _contact_summaries(result: EligibilityResult) -> str:
    contacts: list[str] = []
    for entity in result.benefit_entities:
        contacts.extend(entity.contacts)
    return ", ".join(contacts)


def _aaa_codes(result: EligibilityResult) -> str:
    return ", ".join(error.code for error in result.aaa_errors)
