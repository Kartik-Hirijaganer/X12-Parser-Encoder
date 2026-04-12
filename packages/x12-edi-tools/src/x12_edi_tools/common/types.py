"""Shared type aliases used across the X12 model layer."""

from __future__ import annotations

from dataclasses import dataclass
from os import PathLike
from typing import TypeAlias

SegmentId: TypeAlias = str
ElementValue: TypeAlias = str | None
ElementList: TypeAlias = list[ElementValue]
ElementMap: TypeAlias = dict[int, str]
PathLikeStr: TypeAlias = str | PathLike[str]


@dataclass(frozen=True, slots=True)
class SegmentToken:
    """Token emitted by the tokenizer in the parser phase."""

    segment_id: SegmentId
    elements: tuple[str, ...]
    position: int
