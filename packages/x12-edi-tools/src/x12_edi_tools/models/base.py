"""Base model types for X12 segments, loops, and transactions."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from enum import Enum
from typing import ClassVar, Self, cast

from pydantic import BaseModel, ConfigDict, Field

from x12_edi_tools.common.types import ElementMap, ElementValue


class X12BaseModel(BaseModel):
    """Common strict base for all typed X12 models."""

    model_config = ConfigDict(extra="forbid")


class X12Segment(X12BaseModel):
    """Declarative segment model with generic element mapping support."""

    segment_id: ClassVar[str]
    _element_map: ClassVar[ElementMap] = {}

    @classmethod
    def from_elements(cls, elements: Sequence[ElementValue]) -> Self:
        """Build a segment from positional X12 elements."""

        data = {
            field_name: cls._normalize_element(elements[position - 1])
            if position <= len(elements)
            else None
            for position, field_name in cls._element_map.items()
        }
        return cls(**data)

    def to_elements(self) -> list[str]:
        """Render the segment back to positional element strings."""

        if not self._element_map:
            return []

        rendered = [""] * max(self._element_map)
        for position, field_name in self._element_map.items():
            rendered[position - 1] = self._serialize_element(getattr(self, field_name))
        return rendered

    @staticmethod
    def _normalize_element(value: ElementValue) -> str | None:
        if value in (None, ""):
            return None
        return value

    @staticmethod
    def _serialize_element(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, Enum):
            return cast(str, value.value)
        if isinstance(value, Decimal):
            return format(value, "f")
        return str(value)


class GenericSegment(X12BaseModel):
    """Preserves unsupported but well-formed segments without data loss."""

    segment_id: str = Field(min_length=2, max_length=3)
    raw_elements: list[str] = Field(default_factory=list)

    def to_elements(self) -> list[str]:
        """Return the original raw elements unchanged."""

        return list(self.raw_elements)
