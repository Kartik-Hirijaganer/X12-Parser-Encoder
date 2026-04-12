"""HL hierarchical level segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field, field_validator

from x12_edi_tools.common.enums import HierarchicalLevelCode
from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class HLSegment(X12Segment):
    segment_id: ClassVar[str] = "HL"
    _element_map: ClassVar[ElementMap] = {
        1: "hierarchical_id_number",
        2: "hierarchical_parent_id_number",
        3: "hierarchical_level_code",
        4: "hierarchical_child_code",
    }

    hierarchical_id_number: str = Field(min_length=1)
    hierarchical_parent_id_number: str | None = None
    hierarchical_level_code: HierarchicalLevelCode
    hierarchical_child_code: str | None = None

    @field_validator("hierarchical_child_code")
    @classmethod
    def validate_child_code(cls, value: str | None) -> str | None:
        if value is not None and value not in {"0", "1"}:
            raise ValueError("hierarchical_child_code must be '0' or '1'")
        return value
