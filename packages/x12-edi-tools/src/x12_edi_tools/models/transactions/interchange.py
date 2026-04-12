"""ISA/IEA interchange model."""

from __future__ import annotations

from pydantic import Field

from x12_edi_tools.common.delimiters import Delimiters
from x12_edi_tools.models.base import X12BaseModel
from x12_edi_tools.models.segments import IEASegment, ISASegment
from x12_edi_tools.models.transactions.functional_group import FunctionalGroup


class Interchange(X12BaseModel):
    """Top-level X12 interchange container."""

    isa: ISASegment
    functional_groups: list[FunctionalGroup] = Field(default_factory=list)
    iea: IEASegment
    delimiters: Delimiters = Field(default_factory=Delimiters)
