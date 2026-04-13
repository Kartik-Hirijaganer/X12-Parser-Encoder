"""DC Medicaid search-criteria rules for 270 subscriber lookups."""

from __future__ import annotations

from dataclasses import dataclass

from x12_edi_tools.models.loops import Loop2000C_270, Loop2100C_270
from x12_edi_tools.models.segments import REFSegment
from x12_edi_tools.validator.base import as_list, normalize_str


@dataclass(frozen=True, slots=True)
class SearchCriteriaEvaluation:
    """Normalized view of subscriber search inputs."""

    has_member_id: bool
    has_name: bool
    has_dob: bool
    has_ssn: bool

    @property
    def is_valid(self) -> bool:
        supporting_fields = sum((self.has_name, self.has_dob, self.has_ssn))
        if self.has_member_id:
            return supporting_fields >= 2
        return supporting_fields >= 2

    def describe(self) -> str:
        parts = []
        if self.has_member_id:
            parts.append("member ID")
        if self.has_name:
            parts.append("name")
        if self.has_dob:
            parts.append("DOB")
        if self.has_ssn:
            parts.append("SSN")
        return ", ".join(parts) if parts else "no search criteria"


def evaluate_search_criteria(subscriber_loop: Loop2000C_270) -> SearchCriteriaEvaluation:
    """Evaluate the subscriber criteria present in a 270 inquiry."""

    loop_2100c = subscriber_loop.loop_2100c
    has_member_id = _has_member_id(loop_2100c)
    has_name = _has_name(loop_2100c)
    has_dob = bool(normalize_str(getattr(loop_2100c.dmg, "date_time_period", None)))
    has_ssn = any(_is_ssn_ref(segment) for segment in as_list(loop_2100c.ref_segments))

    return SearchCriteriaEvaluation(
        has_member_id=has_member_id,
        has_name=has_name,
        has_dob=has_dob,
        has_ssn=has_ssn,
    )


def _has_member_id(loop_2100c: Loop2100C_270) -> bool:
    nm1 = loop_2100c.nm1
    qualifier = normalize_str(getattr(nm1, "id_code_qualifier", None))
    identifier = normalize_str(getattr(nm1, "id_code", None))
    return qualifier == "MI" and bool(identifier)


def _has_name(loop_2100c: Loop2100C_270) -> bool:
    nm1 = loop_2100c.nm1
    return bool(normalize_str(getattr(nm1, "last_name", None))) and bool(
        normalize_str(getattr(nm1, "first_name", None))
    )


def _is_ssn_ref(ref_segment: object) -> bool:
    if not isinstance(ref_segment, REFSegment):
        return False
    qualifier = normalize_str(getattr(ref_segment, "reference_identification_qualifier", None))
    identifier = normalize_str(getattr(ref_segment, "reference_identification", None))
    return qualifier == "SY" and bool(identifier)
