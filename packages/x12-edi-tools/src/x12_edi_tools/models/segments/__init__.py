"""Typed segment models used by 270/271 transactions."""

from x12_edi_tools.models.segments.aaa import AAASegment
from x12_edi_tools.models.segments.bht import BHTSegment
from x12_edi_tools.models.segments.dmg import DMGSegment
from x12_edi_tools.models.segments.dtp import DTPSegment
from x12_edi_tools.models.segments.eb import EBSegment
from x12_edi_tools.models.segments.eq import EQSegment
from x12_edi_tools.models.segments.ge import GESegment
from x12_edi_tools.models.segments.gs import GSSegment
from x12_edi_tools.models.segments.hl import HLSegment
from x12_edi_tools.models.segments.iea import IEASegment
from x12_edi_tools.models.segments.isa import ISASegment
from x12_edi_tools.models.segments.ls_le import LESegment, LSSegment
from x12_edi_tools.models.segments.n3 import N3Segment
from x12_edi_tools.models.segments.n4 import N4Segment
from x12_edi_tools.models.segments.nm1 import NM1Segment
from x12_edi_tools.models.segments.per import PERSegment
from x12_edi_tools.models.segments.prv import PRVSegment
from x12_edi_tools.models.segments.ref import REFSegment
from x12_edi_tools.models.segments.se import SESegment
from x12_edi_tools.models.segments.st import STSegment
from x12_edi_tools.models.segments.trn import TRNSegment

__all__ = [
    "AAASegment",
    "BHTSegment",
    "DMGSegment",
    "DTPSegment",
    "EBSegment",
    "EQSegment",
    "GESegment",
    "GSSegment",
    "HLSegment",
    "IEASegment",
    "ISASegment",
    "LESegment",
    "LSSegment",
    "N3Segment",
    "N4Segment",
    "NM1Segment",
    "PERSegment",
    "PRVSegment",
    "REFSegment",
    "SESegment",
    "STSegment",
    "TRNSegment",
]
