"""2120C loop models for 271 benefit-related entities."""

from __future__ import annotations

from pydantic import AliasChoices, Field

from x12_edi_tools.models.base import X12BaseModel
from x12_edi_tools.models.segments import LESegment, LSSegment, NM1Segment, PERSegment


class Loop2120C_271(X12BaseModel):
    """271 benefit-related entity loop wrapped by LS/LE."""

    ls: LSSegment = Field(validation_alias=AliasChoices("ls", "ls_segment"))
    nm1: NM1Segment
    per_segments: list[PERSegment] = Field(default_factory=list)
    le: LESegment = Field(validation_alias=AliasChoices("le", "le_segment"))

    @property
    def ls_segment(self) -> LSSegment:
        """Backward-compatible accessor for the planned ``ls`` field."""

        return self.ls

    @property
    def le_segment(self) -> LESegment:
        """Backward-compatible accessor for the planned ``le`` field."""

        return self.le
