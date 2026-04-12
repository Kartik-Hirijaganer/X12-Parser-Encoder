"""EB eligibility or benefit information segment."""

from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from x12_edi_tools.common.enums import EligibilityInfoCode, ServiceTypeCode
from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class EBSegment(X12Segment):
    segment_id: ClassVar[str] = "EB"
    _element_map: ClassVar[ElementMap] = {
        1: "eligibility_or_benefit_information",
        2: "coverage_level_code",
        3: "service_type_code",
        4: "insurance_type_code",
        5: "plan_coverage_description",
        6: "time_period_qualifier",
        7: "monetary_amount",
        8: "percent",
        9: "quantity_qualifier",
        10: "quantity",
        11: "authorization_or_certification_indicator",
        12: "in_plan_network_indicator",
        13: "procedure_identifier",
    }

    eligibility_or_benefit_information: EligibilityInfoCode
    coverage_level_code: str | None = None
    service_type_code: ServiceTypeCode | None = None
    insurance_type_code: str | None = None
    plan_coverage_description: str | None = None
    time_period_qualifier: str | None = None
    monetary_amount: Decimal | None = None
    percent: Decimal | None = None
    quantity_qualifier: str | None = None
    quantity: Decimal | None = None
    authorization_or_certification_indicator: str | None = None
    in_plan_network_indicator: str | None = None
    procedure_identifier: str | None = None
