"""Excel export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.schemas.export import ExportWorkbookRequest
from app.services.exporter import build_workbook_bytes

router = APIRouter(tags=["export"])


@router.post("/export/xlsx")
async def export_xlsx(request: Request, payload: ExportWorkbookRequest) -> Response:
    """Export parsed eligibility results as an Excel workbook."""

    workbook_bytes = build_workbook_bytes(
        payload,
        correlation_id=request.state.correlation_id,
        metrics_path=request.url.path,
    )
    filename = payload.filename or "eligibility_results.xlsx"
    return Response(
        content=workbook_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
