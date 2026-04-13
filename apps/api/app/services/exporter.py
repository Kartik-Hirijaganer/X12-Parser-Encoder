"""Excel export services."""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook  # type: ignore[import-untyped]
from openpyxl.styles import Font  # type: ignore[import-untyped]

from app.core.logging import get_logger
from app.core.metrics import observe_record_count
from app.schemas.export import ExportWorkbookRequest

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
    summary_sheet["A6"] = "Unknown"
    summary_sheet["B6"] = payload.summary.unknown
    for cell in summary_sheet["A"][:6]:
        cell.font = Font(bold=True)

    results_sheet = workbook.create_sheet("Eligibility Results")
    headers = [
        "member_name",
        "member_id",
        "overall_status",
        "eligibility_codes",
        "service_type_codes",
        "benefit_entities",
        "aaa_errors",
    ]
    results_sheet.append(headers)
    for cell in results_sheet[1]:
        cell.font = Font(bold=True)
    results_sheet.freeze_panes = "A2"

    for result in payload.results:
        eligibility_codes = ", ".join(
            segment.eligibility_code for segment in result.eligibility_segments
        )
        service_types = ", ".join(
            segment.service_type_code
            for segment in result.eligibility_segments
            if segment.service_type_code
        )
        benefit_entities = ", ".join(entity.identifier for entity in result.benefit_entities)
        aaa_errors = ", ".join(error.code for error in result.aaa_errors)
        results_sheet.append(
            [
                result.member_name,
                result.member_id,
                result.overall_status,
                eligibility_codes,
                service_types,
                benefit_entities,
                aaa_errors,
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
