"""GS/GE functional group model."""

from __future__ import annotations

from pydantic import Field

from x12_edi_tools.models.base import X12BaseModel
from x12_edi_tools.models.segments import GESegment, GSSegment
from x12_edi_tools.models.transactions.transaction_270 import Transaction270
from x12_edi_tools.models.transactions.transaction_271 import Transaction271


class FunctionalGroup(X12BaseModel):
    """A functional group containing one or more eligibility transactions."""

    gs: GSSegment
    transactions: list[Transaction270 | Transaction271] = Field(default_factory=list)
    ge: GESegment
