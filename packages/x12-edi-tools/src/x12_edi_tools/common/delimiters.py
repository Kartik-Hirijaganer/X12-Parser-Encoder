"""Delimiter primitives for X12 interchange handling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Delimiters:
    """Immutable delimiter bundle derived from the ISA segment."""

    element: str = "*"
    sub_element: str = ":"
    segment: str = "~"
    repetition: str = "^"

    def __post_init__(self) -> None:
        for field_name, value in (
            ("element", self.element),
            ("sub_element", self.sub_element),
            ("segment", self.segment),
            ("repetition", self.repetition),
        ):
            if len(value) != 1:
                raise ValueError(f"{field_name} delimiter must be exactly one character")

    @property
    def element_separator(self) -> str:
        """Compatibility alias for later parser/encoder phases."""

        return self.element

    @property
    def component_separator(self) -> str:
        """Compatibility alias for later parser/encoder phases."""

        return self.sub_element

    @property
    def segment_terminator(self) -> str:
        """Compatibility alias for later parser/encoder phases."""

        return self.segment

    @property
    def repetition_separator(self) -> str:
        """Compatibility alias for later parser/encoder phases."""

        return self.repetition
