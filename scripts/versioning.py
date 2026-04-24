"""Shared SemVer helpers for release scripts."""

from __future__ import annotations

import re
from dataclasses import dataclass

PRERELEASE_TAG_PATTERN = r"(?:0|[1-9]\d*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
SEMVER_PATTERN = (
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    rf"(?:-(?P<prerelease>{PRERELEASE_TAG_PATTERN}(?:\.{PRERELEASE_TAG_PATTERN})*))?$"
)
SEMVER_RE = re.compile(SEMVER_PATTERN)


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()

    @property
    def is_prerelease(self) -> bool:
        return bool(self.prerelease)

    def without_prerelease(self) -> "SemVer":
        return SemVer(self.major, self.minor, self.patch)

    def with_prerelease(self, *parts: str) -> "SemVer":
        return SemVer(self.major, self.minor, self.patch, tuple(parts))

    def bump_major(self) -> "SemVer":
        return SemVer(self.major + 1, 0, 0)

    def bump_minor(self) -> "SemVer":
        return SemVer(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "SemVer":
        return SemVer(self.major, self.minor, self.patch + 1)

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            return f"{base}-" + ".".join(self.prerelease)
        return base


def parse_semver(version: str) -> SemVer:
    match = SEMVER_RE.fullmatch(version)
    if match is None:
        raise ValueError(
            f"'{version}' is not valid SemVer. Expected X.Y.Z or X.Y.Z-prerelease"
        )
    prerelease = match.group("prerelease")
    return SemVer(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        prerelease=tuple(prerelease.split(".")) if prerelease else (),
    )


def normalize_release_candidate(current: str) -> str:
    version = parse_semver(current)
    if version.prerelease[:1] == ("rc",) and len(version.prerelease) == 2:
        candidate_number = version.prerelease[1]
        if candidate_number.isdigit() and not (
            candidate_number.startswith("0") and candidate_number != "0"
        ):
            return str(version.with_prerelease("rc", str(int(candidate_number) + 1)))
    if version.is_prerelease:
        return str(version.with_prerelease("rc", "1"))
    return str(version.bump_patch().with_prerelease("rc", "1"))


def normalize_final(current: str) -> str:
    return str(parse_semver(current).without_prerelease())


def require_semver(version: str, *, label: str) -> None:
    try:
        parse_semver(version)
    except ValueError as exc:
        raise SystemExit(f"{label}: {exc}") from exc
