"""Plan selection helpers for 271 display and export."""

from __future__ import annotations

from typing import Literal

from app.schemas.common import EligibilityResult, EligibilitySegment, PlanOption

PlanView = Literal["agency", "primary", "medicare", "all"]

MEDICAID_INSURANCE_TYPE_CODES = frozenset({"MC"})
MEDICARE_INSURANCE_TYPE_CODES = frozenset({"MA", "MB", "MP"})


def build_plan_options(
    eligibility_segments: list[EligibilitySegment],
) -> tuple[list[PlanOption], int | None]:
    options: list[PlanOption] = []
    for source_index, segment in enumerate(eligibility_segments):
        description = segment.plan_coverage_description
        if not description:
            continue

        program_name, payer_code, category = split_plan_description(description)
        if not any((program_name, payer_code, category)):
            continue

        plan_type = _plan_type(segment, program_name, payer_code, category)
        options.append(
            PlanOption(
                label=_plan_label(plan_type, program_name),
                program_name=program_name,
                payer_code=payer_code,
                category=category,
                insurance_type_code=segment.insurance_type_code,
                eligibility_code=segment.eligibility_code,
                source_segment_index=source_index,
                plan_type=plan_type,
                agency_preferred=plan_type == "medicaid",
                primary_returned=len(options) == 0,
            )
        )

    return options, _default_plan_option_index(options)


def selected_plan_options(result: EligibilityResult, plan_view: PlanView) -> list[PlanOption]:
    options = _resolved_plan_options(result)
    if not options:
        return []

    if plan_view == "all":
        return options

    if plan_view == "primary":
        primary = next((option for option in options if option.primary_returned), None)
        return [primary or options[0]]

    if plan_view == "medicare":
        medicare = next((option for option in options if option.plan_type == "medicare"), None)
        return [medicare] if medicare else []

    return [_default_plan_option(result, options)]


def split_plan_description(description: str | None) -> tuple[str, str, str]:
    if not description:
        return ("", "", "")
    parts = [part.strip() for part in description.split("|")]
    if len(parts) < 3:
        return (description.strip(), "", "")
    return (parts[0], parts[1], parts[2])


def _resolved_plan_options(result: EligibilityResult) -> list[PlanOption]:
    if result.plan_options:
        return result.plan_options
    options, _default_index = build_plan_options(result.eligibility_segments)
    return options


def _default_plan_option(result: EligibilityResult, options: list[PlanOption]) -> PlanOption:
    if result.default_plan_option_index is not None:
        if 0 <= result.default_plan_option_index < len(options):
            return options[result.default_plan_option_index]

    agency = next((option for option in options if option.agency_preferred), None)
    return agency or options[0]


def _default_plan_option_index(options: list[PlanOption]) -> int | None:
    for index, option in enumerate(options):
        if option.agency_preferred:
            return index
    return 0 if options else None


def _plan_type(
    segment: EligibilitySegment,
    program_name: str,
    payer_code: str,
    category: str,
) -> str:
    insurance_type = (segment.insurance_type_code or "").strip().upper()
    text = " ".join((program_name, payer_code, category)).upper()

    if insurance_type in MEDICAID_INSURANCE_TYPE_CODES or "MEDICAID" in text:
        return "medicaid"
    if insurance_type in MEDICARE_INSURANCE_TYPE_CODES or "MEDICARE" in text:
        return "medicare"
    return "other"


def _plan_label(plan_type: str, program_name: str) -> str:
    if plan_type == "medicaid":
        return "Medicaid/Gainwell"
    if plan_type == "medicare":
        return "Medicare"
    return program_name or "Other"
