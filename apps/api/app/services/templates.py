"""Template rendering helpers."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, status
from openpyxl import Workbook  # type: ignore[import-untyped]
from openpyxl.styles import Font  # type: ignore[import-untyped]

from app.services.patients import CANONICAL_COLUMNS

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
CSV_TEMPLATE_PATH = TEMPLATE_DIR / "eligibility_template.csv"
SPEC_PATH = TEMPLATE_DIR / "template_spec.md"


def get_template_bytes(name: str) -> tuple[bytes, str]:
    """Return the requested template bytes and media type."""

    normalized = name.strip()
    if normalized == "eligibility_template.csv":
        return _csv_template_bytes(), "text/csv; charset=utf-8"
    if normalized == "eligibility_template.xlsx":
        return _xlsx_template_bytes(), (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    if normalized == "template_spec.md":
        return SPEC_PATH.read_bytes(), "text/markdown; charset=utf-8"

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"message": f"Unknown template '{name}'."},
    )


def _csv_template_bytes() -> bytes:
    if CSV_TEMPLATE_PATH.exists():
        return CSV_TEMPLATE_PATH.read_bytes()
    return (",".join(CANONICAL_COLUMNS) + "\n").encode("utf-8")


def _xlsx_template_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Eligibility Template"
    sheet.append(CANONICAL_COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
