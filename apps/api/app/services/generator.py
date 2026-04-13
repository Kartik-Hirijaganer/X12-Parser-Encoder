"""270 generation services."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from io import BytesIO
from itertools import count
from typing import cast
from zipfile import ZIP_DEFLATED, ZipFile

from x12_edi_tools import encode, parse
from x12_edi_tools.common.enums import (
    AcknowledgmentRequested,
    EntityIdentifierCode,
    GenderCode,
    HierarchicalLevelCode,
    ServiceTypeCode,
    UsageIndicator,
)
from x12_edi_tools.config import SubmitterConfig
from x12_edi_tools.models import (
    BHTSegment,
    DMGSegment,
    DTPSegment,
    EQSegment,
    FunctionalGroup,
    GESegment,
    GSSegment,
    HLSegment,
    IEASegment,
    Interchange,
    ISASegment,
    Loop2000A_270,
    Loop2000B_270,
    Loop2000C_270,
    Loop2100A_270,
    Loop2100B_270,
    Loop2100C_270,
    Loop2110C_270,
    NM1Segment,
    PERSegment,
    PRVSegment,
    REFSegment,
    SESegment,
    STSegment,
    Transaction270,
    Transaction271,
    TRNSegment,
)
from x12_edi_tools.parser import ParseResult
from x12_edi_tools.payers import get_profile

from app.core.logging import get_logger
from app.core.metrics import observe_record_count, observe_segment_count
from app.schemas.common import ArchiveEntry, ControlNumbers, PatientRecord
from app.schemas.generate import GenerateResponse
from app.services.patients import normalize_patient_rows

IMPLEMENTATION_REFERENCE = "005010X279A1"
logger = get_logger(__name__)


def generate_270_response(
    *,
    config: SubmitterConfig,
    patients: list[dict[str, object]],
    profile_name: str,
    correlation_id: str | None = None,
    metrics_path: str = "/api/v1/generate",
) -> GenerateResponse:
    """Generate one or more X12 270 interchanges from normalized patients."""

    now = datetime.now()
    profile = get_profile(profile_name)
    normalized = normalize_patient_rows(
        patients,
        default_service_type_code=config.default_service_type_code,
        default_service_date=config.default_service_date,
        row_offset=1,
    )
    interchanges = _build_interchanges(
        patients=normalized.patients,
        config=config,
        payer_name=str(profile.get_defaults().get("payer_name", config.payer_name)),
        payer_id=str(profile.get_defaults().get("payer_id", config.payer_id)),
        now=now,
    )

    if not interchanges:
        observe_record_count(path=metrics_path, operation="generated_transactions", count=0)
        response = GenerateResponse(
            x12_content=None,
            transaction_count=0,
            segment_count=0,
            file_size_bytes=0,
            split_count=0,
            control_numbers=ControlNumbers(),
            errors=normalized.errors,
            partial=False,
        )
        logger.info(
            "generate_270_completed",
            extra={
                "correlation_id": correlation_id,
                "path": metrics_path,
                "transaction_count": 0,
                "segment_count": 0,
                "partial": False,
            },
        )
        return response

    encoded = encode(
        interchanges if len(interchanges) > 1 else interchanges[0],
        config=config,
        correlation_id=correlation_id,
    )
    rendered_documents = encoded if isinstance(encoded, list) else [encoded]
    parsed_documents = [
        parse(document, correlation_id=correlation_id) for document in rendered_documents
    ]
    generation_date = now.strftime("%Y%m%d")
    archive_entries = _archive_entries(
        parsed_documents,
        trading_partner_id=config.trading_partner_id,
        generation_date=generation_date,
    )
    total_transactions = sum(
        len(result.interchange.functional_groups[0].transactions) for result in parsed_documents
    )
    segment_count = sum(document.count("~") for document in rendered_documents)
    batch_summary_file_name = _build_batch_summary_file_name(
        trading_partner_id=config.trading_partner_id,
        generation_date=generation_date,
        primary_control_number=archive_entries[0].control_numbers.isa13,
    )
    batch_summary_text = _build_batch_summary_text(
        trading_partner_id=config.trading_partner_id,
        payer_name=str(profile.get_defaults().get("payer_name", config.payer_name)),
        payer_id=str(profile.get_defaults().get("payer_id", config.payer_id)),
        profile_name=profile_name,
        patients=normalized.patients,
        archive_entries=archive_entries,
        transaction_count=total_transactions,
        excluded_row_count=len(normalized.errors),
        generated_at=now,
    )
    observe_record_count(
        path=metrics_path,
        operation="generated_transactions",
        count=total_transactions,
    )
    observe_segment_count(
        path=metrics_path,
        operation="generated_segments",
        count=segment_count,
    )

    if len(rendered_documents) == 1:
        rendered_document = rendered_documents[0]
        response = GenerateResponse(
            x12_content=rendered_document,
            download_file_name=archive_entries[0].file_name,
            batch_summary_text=batch_summary_text,
            batch_summary_file_name=batch_summary_file_name,
            transaction_count=total_transactions,
            segment_count=segment_count,
            file_size_bytes=len(rendered_document.encode("utf-8")),
            split_count=1,
            control_numbers=archive_entries[0].control_numbers,
            archive_entries=archive_entries,
            errors=normalized.errors,
            partial=bool(normalized.errors),
        )
        logger.info(
            "generate_270_completed",
            extra={
                "correlation_id": correlation_id,
                "path": metrics_path,
                "transaction_count": total_transactions,
                "segment_count": segment_count,
                "split_count": 1,
                "partial": bool(normalized.errors),
            },
        )
        return response

    manifest = {
        "split_count": len(rendered_documents),
        "record_count": total_transactions,
        "excluded_row_count": len(normalized.errors),
        "batch_summary_file_name": batch_summary_file_name,
        "service_date_range": _service_date_range(normalized.patients),
        "files": [entry.model_dump() for entry in archive_entries],
    }
    zip_file_name = _build_zip_file_name(
        trading_partner_id=config.trading_partner_id,
        generation_date=generation_date,
        primary_control_number=archive_entries[0].control_numbers.isa13,
    )
    zip_payload = _build_zip_payload(
        documents=rendered_documents,
        archive_entries=archive_entries,
        manifest=manifest,
        batch_summary_file_name=batch_summary_file_name,
        batch_summary_text=batch_summary_text,
    )
    response = GenerateResponse(
        x12_content=None,
        zip_content_base64=base64.b64encode(zip_payload).decode("ascii"),
        download_file_name=zip_file_name,
        batch_summary_text=batch_summary_text,
        batch_summary_file_name=batch_summary_file_name,
        transaction_count=total_transactions,
        segment_count=segment_count,
        file_size_bytes=len(zip_payload),
        split_count=len(rendered_documents),
        control_numbers=archive_entries[0].control_numbers,
        archive_entries=archive_entries,
        manifest=manifest,
        errors=normalized.errors,
        partial=bool(normalized.errors),
    )
    logger.info(
        "generate_270_completed",
        extra={
            "correlation_id": correlation_id,
            "path": metrics_path,
            "transaction_count": total_transactions,
            "segment_count": segment_count,
            "split_count": len(rendered_documents),
            "partial": bool(normalized.errors),
        },
    )
    return response


def _build_interchanges(
    *,
    patients: list[PatientRecord],
    config: SubmitterConfig,
    payer_name: str,
    payer_id: str,
    now: datetime,
) -> list[Interchange]:
    date_yymmdd = now.strftime("%y%m%d")
    date_yyyymmdd = now.strftime("%Y%m%d")
    time_hhmm = now.strftime("%H%M")

    interchanges: list[Interchange] = []
    trace_numbers = count(start=1)
    transaction_numbers = count(start=1)

    for batch_index, batch in enumerate(_chunks(patients, config.max_batch_size), start=1):
        transactions = [
            _build_transaction(
                patient=patient,
                transaction_number=next(transaction_numbers),
                trace_number=next(trace_numbers),
                config=config,
                payer_name=payer_name,
                payer_id=payer_id,
                date_yyyymmdd=date_yyyymmdd,
                time_hhmm=time_hhmm,
            )
            for patient in batch
        ]

        isa = ISASegment(
            authorization_information_qualifier="00",
            authorization_information=" " * 10,
            security_information_qualifier="00",
            security_information=" " * 10,
            sender_id_qualifier=config.sender_id_qualifier,
            sender_id=f"{config.trading_partner_id:<15}"[:15],
            receiver_id_qualifier=config.receiver_id_qualifier,
            receiver_id=f"{config.interchange_receiver_id:<15}"[:15],
            interchange_date=date_yymmdd,
            interchange_time=time_hhmm,
            repetition_separator="^",
            control_version_number="00501",
            interchange_control_number="000000001",
            acknowledgment_requested=AcknowledgmentRequested(config.acknowledgment_requested),
            usage_indicator=UsageIndicator(config.usage_indicator),
            component_element_separator=":",
        )
        gs = GSSegment(
            functional_identifier_code="HS",
            application_sender_code=config.trading_partner_id,
            application_receiver_code=config.payer_id,
            date=date_yyyymmdd,
            time=time_hhmm,
            group_control_number=str(batch_index),
            responsible_agency_code="X",
            version_release_industry_identifier_code=IMPLEMENTATION_REFERENCE,
        )
        ge = GESegment(
            number_of_transaction_sets_included=len(transactions),
            group_control_number=str(batch_index),
        )
        iea = IEASegment(
            number_of_included_functional_groups=1,
            interchange_control_number="000000001",
        )
        typed_transactions = cast(list[Transaction270 | Transaction271], transactions)
        interchanges.append(
            Interchange(
                isa=isa,
                functional_groups=[FunctionalGroup(gs=gs, transactions=typed_transactions, ge=ge)],
                iea=iea,
            )
        )
    return interchanges


def _build_transaction(
    *,
    patient: PatientRecord,
    transaction_number: int,
    trace_number: int,
    config: SubmitterConfig,
    payer_name: str,
    payer_id: str,
    date_yyyymmdd: str,
    time_hhmm: str,
) -> Transaction270:
    control_number = f"{transaction_number:04d}"
    subscriber_ref_segments = []
    if patient.ssn:
        subscriber_ref_segments.append(
            REFSegment(
                reference_identification_qualifier="SY",
                reference_identification=patient.ssn,
            )
        )

    dtp_period_format = "D8"
    dtp_period = patient.service_date
    if patient.service_date_end:
        dtp_period_format = "RD8"
        dtp_period = f"{patient.service_date}-{patient.service_date_end}"

    provider_loop = Loop2100B_270(
        nm1=NM1Segment(
            entity_identifier_code=EntityIdentifierCode.PROVIDER,
            entity_type_qualifier=config.provider_entity_type,
            last_name=config.organization_name.upper(),
            id_code_qualifier="XX",
            id_code=config.provider_npi,
        ),
        prv=_provider_prv_segment(config.provider_taxonomy_code),
        per=_provider_per_segment(config.contact_name, config.contact_phone, config.contact_email),
    )

    return Transaction270(
        st=STSegment(
            transaction_set_identifier_code="270",
            transaction_set_control_number=control_number,
            implementation_convention_reference=IMPLEMENTATION_REFERENCE,
        ),
        bht=BHTSegment(
            hierarchical_structure_code="0022",
            transaction_set_purpose_code="13",
            reference_identification=f"BATCH{transaction_number:08d}",
            date=date_yyyymmdd,
            time=time_hhmm,
        ),
        loop_2000a=Loop2000A_270(
            hl=HLSegment(
                hierarchical_id_number="1",
                hierarchical_parent_id_number=None,
                hierarchical_level_code=HierarchicalLevelCode.INFORMATION_SOURCE,
                hierarchical_child_code="1",
            ),
            loop_2100a=Loop2100A_270(
                nm1=NM1Segment(
                    entity_identifier_code=EntityIdentifierCode.PAYER,
                    entity_type_qualifier="2",
                    last_name=payer_name,
                    id_code_qualifier="PI",
                    id_code=payer_id,
                )
            ),
            loop_2000b=[
                Loop2000B_270(
                    hl=HLSegment(
                        hierarchical_id_number="2",
                        hierarchical_parent_id_number="1",
                        hierarchical_level_code=HierarchicalLevelCode.INFORMATION_RECEIVER,
                        hierarchical_child_code="1",
                    ),
                    loop_2100b=provider_loop,
                    loop_2000c=[
                        Loop2000C_270(
                            hl=HLSegment(
                                hierarchical_id_number="3",
                                hierarchical_parent_id_number="2",
                                hierarchical_level_code=HierarchicalLevelCode.SUBSCRIBER,
                                hierarchical_child_code="0",
                            ),
                            trn=TRNSegment(
                                trace_type_code="1",
                                reference_identification_1=f"TRACE{trace_number:07d}",
                                originating_company_identifier=config.provider_npi,
                            ),
                            loop_2100c=Loop2100C_270(
                                nm1=NM1Segment(
                                    entity_identifier_code=EntityIdentifierCode.SUBSCRIBER,
                                    entity_type_qualifier="1",
                                    last_name=patient.last_name,
                                    first_name=patient.first_name,
                                    id_code_qualifier="MI" if patient.member_id else None,
                                    id_code=patient.member_id,
                                ),
                                dmg=DMGSegment(
                                    date_time_period_format_qualifier="D8",
                                    date_time_period=patient.date_of_birth,
                                    gender_code=GenderCode(patient.gender),
                                ),
                                ref_segments=subscriber_ref_segments,
                            ),
                            loop_2110c=[
                                Loop2110C_270(
                                    eq_segments=[
                                        EQSegment(
                                            service_type_code=ServiceTypeCode(
                                                patient.service_type_code
                                            )
                                        )
                                    ],
                                    dtp_segments=[
                                        DTPSegment(
                                            date_time_qualifier="291",
                                            date_time_period_format_qualifier=dtp_period_format,
                                            date_time_period=dtp_period,
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        ),
        se=SESegment(
            number_of_included_segments=13,
            transaction_set_control_number=control_number,
        ),
    )


def _provider_prv_segment(taxonomy_code: str | None) -> PRVSegment | None:
    if not taxonomy_code:
        return None
    return PRVSegment(
        provider_code="BI",
        reference_identification_qualifier="PXC",
        reference_identification=taxonomy_code,
    )


def _provider_per_segment(
    contact_name: str | None,
    contact_phone: str | None,
    contact_email: str | None,
) -> PERSegment | None:
    if not any([contact_name, contact_phone, contact_email]):
        return None
    return PERSegment(
        contact_function_code="IC",
        name=contact_name,
        communication_number_qualifier_1="TE" if contact_phone else None,
        communication_number_1=contact_phone,
        communication_number_qualifier_2="EM" if contact_email else None,
        communication_number_2=contact_email,
    )


def _chunks(items: list[PatientRecord], size: int) -> list[list[PatientRecord]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _archive_entries(
    parsed_documents: list[ParseResult],
    *,
    trading_partner_id: str,
    generation_date: str,
) -> list[ArchiveEntry]:
    entries: list[ArchiveEntry] = []
    record_start = 1
    for parsed in parsed_documents:
        group = parsed.interchange.functional_groups[0]
        transactions = group.transactions
        st_controls = [
            transaction.st.transaction_set_control_number for transaction in transactions
        ]
        isa_control_number = parsed.interchange.isa.interchange_control_number
        entries.append(
            ArchiveEntry(
                file_name=_build_document_file_name(
                    trading_partner_id=trading_partner_id,
                    generation_date=generation_date,
                    isa_control_number=isa_control_number,
                ),
                record_range_start=record_start,
                record_range_end=record_start + len(transactions) - 1,
                control_numbers=ControlNumbers(
                    isa13=isa_control_number,
                    gs06=group.gs.group_control_number,
                    st02_range=st_controls,
                ),
            )
        )
        record_start += len(transactions)
    return entries


def _build_document_file_name(
    *,
    trading_partner_id: str,
    generation_date: str,
    isa_control_number: str | None,
) -> str:
    return (
        f"{_sanitize_filename_token(trading_partner_id)}_270_{generation_date}_"
        f"{isa_control_number or 'unknown'}.x12"
    )


def _build_zip_file_name(
    *,
    trading_partner_id: str,
    generation_date: str,
    primary_control_number: str | None,
) -> str:
    return (
        f"{_sanitize_filename_token(trading_partner_id)}_270_batch_{generation_date}_"
        f"{primary_control_number or 'unknown'}.zip"
    )


def _build_batch_summary_file_name(
    *,
    trading_partner_id: str,
    generation_date: str,
    primary_control_number: str | None,
) -> str:
    return (
        f"{_sanitize_filename_token(trading_partner_id)}_270_{generation_date}_"
        f"{primary_control_number or 'unknown'}_summary.txt"
    )


def _sanitize_filename_token(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip().upper()).strip("_")
    return sanitized or "SUBMITTER"


def _service_date_range(patients: list[PatientRecord]) -> str:
    service_dates = [patient.service_date for patient in patients]
    service_dates.extend(
        patient.service_date_end for patient in patients if patient.service_date_end is not None
    )
    if not service_dates:
        return "N/A"

    start = min(service_dates)
    end = max(service_dates)
    if start == end:
        return _format_yyyymmdd(start)
    return f"{_format_yyyymmdd(start)} to {_format_yyyymmdd(end)}"


def _format_yyyymmdd(value: str) -> str:
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return value


def _format_st_range(control_numbers: list[str]) -> str:
    if not control_numbers:
        return "N/A"
    if len(control_numbers) == 1:
        return control_numbers[0]
    return f"{control_numbers[0]}-{control_numbers[-1]}"


def _build_batch_summary_text(
    *,
    trading_partner_id: str,
    payer_name: str,
    payer_id: str,
    profile_name: str,
    patients: list[PatientRecord],
    archive_entries: list[ArchiveEntry],
    transaction_count: int,
    excluded_row_count: int,
    generated_at: datetime,
) -> str:
    lines = [
        "Submission Batch Summary",
        "========================",
        f"Generated at: {generated_at.strftime('%Y-%m-%d %H:%M')}",
        f"Trading Partner ID: {trading_partner_id}",
        f"Payer: {payer_name} ({payer_id})",
        f"Profile: {profile_name}",
        f"Record count: {transaction_count}",
        f"Excluded rows: {excluded_row_count}",
        f"Split count: {len(archive_entries)}",
        f"Service date range: {_service_date_range(patients)}",
        "",
        "Control numbers",
        "---------------",
    ]

    for entry in archive_entries:
        lines.append(
            f"- {entry.file_name}: ISA13 {entry.control_numbers.isa13 or 'N/A'}, "
            f"GS06 {entry.control_numbers.gs06 or 'N/A'}, "
            f"ST02 {_format_st_range(entry.control_numbers.st02_range)}"
        )

    lines.extend(
        [
            "",
            "Submission reminder",
            "-------------------",
            "Submit this batch to Gainwell through the channel defined in your trading "
            "partner agreement, typically the web portal or SFTP.",
            "Keep the generated filename and ISA13 control number together for audit "
            "trail matching.",
        ]
    )
    return "\n".join(lines)


def _build_zip_payload(
    *,
    documents: list[str],
    archive_entries: list[ArchiveEntry],
    manifest: dict[str, object],
    batch_summary_file_name: str,
    batch_summary_text: str,
) -> bytes:
    output = BytesIO()
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as zip_file:
        for entry, document in zip(archive_entries, documents, strict=True):
            zip_file.writestr(entry.file_name, document)
        zip_file.writestr(batch_summary_file_name, batch_summary_text)
        zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))
    return output.getvalue()
