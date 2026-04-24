"""EB eligibility or benefit information segment."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import ClassVar, Self

from pydantic import Field, model_validator

from x12_edi_tools.common.enums import EligibilityInfoCode, ServiceTypeCode
from x12_edi_tools.common.types import ElementMap, ElementValue
from x12_edi_tools.models.base import X12Segment

OUTBOUND_ELIGIBILITY_INFO_CODES = frozenset(
    {
        *(code.value for code in EligibilityInfoCode),
        "L",
        "MC",
        "R",
    }
)
OUTBOUND_SERVICE_TYPE_CODES = frozenset(code.value for code in ServiceTypeCode)


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

    eligibility_or_benefit_information: str
    coverage_level_code: str | None = None
    service_type_code: str | None = None
    service_type_codes: list[str] = Field(default_factory=list)
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

    @classmethod
    def from_elements(
        cls,
        elements: Sequence[ElementValue],
        *,
        repetition_separator: str | None = None,
    ) -> Self:
        """Build an EB segment while preserving repeated EB03 values."""

        data: dict[str, object] = {
            field_name: cls._normalize_element(elements[position - 1])
            if position <= len(elements)
            else None
            for position, field_name in cls._element_map.items()
        }
        raw_service_type = data.get("service_type_code")
        if raw_service_type is None:
            data["service_type_codes"] = []
        elif (
            isinstance(raw_service_type, str)
            and repetition_separator
            and repetition_separator in raw_service_type
        ):
            service_type_codes = [
                code for code in raw_service_type.split(repetition_separator) if code
            ]
            data["service_type_codes"] = service_type_codes
            data["service_type_code"] = service_type_codes[0] if service_type_codes else None
        else:
            data["service_type_codes"] = [raw_service_type]
        return cls.model_validate(data)

    @model_validator(mode="after")
    def sync_service_type_fields(self) -> Self:
        """Keep the scalar and repeated EB03 projections in lock-step."""

        service_type_codes = [code for code in self.service_type_codes if code]
        if not service_type_codes and self.service_type_code is not None:
            service_type_codes = [self.service_type_code]
        self.service_type_codes = service_type_codes
        self.service_type_code = service_type_codes[0] if service_type_codes else None
        return self
