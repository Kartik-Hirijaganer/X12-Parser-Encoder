"""Enum values shared by typed X12 models."""

from enum import StrEnum


class UsageIndicator(StrEnum):
    TEST = "T"
    PRODUCTION = "P"


class AcknowledgmentRequested(StrEnum):
    NO = "0"
    YES = "1"


class EntityIdentifierCode(StrEnum):
    """NM101 entity identifiers used by the initial 270/271 workflow."""

    PAYER = "PR"
    PROVIDER = "1P"
    SUBSCRIBER = "IL"


class HierarchicalLevelCode(StrEnum):
    """HL03 level codes used by 270/271 eligibility transactions."""

    INFORMATION_SOURCE = "20"
    INFORMATION_RECEIVER = "21"
    SUBSCRIBER = "22"


class EligibilityInfoCode(StrEnum):
    """EB01 values used by early eligibility response handling."""

    ACTIVE_COVERAGE = "1"
    ACTIVE_FULL_RISK_CAPITATION = "2"
    ACTIVE_SERVICES_CAPITATED = "3"
    ACTIVE_SERVICES_CAPITATED_TO_PCP = "4"
    ACTIVE_PENDING_INVESTIGATION = "5"
    INACTIVE = "6"
    INACTIVE_PENDING_ELIGIBILITY_UPDATE = "7"
    INACTIVE_PENDING_INVESTIGATION = "8"
    CO_INSURANCE = "A"
    CO_PAYMENT = "B"
    DEDUCTIBLE = "C"
    OUT_OF_POCKET = "G"
    CONTACT_FOLLOWING_ENTITY = "U"


class ServiceTypeCode(StrEnum):
    """Subset required by the DC Medicaid companion workflow."""

    MEDICAL_CARE = "1"
    HEALTH_BENEFIT_PLAN_COVERAGE = "30"
    CHIROPRACTIC = "33"
    DENTAL_CARE = "35"
    HOSPITAL = "47"
    HOSPITAL_INPATIENT = "48"
    HOSPITAL_OUTPATIENT = "50"
    EMERGENCY_SERVICES = "86"
    PHARMACY = "88"
    PROFESSIONAL_PHYSICIAN_VISIT_OFFICE = "98"
    VISION = "AL"
    MENTAL_HEALTH = "MH"
    URGENT_CARE = "UC"


class GenderCode(StrEnum):
    FEMALE = "F"
    MALE = "M"
    UNKNOWN = "U"


class AAARejectReasonCode(StrEnum):
    PROVIDER_NOT_ON_FILE = "51"
    DATE_OF_BIRTH_MISMATCH = "71"
    INVALID_MEMBER_ID = "72"
    INVALID_NAME = "73"
    SUBSCRIBER_INSURED_NOT_FOUND = "75"
