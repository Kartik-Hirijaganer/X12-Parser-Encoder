"""Per-patient projection for 270 validation results."""

from __future__ import annotations

from collections import defaultdict
from enum import Enum

from x12_edi_tools.models.loops import Loop2000A_270, Loop2000B_270, Loop2000C_270, Loop2110C_270
from x12_edi_tools.models.transactions import Interchange, Transaction270
from x12_edi_tools.validator.base import as_list

from app.schemas.common import ValidationIssue
from app.schemas.validate import PatientValidationRow


def project_patient_rows(
    interchange: Interchange,
    issues: list[ValidationIssue],
) -> list[PatientValidationRow]:
    """Project one validation row per parsed subscriber loop."""

    issues_by_transaction: dict[int, list[ValidationIssue]] = defaultdict(list)
    for validation_issue in issues:
        if validation_issue.transaction_index is not None:
            issues_by_transaction[validation_issue.transaction_index].append(validation_issue)

    rows: list[PatientValidationRow] = []
    transaction_index = 0
    for group in as_list(interchange.functional_groups):
        for transaction in as_list(getattr(group, "transactions", [])):
            if isinstance(transaction, Transaction270):
                rows.extend(
                    _project_transaction_rows(
                        transaction,
                        issues_by_transaction.get(transaction_index, []),
                        row_start=len(rows),
                    )
                )
            transaction_index += 1
    return rows


def _project_transaction_rows(
    transaction: Transaction270,
    issues: list[ValidationIssue],
    *,
    row_start: int,
) -> list[PatientValidationRow]:
    loop_2000a = getattr(transaction, "loop_2000a", None)
    if not isinstance(loop_2000a, Loop2000A_270):
        return []

    rows: list[PatientValidationRow] = []
    for receiver_loop in as_list(loop_2000a.loop_2000b):
        if not isinstance(receiver_loop, Loop2000B_270):
            continue
        for subscriber_loop in as_list(receiver_loop.loop_2000c):
            if not isinstance(subscriber_loop, Loop2000C_270):
                continue
            rows.append(
                _project_subscriber_row(
                    transaction,
                    subscriber_loop,
                    issues,
                    index=row_start + len(rows),
                )
            )
    return rows


def _project_subscriber_row(
    transaction: Transaction270,
    subscriber_loop: Loop2000C_270,
    issues: list[ValidationIssue],
    *,
    index: int,
) -> PatientValidationRow:
    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    nm1 = subscriber_loop.loop_2100c.nm1
    return PatientValidationRow(
        index=index,
        transaction_control_number=transaction.st.transaction_set_control_number,
        member_name=_member_name(nm1),
        member_id=nm1.id_code,
        service_date=_service_date(subscriber_loop),
        status="invalid" if error_count else "valid",
        error_count=error_count,
        warning_count=warning_count,
        issues=list(issues),
    )


def _member_name(nm1: object) -> str:
    name = ", ".join(
        part
        for part in (
            getattr(nm1, "last_name", None),
            getattr(nm1, "first_name", None),
        )
        if part
    )
    return name or "UNKNOWN"


def _service_date(subscriber_loop: Loop2000C_270) -> str | None:
    for dtp in as_list(subscriber_loop.loop_2100c.dtp_segments):
        if _code(getattr(dtp, "date_time_qualifier", None)) == "291":
            return getattr(dtp, "date_time_period", None)

    for inquiry_loop in as_list(subscriber_loop.loop_2110c):
        if not isinstance(inquiry_loop, Loop2110C_270):
            continue
        for dtp in as_list(inquiry_loop.dtp_segments):
            if _code(getattr(dtp, "date_time_qualifier", None)) == "291":
                return getattr(dtp, "date_time_period", None)
    return None


def _code(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)
