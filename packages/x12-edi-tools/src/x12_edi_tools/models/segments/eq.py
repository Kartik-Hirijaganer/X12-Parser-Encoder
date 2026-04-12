"""EQ eligibility or benefit inquiry segment."""

from __future__ import annotations

from typing import ClassVar

from x12_edi_tools.common.enums import ServiceTypeCode
from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class EQSegment(X12Segment):
    segment_id: ClassVar[str] = "EQ"
    _element_map: ClassVar[ElementMap] = {
        1: "service_type_code",
        2: "medical_procedure_identifier",
        3: "coverage_level_code",
        4: "insurance_type_code",
        5: "diagnosis_code_pointer",
    }

    service_type_code: ServiceTypeCode
    medical_procedure_identifier: str | None = None
    coverage_level_code: str | None = None
    insurance_type_code: str | None = None
    diagnosis_code_pointer: str | None = None
