from __future__ import annotations

import pytest
from app.schemas.common import AAAError, EligibilitySegment
from app.services.parser import _overall_status


@pytest.mark.parametrize(
    ("eligibility_segments", "aaa_errors", "expected_status", "expected_reason"),
    [
        (
            [],
            [AAAError(code="75", message="Subscriber not found")],
            "not_found",
            "Subscriber not found",
        ),
        ([], [AAAError(code="72", message="Invalid member ID")], "error", "Invalid member ID"),
        ([EligibilitySegment(eligibility_code="1")], [], "active", "Coverage on file"),
        ([EligibilitySegment(eligibility_code="6")], [], "inactive", "Coverage terminated"),
        (
            [EligibilitySegment(eligibility_code="R")],
            [],
            "unknown",
            "Additional payer information only",
        ),
    ],
)
def test_overall_status_uses_five_way_classifier(
    eligibility_segments: list[EligibilitySegment],
    aaa_errors: list[AAAError],
    expected_status: str,
    expected_reason: str,
) -> None:
    assert _overall_status(eligibility_segments, aaa_errors) == (
        expected_status,
        expected_reason,
    )
