"""DC Medicaid 270 payer-profile validation rules."""

from __future__ import annotations

from x12_edi_tools.models.loops import Loop2000C_270
from x12_edi_tools.models.segments import DTPSegment
from x12_edi_tools.validator.base import (
    SnipLevel,
    ValidationError,
    issue,
    normalize_str,
)

_SUBSCRIBER_DATE_QUALIFIER = "291"


def validate_270_dtp_placement(
    subscriber_loop: Loop2000C_270,
    *,
    location: str,
    profile: str,
) -> list[ValidationError]:
    """Validate Gainwell's DTP*291 placement rule for a 270 subscriber loop."""

    if _has_subscriber_date(subscriber_loop):
        return []

    issues: list[ValidationError] = []
    for inquiry_index, inquiry_loop in enumerate(subscriber_loop.loop_2110c):
        for dtp_index, dtp in enumerate(inquiry_loop.dtp_segments):
            if not _is_subscriber_date(dtp):
                continue
            issues.append(
                issue(
                    level=SnipLevel.SNIP5,
                    code="DCM_270_DTP291_REQUIRES_2100C",
                    message=(
                        "Segment DTP (Subscriber Eligibility/Benefit Date) is used. It should "
                        "not be used when segment DTP (Subscriber Date) is not used in loop "
                        "2100C."
                    ),
                    location=(f"{location}.Loop2110C[{inquiry_index}].DTP[{dtp_index}].01"),
                    segment_id="DTP",
                    element="01",
                    suggestion="Move DTP*291 before the EQ segment so it is in Loop 2100C.",
                    profile=profile,
                )
            )
    return issues


def _has_subscriber_date(subscriber_loop: Loop2000C_270) -> bool:
    return any(_is_subscriber_date(dtp) for dtp in subscriber_loop.loop_2100c.dtp_segments)


def _is_subscriber_date(dtp: DTPSegment) -> bool:
    return normalize_str(dtp.date_time_qualifier) == _SUBSCRIBER_DATE_QUALIFIER
