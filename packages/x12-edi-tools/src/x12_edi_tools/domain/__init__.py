"""Business-object domain models (X12-agnostic).

All classes here are framework-agnostic Pydantic v2 models. They describe
*what a claim or remittance is* rather than how X12 expresses it; wire-
format translation lives in ``builders/`` and ``readers/``.

These modules intentionally have no imports from ``x12_edi_tools.models``,
``x12_edi_tools.parser``, or ``x12_edi_tools.encoder`` — enforced by a
structural test in ``tests/test_domain/test_layering.py``.
"""

from __future__ import annotations

from x12_edi_tools.domain.acknowledgement import (
    Acknowledgement,
    AcknowledgementError,
    AcknowledgementKind,
    AcknowledgementStatus,
)
from x12_edi_tools.domain.adjustment import (
    Adjustment,
    AdjustmentGroupCode,
    CARCRARCMessage,
    ClaimAdjustmentReasonCode,
    RemarkCodeType,
    RemittanceAdviceRemarkCode,
)
from x12_edi_tools.domain.audit import (
    AuditOperation,
    AuditOutcome,
    TransactionAudit,
)
from x12_edi_tools.domain.claim import (
    BenefitsAssignmentCode,
    Claim,
    ClaimAdjustment,
    ClaimFrequencyCode,
    ClaimLine,
    ClaimSupportingInfo,
    ClaimSupportingInfoCategory,
    ClaimType,
    DateRange,
    ReleaseOfInformationCode,
)
from x12_edi_tools.domain.patient import (
    Patient,
    PatientAddress,
    PatientRelationship,
    Subscriber,
)
from x12_edi_tools.domain.payer import (
    Payer,
    PayerAddress,
    PayerIdQualifier,
    PayerResponsibility,
)
from x12_edi_tools.domain.provider import (
    AttendingProvider,
    BillingProvider,
    ProviderAddress,
    ProviderEntityType,
    ProviderRole,
    ReferringProvider,
    RenderingProvider,
    ServiceFacility,
    validate_npi,
)
from x12_edi_tools.domain.remittance import (
    ClaimFilingIndicator,
    ClaimStatusCode,
    PaymentMethodCode,
    ProviderAdjustmentReason,
    ProviderLevelAdjustment,
    Remittance,
    RemittanceClaim,
    RemittancePayment,
    RemittanceServiceLine,
)
from x12_edi_tools.domain.submission_batch import (
    ArchiveEntry,
    ControlNumbers,
    SubmissionBatch,
    TransactionType,
)

__all__ = [
    "Acknowledgement",
    "AcknowledgementError",
    "AcknowledgementKind",
    "AcknowledgementStatus",
    "Adjustment",
    "AdjustmentGroupCode",
    "ArchiveEntry",
    "AttendingProvider",
    "AuditOperation",
    "AuditOutcome",
    "BenefitsAssignmentCode",
    "BillingProvider",
    "CARCRARCMessage",
    "Claim",
    "ClaimAdjustment",
    "ClaimAdjustmentReasonCode",
    "ClaimFilingIndicator",
    "ClaimFrequencyCode",
    "ClaimLine",
    "ClaimStatusCode",
    "ClaimSupportingInfo",
    "ClaimSupportingInfoCategory",
    "ClaimType",
    "ControlNumbers",
    "DateRange",
    "Patient",
    "PatientAddress",
    "PatientRelationship",
    "Payer",
    "PayerAddress",
    "PayerIdQualifier",
    "PayerResponsibility",
    "PaymentMethodCode",
    "ProviderAddress",
    "ProviderAdjustmentReason",
    "ProviderEntityType",
    "ProviderLevelAdjustment",
    "ProviderRole",
    "ReferringProvider",
    "ReleaseOfInformationCode",
    "RemarkCodeType",
    "Remittance",
    "RemittanceAdviceRemarkCode",
    "RemittanceClaim",
    "RemittancePayment",
    "RemittanceServiceLine",
    "RenderingProvider",
    "ServiceFacility",
    "Subscriber",
    "SubmissionBatch",
    "TransactionAudit",
    "TransactionType",
    "validate_npi",
]
