"""High-level convenience API surface reserved for later phases."""

from __future__ import annotations

from typing import Any

from x12_edi_tools.common.types import PathLikeStr
from x12_edi_tools.config import SubmitterConfig
from x12_edi_tools.models.transactions import Interchange


def from_csv(path: PathLikeStr) -> list[Any]:
    """Load patient records from a canonical CSV template."""

    raise NotImplementedError("from_csv() is scheduled for a later implementation phase")


def from_excel(path: PathLikeStr) -> list[Any]:
    """Load patient records from a canonical Excel template."""

    raise NotImplementedError("from_excel() is scheduled for a later implementation phase")


def build_270(
    patients: list[Any],
    *,
    config: SubmitterConfig,
    profile: str,
) -> Interchange:
    """Build a typed 270 interchange from normalized patient records."""

    raise NotImplementedError("build_270() is scheduled for a later implementation phase")


def read_271(path_or_string: PathLikeStr | str) -> Any:
    """Parse a 271 response into higher-level eligibility results."""

    raise NotImplementedError("read_271() is scheduled for a later implementation phase")
