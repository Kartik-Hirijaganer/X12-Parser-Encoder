"""DC Medicaid payer-profile validation rules."""

from __future__ import annotations

from datetime import date

from x12_edi_tools.models.loops import (
    Loop2000A_270,
    Loop2000A_271,
    Loop2000B_270,
    Loop2000B_271,
    Loop2000C_270,
    Loop2000C_271,
    Loop2110C_270,
)
from x12_edi_tools.models.segments import AAASegment, DTPSegment, EBSegment, EQSegment
from x12_edi_tools.models.transactions import (
    FunctionalGroup,
    Interchange,
    Transaction270,
    Transaction271,
)
from x12_edi_tools.payers.base import PayerProfile
from x12_edi_tools.payers.dc_medicaid.constants import (
    AAA_REASON_MESSAGES,
    AAA_REASON_SUGGESTIONS,
    DEFAULT_SERVICE_TYPE_CODE,
    ISA_RECEIVER_ID,
    MAX_BATCH_TRANSACTIONS,
    PAYER_ID,
    PAYER_NAME,
    PROFILE_NAME,
    RECEIVER_ID_QUALIFIER,
    VALID_SERVICE_TYPE_CODES,
)
from x12_edi_tools.payers.dc_medicaid.profile_270 import validate_270_dtp_placement
from x12_edi_tools.payers.dc_medicaid.search_criteria import evaluate_search_criteria
from x12_edi_tools.validator.base import (
    ValidationError,
    annotate_transaction_issues,
    as_list,
    issue,
    iter_transactions,
    normalize_str,
    parse_date_yyyymmdd,
    subtract_months,
)
from x12_edi_tools.validator.context import (
    MemberRegistryLookup,
    ProviderRegistryLookup,
    ValidationContext,
)


class DCMedicaidProfile(PayerProfile):
    """DC Medicaid profile pack for 270/271 eligibility transactions."""

    name = PROFILE_NAME
    snip7_enabled: bool = False

    def validate(
        self,
        interchange: Interchange,
        *,
        context: ValidationContext | None = None,
    ) -> list[ValidationError]:
        issues: list[ValidationError] = []

        issues.extend(self._validate_envelope_values(interchange))
        issues.extend(self._validate_transaction_limits(interchange))

        for tx_context in iter_transactions(interchange):
            transaction_issues: list[ValidationError] = []
            transaction = tx_context.transaction
            if isinstance(transaction, Transaction270):
                transaction_issues.extend(
                    self._validate_270_transaction(
                        transaction,
                        tx_context.functional_group_index,
                        tx_context.transaction_index,
                    )
                )
            elif isinstance(transaction, Transaction271):
                transaction_issues.extend(
                    self._validate_271_transaction(
                        transaction,
                        tx_context.functional_group_index,
                        tx_context.transaction_index,
                    )
                )
            issues.extend(annotate_transaction_issues(transaction_issues, tx_context))

        return issues

    def get_defaults(self) -> dict[str, object]:
        return {
            "payer_name": PAYER_NAME,
            "payer_id": PAYER_ID,
            "interchange_receiver_id": ISA_RECEIVER_ID,
            "receiver_id_qualifier": RECEIVER_ID_QUALIFIER,
            "default_service_type_code": DEFAULT_SERVICE_TYPE_CODE,
            "max_batch_size": MAX_BATCH_TRANSACTIONS,
        }

    def build_validation_context(
        self,
        *,
        provider_lookup: ProviderRegistryLookup | None = None,
        member_lookup: MemberRegistryLookup | None = None,
        correlation_id: str | None = None,
    ) -> ValidationContext:
        # Phase 5 will override this to raise PayerConfigurationError when either
        # lookup is None (CG \u00a73.2). Phase 0 returns a permissive context so the
        # 270/271 test suite continues to pass without SNIP 7 wiring.
        return ValidationContext(
            provider_lookup=provider_lookup,
            member_lookup=member_lookup,
            correlation_id=correlation_id,
        )

    def get_claim_defaults(self, transaction: str) -> dict[str, object]:
        raise NotImplementedError("Phase 5 \u2014 DC Medicaid claim defaults")

    def get_remit_overrides(self) -> dict[str, object]:
        raise NotImplementedError("Phase 5 \u2014 DC Medicaid remittance overrides")

    def _validate_envelope_values(self, interchange: Interchange) -> list[ValidationError]:
        issues: list[ValidationError] = []

        receiver_id = normalize_str(getattr(getattr(interchange, "isa", None), "receiver_id", None))
        if receiver_id and receiver_id.strip() != ISA_RECEIVER_ID:
            issues.append(
                issue(
                    level=self.name,
                    code="DCM_INVALID_ISA08",
                    message=(
                        f"ISA08 must be '{ISA_RECEIVER_ID}' for DC Medicaid, got "
                        f"'{receiver_id.strip()}'."
                    ),
                    location="ISA.08",
                    segment_id="ISA",
                    element="08",
                    suggestion="Set ISA08 to the DC Medicaid receiver ID 'DCMEDICAID'.",
                    profile=self.name,
                )
            )

        for group_index, group in enumerate(as_list(getattr(interchange, "functional_groups", []))):
            if not isinstance(group, FunctionalGroup):
                continue
            gs_receiver = normalize_str(
                getattr(getattr(group, "gs", None), "application_receiver_code", None)
            )
            if gs_receiver != PAYER_ID:
                issues.append(
                    issue(
                        level=self.name,
                        code="DCM_INVALID_GS03",
                        message=(
                            f"GS03 must be '{PAYER_ID}' for DC Medicaid, got '{gs_receiver or ''}'."
                        ),
                        location=f"FunctionalGroup[{group_index}].GS.03",
                        segment_id="GS",
                        element="03",
                        suggestion="Set GS03 to DCMEDICAID.",
                        profile=self.name,
                    )
                )

        return issues

    def _validate_transaction_limits(self, interchange: Interchange) -> list[ValidationError]:
        issues: list[ValidationError] = []
        total_transactions = 0
        for group in as_list(getattr(interchange, "functional_groups", [])):
            if isinstance(group, FunctionalGroup):
                total_transactions += len(as_list(group.transactions))

        if total_transactions > MAX_BATCH_TRANSACTIONS:
            issues.append(
                issue(
                    level=self.name,
                    code="DCM_BATCH_LIMIT_EXCEEDED",
                    message=(
                        f"DC Medicaid accepts at most {MAX_BATCH_TRANSACTIONS} transactions per "
                        f"interchange, got {total_transactions}."
                    ),
                    location="GS",
                    suggestion=(
                        "Split the batch into multiple interchanges of 5000 or fewer transactions."
                    ),
                    profile=self.name,
                )
            )
        return issues

    def _validate_270_transaction(
        self,
        transaction: Transaction270,
        group_index: int,
        transaction_index: int,
    ) -> list[ValidationError]:
        issues: list[ValidationError] = []
        prefix = f"FunctionalGroup[{group_index}].Transaction[{transaction_index}]"

        loop_2000a = getattr(transaction, "loop_2000a", None)
        if not isinstance(loop_2000a, Loop2000A_270):
            return issues

        issues.extend(
            self._validate_payer_nm1(
                getattr(getattr(loop_2000a, "loop_2100a", None), "nm1", None),
                location=f"{prefix}.Loop2100A.NM1",
            )
        )

        anchor_date = _transaction_anchor_date(transaction)
        for receiver_index, receiver_loop in enumerate(as_list(loop_2000a.loop_2000b)):
            if not isinstance(receiver_loop, Loop2000B_270):
                continue
            for subscriber_index, subscriber_loop in enumerate(as_list(receiver_loop.loop_2000c)):
                if not isinstance(subscriber_loop, Loop2000C_270):
                    continue
                issues.extend(
                    self._validate_hl_codes(
                        getattr(subscriber_loop, "hl", None),
                        location=f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}].HL",
                    )
                )
                issues.extend(
                    self._validate_search_criteria(
                        subscriber_loop,
                        location=f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}]",
                    )
                )
                issues.extend(
                    validate_270_dtp_placement(
                        subscriber_loop,
                        location=(
                            f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}]"
                        ),
                        profile=self.name,
                    )
                )
                issues.extend(
                    self._validate_2100c_dates(
                        subscriber_loop,
                        anchor_date=anchor_date,
                        location=(
                            f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}]"
                        ),
                    )
                )
                for inquiry_index, inquiry_loop in enumerate(as_list(subscriber_loop.loop_2110c)):
                    issues.extend(
                        self._validate_2110c_dates(
                            inquiry_loop,
                            anchor_date=anchor_date,
                            location=(
                                f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                                f"[{subscriber_index}].Loop2110C[{inquiry_index}]"
                            ),
                        )
                    )
                    issues.extend(
                        self._validate_2110c_service_types(
                            inquiry_loop,
                            location=(
                                f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                                f"[{subscriber_index}].Loop2110C[{inquiry_index}]"
                            ),
                        )
                    )

        return issues

    def _validate_271_transaction(
        self,
        transaction: Transaction271,
        group_index: int,
        transaction_index: int,
    ) -> list[ValidationError]:
        issues: list[ValidationError] = []
        prefix = f"FunctionalGroup[{group_index}].Transaction[{transaction_index}]"

        loop_2000a = getattr(transaction, "loop_2000a", None)
        if not isinstance(loop_2000a, Loop2000A_271):
            return issues

        issues.extend(
            self._validate_payer_nm1(
                getattr(getattr(loop_2000a, "loop_2100a", None), "nm1", None),
                location=f"{prefix}.Loop2100A.NM1",
            )
        )
        issues.extend(
            self._map_aaa_segments(
                as_list(loop_2000a.aaa_segments),
                location=f"{prefix}.Loop2000A.AAA",
            )
        )

        anchor_date = _transaction_anchor_date(transaction)
        for receiver_index, receiver_loop in enumerate(as_list(loop_2000a.loop_2000b)):
            if not isinstance(receiver_loop, Loop2000B_271):
                continue
            issues.extend(
                self._map_aaa_segments(
                    as_list(receiver_loop.aaa_segments),
                    location=f"{prefix}.Loop2000B[{receiver_index}].AAA",
                )
            )
            for subscriber_index, subscriber_loop in enumerate(as_list(receiver_loop.loop_2000c)):
                if not isinstance(subscriber_loop, Loop2000C_271):
                    continue
                issues.extend(
                    self._validate_hl_codes(
                        getattr(subscriber_loop, "hl", None),
                        location=f"{prefix}.Loop2000B[{receiver_index}].Loop2000C[{subscriber_index}].HL",
                    )
                )
                issues.extend(
                    self._map_aaa_segments(
                        as_list(subscriber_loop.aaa_segments),
                        location=(
                            f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                            f"[{subscriber_index}].AAA"
                        ),
                    )
                )
                issues.extend(
                    self._map_aaa_segments(
                        as_list(
                            getattr(
                                getattr(subscriber_loop, "loop_2100c", None),
                                "aaa_segments",
                                [],
                            )
                        ),
                        location=(
                            f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                            f"[{subscriber_index}].Loop2100C.AAA"
                        ),
                    )
                )
                for inquiry_index, inquiry_loop in enumerate(as_list(subscriber_loop.loop_2110c)):
                    issues.extend(
                        self._validate_2110c_dates(
                            inquiry_loop,
                            anchor_date=anchor_date,
                            location=(
                                f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                                f"[{subscriber_index}].Loop2110C[{inquiry_index}]"
                            ),
                        )
                    )
                    issues.extend(
                        self._validate_2110c_service_types(
                            inquiry_loop,
                            location=(
                                f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                                f"[{subscriber_index}].Loop2110C[{inquiry_index}]"
                            ),
                        )
                    )
                    issues.extend(
                        self._map_aaa_segments(
                            as_list(getattr(inquiry_loop, "aaa_segments", [])),
                            location=(
                                f"{prefix}.Loop2000B[{receiver_index}].Loop2000C"
                                f"[{subscriber_index}].Loop2110C[{inquiry_index}].AAA"
                            ),
                        )
                    )

        return issues

    def _validate_payer_nm1(self, nm1: object, *, location: str) -> list[ValidationError]:
        issues: list[ValidationError] = []
        last_name = normalize_str(getattr(nm1, "last_name", None))
        if last_name != PAYER_NAME:
            issues.append(
                issue(
                    level=self.name,
                    code="DCM_INVALID_PAYER_NAME",
                    message=f"Loop 2100A NM103 must be '{PAYER_NAME}', got '{last_name or ''}'.",
                    location=f"{location}.03",
                    segment_id="NM1",
                    element="03",
                    suggestion="Set payer NM103 to DC MEDICAID.",
                    profile=self.name,
                )
            )

        payer_id = normalize_str(getattr(nm1, "id_code", None))
        if payer_id != PAYER_ID:
            issues.append(
                issue(
                    level=self.name,
                    code="DCM_INVALID_PAYER_ID",
                    message=f"Loop 2100A NM109 must be '{PAYER_ID}', got '{payer_id or ''}'.",
                    location=f"{location}.09",
                    segment_id="NM1",
                    element="09",
                    suggestion="Set payer NM109 to DCMEDICAID.",
                    profile=self.name,
                )
            )

        return issues

    def _validate_hl_codes(self, hl: object, *, location: str) -> list[ValidationError]:
        level_code = normalize_str(getattr(hl, "hierarchical_level_code", None))
        if level_code != "23":
            return []
        return [
            issue(
                level=self.name,
                code="DCM_DEPENDENT_LOOP_NOT_ALLOWED",
                message="DC Medicaid v1 does not support dependent subscriber loops (HL03=23).",
                location=f"{location}.03",
                segment_id="HL",
                element="03",
                suggestion="Use subscriber-only 22 loops for DC Medicaid eligibility transactions.",
                profile=self.name,
            )
        ]

    def _validate_search_criteria(
        self,
        subscriber_loop: Loop2000C_270,
        *,
        location: str,
    ) -> list[ValidationError]:
        evaluation = evaluate_search_criteria(subscriber_loop)
        if evaluation.is_valid:
            return []
        return [
            issue(
                level=self.name,
                code="DCM_INVALID_SEARCH_CRITERIA",
                message=(
                    "DC Medicaid subscriber search criteria are incomplete. Present criteria: "
                    f"{evaluation.describe()}."
                ),
                location=location,
                suggestion=(
                    "Provide member ID plus two supporting identifiers, or at least two of "
                    "name, DOB, and SSN."
                ),
                profile=self.name,
            )
        ]

    def _validate_2100c_dates(
        self,
        subscriber_loop: Loop2000C_270,
        *,
        anchor_date: date,
        location: str,
    ) -> list[ValidationError]:
        return self._validate_dtp_date_bounds(
            subscriber_loop.loop_2100c.dtp_segments,
            anchor_date=anchor_date,
            location=f"{location}.Loop2100C",
        )

    def _validate_2110c_dates(
        self,
        inquiry_loop: Loop2110C_270,
        *,
        anchor_date: date,
        location: str,
    ) -> list[ValidationError]:
        return self._validate_dtp_date_bounds(
            inquiry_loop.dtp_segments,
            anchor_date=anchor_date,
            location=location,
        )

    def _validate_dtp_date_bounds(
        self,
        dtp_segments: list[DTPSegment],
        *,
        anchor_date: date,
        location: str,
    ) -> list[ValidationError]:
        issues: list[ValidationError] = []
        earliest_allowed = subtract_months(anchor_date, 13)

        for dtp_index, dtp in enumerate(dtp_segments):
            if normalize_str(getattr(dtp, "date_time_period_format_qualifier", None)) != "D8":
                continue
            service_date_text = normalize_str(getattr(dtp, "date_time_period", None))
            service_date = parse_date_yyyymmdd(service_date_text or "")
            if service_date is None:
                continue
            if service_date > anchor_date:
                issues.append(
                    issue(
                        level=self.name,
                        code="DCM_FUTURE_SERVICE_DATE",
                        message=(
                            f"Service date '{service_date_text}' is in the future for a DC "
                            "Medicaid eligibility request."
                        ),
                        location=f"{location}.DTP[{dtp_index}].03",
                        segment_id="DTP",
                        element="03",
                        suggestion=(
                            "Use the transaction date or a prior date within the last 13 months."
                        ),
                        profile=self.name,
                    )
                )
            if service_date < earliest_allowed:
                issues.append(
                    issue(
                        level=self.name,
                        code="DCM_SERVICE_DATE_TOO_OLD",
                        message=(
                            f"Service date '{service_date_text}' is older than the DC Medicaid "
                            "13-month historical limit."
                        ),
                        location=f"{location}.DTP[{dtp_index}].03",
                        segment_id="DTP",
                        element="03",
                        suggestion="Use a service date within the last 13 months.",
                        profile=self.name,
                    )
                )

        return issues

    def _validate_2110c_service_types(
        self,
        inquiry_loop: object,
        *,
        location: str,
    ) -> list[ValidationError]:
        issues: list[ValidationError] = []

        for eq_index, eq in enumerate(as_list(getattr(inquiry_loop, "eq_segments", []))):
            if not isinstance(eq, EQSegment):
                continue
            service_type = normalize_str(getattr(eq, "service_type_code", None))
            if service_type not in VALID_SERVICE_TYPE_CODES:
                issues.append(
                    issue(
                        level=self.name,
                        code="DCM_INVALID_SERVICE_TYPE",
                        message=(
                            f"Service type code '{service_type or ''}' is not allowed by the "
                            "DC Medicaid profile."
                        ),
                        location=f"{location}.EQ[{eq_index}].01",
                        segment_id="EQ",
                        element="01",
                        suggestion="Use a DC Medicaid Appendix A.1 service type code.",
                        profile=self.name,
                    )
                )

        for eb_index, eb in enumerate(as_list(getattr(inquiry_loop, "eb_segments", []))):
            if not isinstance(eb, EBSegment):
                continue
            service_type = normalize_str(getattr(eb, "service_type_code", None))
            if service_type is not None and service_type not in VALID_SERVICE_TYPE_CODES:
                issues.append(
                    issue(
                        level=self.name,
                        code="DCM_INVALID_SERVICE_TYPE",
                        message=(
                            f"Service type code '{service_type}' is not allowed by the "
                            "DC Medicaid profile."
                        ),
                        location=f"{location}.EB[{eb_index}].03",
                        segment_id="EB",
                        element="03",
                        suggestion="Use a DC Medicaid Appendix A.1 service type code.",
                        profile=self.name,
                    )
                )

        return issues

    def _map_aaa_segments(self, segments: list[object], *, location: str) -> list[ValidationError]:
        issues: list[ValidationError] = []

        for aaa_index, segment in enumerate(segments):
            if not isinstance(segment, AAASegment):
                continue
            reason_code = normalize_str(getattr(segment, "reject_reason_code", None))
            mapped_message = AAA_REASON_MESSAGES.get(reason_code or "")
            if not mapped_message:
                continue
            issues.append(
                issue(
                    severity="info",
                    level=self.name,
                    code=f"DCM_AAA_REJECT_{reason_code}",
                    message=f"AAA reject code {reason_code}: {mapped_message}.",
                    location=f"{location}[{aaa_index}].03",
                    segment_id="AAA",
                    element="03",
                    suggestion=AAA_REASON_SUGGESTIONS.get(reason_code or ""),
                    profile=self.name,
                )
            )

        return issues


def _transaction_anchor_date(transaction: Transaction270 | Transaction271) -> date:
    bht_date = normalize_str(getattr(getattr(transaction, "bht", None), "date", None))
    parsed = parse_date_yyyymmdd(bht_date or "")
    return parsed if parsed is not None else date.today()
