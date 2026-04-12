"""NM1 individual or organizational name segment."""

from __future__ import annotations

from typing import ClassVar

from pydantic import field_validator

from x12_edi_tools.common.enums import EntityIdentifierCode
from x12_edi_tools.common.types import ElementMap
from x12_edi_tools.models.base import X12Segment


class NM1Segment(X12Segment):
    segment_id: ClassVar[str] = "NM1"
    _element_map: ClassVar[ElementMap] = {
        1: "entity_identifier_code",
        2: "entity_type_qualifier",
        3: "last_name",
        4: "first_name",
        5: "middle_name",
        6: "name_prefix",
        7: "name_suffix",
        8: "id_code_qualifier",
        9: "id_code",
    }

    entity_identifier_code: EntityIdentifierCode
    entity_type_qualifier: str | None = None
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    name_prefix: str | None = None
    name_suffix: str | None = None
    id_code_qualifier: str | None = None
    id_code: str | None = None

    @field_validator("entity_type_qualifier")
    @classmethod
    def validate_entity_type(cls, value: str | None) -> str | None:
        if value is not None and value not in {"1", "2"}:
            raise ValueError("entity_type_qualifier must be '1' or '2'")
        return value
