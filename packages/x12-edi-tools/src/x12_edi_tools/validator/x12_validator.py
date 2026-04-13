"""Validation orchestrator for generic SNIP rules plus payer profiles."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from x12_edi_tools._logging import build_log_extra, get_logger
from x12_edi_tools.exceptions import X12ValidationError
from x12_edi_tools.models.transactions import Interchange
from x12_edi_tools.payers import get_profile
from x12_edi_tools.payers.base import PayerProfile
from x12_edi_tools.validator.base import SnipLevel, ValidationResult, ValidationRule
from x12_edi_tools.validator.snip1 import validate_snip1
from x12_edi_tools.validator.snip2 import validate_snip2
from x12_edi_tools.validator.snip3 import validate_snip3
from x12_edi_tools.validator.snip4 import validate_snip4
from x12_edi_tools.validator.snip5 import validate_snip5

_VALIDATORS = {
    SnipLevel.SNIP1: validate_snip1,
    SnipLevel.SNIP2: validate_snip2,
    SnipLevel.SNIP3: validate_snip3,
    SnipLevel.SNIP4: validate_snip4,
    SnipLevel.SNIP5: validate_snip5,
}
logger = get_logger(__name__)


def validate(
    interchange: Interchange,
    *,
    levels: Iterable[int | str | SnipLevel] | None = None,
    profile: str | PayerProfile | None = None,
    custom_rules: Sequence[ValidationRule] | None = None,
    correlation_id: str | None = None,
) -> ValidationResult:
    """Validate a typed interchange against SNIP levels and an optional payer profile."""

    normalized_levels = _normalize_levels(levels)
    issues = []

    logger.info(
        "x12_validate_started",
        extra=build_log_extra(
            correlation_id=correlation_id,
            snip_levels=[level.value for level in normalized_levels],
            payer_profile=(profile if isinstance(profile, str) else getattr(profile, "name", None)),
            custom_rule_count=len(custom_rules or ()),
        ),
    )

    for level in normalized_levels:
        issues.extend(_VALIDATORS[level](interchange))

    if profile is not None:
        resolved_profile = get_profile(profile) if isinstance(profile, str) else profile
        issues.extend(list(resolved_profile.validate(interchange)))

    for rule in custom_rules or ():
        issues.extend(list(rule(interchange)))

    result = ValidationResult(issues=issues)
    logger.info(
        "x12_validate_completed",
        extra=build_log_extra(
            correlation_id=correlation_id,
            issue_count=len(issues),
            error_count=sum(1 for issue in issues if issue.severity == "error"),
            warning_count=sum(1 for issue in issues if issue.severity == "warning"),
        ),
    )
    return result


def _normalize_levels(levels: Iterable[int | str | SnipLevel] | None) -> list[SnipLevel]:
    if levels is None:
        return [
            SnipLevel.SNIP1,
            SnipLevel.SNIP2,
            SnipLevel.SNIP3,
            SnipLevel.SNIP4,
            SnipLevel.SNIP5,
        ]

    normalized = []
    seen: set[SnipLevel] = set()
    for value in levels:
        level = SnipLevel.from_value(value)
        if level in seen:
            continue
        seen.add(level)
        normalized.append(level)

    if not normalized:
        raise X12ValidationError("validate() requires at least one SNIP level when levels is set")
    return normalized
