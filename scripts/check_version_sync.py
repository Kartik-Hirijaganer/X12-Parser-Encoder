#!/usr/bin/env python3
"""Fail when version-bearing files drift away from the repo VERSION."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from versioning import require_semver

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
README_FILE = REPO_ROOT / "README.md"
PROVIDER_PIN_ANNOTATION = r'provider_pin_repo_version\s*=\s*"([^"]+)"'


def check_text_pattern(path: Path, pattern: str) -> str | None:
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def check_json_version(path: Path, *keys: str) -> str | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value if isinstance(value, str) else None


def record_check(
    checks: dict[str, str | None],
    mismatches: list[str],
    *,
    path: str,
    actual: str | None,
) -> None:
    checks[path] = actual
    if actual is None:
        mismatches.append(f"{path}: expected {EXPECTED}, found missing version")
        return
    try:
        require_semver(actual, label=path)
    except SystemExit as exc:
        mismatches.append(str(exc))
        return
    if actual != EXPECTED:
        mismatches.append(f"{path}: expected {EXPECTED}, found {actual}")


def record_soft_check(
    checks: dict[str, str | None],
    warnings: list[str],
    *,
    path: str,
    actual: str | None,
) -> None:
    checks[path] = actual
    if actual is None:
        warnings.append(f"{path}: missing provider_pin_repo_version annotation")
        return
    try:
        require_semver(actual, label=path)
    except SystemExit as exc:
        warnings.append(str(exc))
        return
    if actual != EXPECTED:
        warnings.append(
            f"{path}: expected provider_pin_repo_version {EXPECTED}, found {actual}"
        )


def main() -> None:
    mismatches: list[str] = []
    warnings: list[str] = []
    try:
        require_semver(EXPECTED, label="VERSION")
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    checks: dict[str, str | None] = {}
    record_check(
        checks,
        mismatches,
        path="packages/x12-edi-tools/pyproject.toml",
        actual=check_text_pattern(
            REPO_ROOT / "packages" / "x12-edi-tools" / "pyproject.toml",
            r'^version = "([^"]+)"$',
        ),
    )
    record_check(
        checks,
        mismatches,
        path="packages/x12-edi-tools/src/x12_edi_tools/__about__.py",
        actual=check_text_pattern(
            REPO_ROOT
            / "packages"
            / "x12-edi-tools"
            / "src"
            / "x12_edi_tools"
            / "__about__.py",
            r'^__version__ = "([^"]+)"$',
        ),
    )
    record_check(
        checks,
        mismatches,
        path="apps/api/pyproject.toml",
        actual=check_text_pattern(
            REPO_ROOT / "apps" / "api" / "pyproject.toml",
            r'^version = "([^"]+)"$',
        ),
    )
    for artifact in ("Monorepo", "Python package", "API app", "Web app"):
        record_check(
            checks,
            mismatches,
            path=f"README.md ({artifact})",
            actual=check_text_pattern(
                README_FILE,
                rf"\| {re.escape(artifact)} \| `([^`]+)` \|",
            ),
        )

    record_check(
        checks,
        mismatches,
        path="apps/web/package.json",
        actual=check_json_version(
            REPO_ROOT / "apps" / "web" / "package.json",
            "version",
        ),
    )
    record_check(
        checks,
        mismatches,
        path="apps/web/package-lock.json",
        actual=check_json_version(
            REPO_ROOT / "apps" / "web" / "package-lock.json",
            "version",
        ),
    )
    record_check(
        checks,
        mismatches,
        path="apps/web/package-lock.json (root package)",
        actual=check_json_version(
            REPO_ROOT / "apps" / "web" / "package-lock.json",
            "packages",
            "",
            "version",
        ),
    )

    for versions_file in sorted(
        (REPO_ROOT / "infra" / "terraform" / "modules").glob("*/versions.tf")
    ):
        record_soft_check(
            checks,
            warnings,
            path=str(versions_file.relative_to(REPO_ROOT)),
            actual=check_text_pattern(versions_file, PROVIDER_PIN_ANNOTATION),
        )

    # The checks dict is kept explicit so this script fails loudly if a version
    # source is accidentally removed while refactoring release metadata.
    if not checks:
        mismatches.append("No version-bearing files were checked")

    if warnings:
        print("Version sync warnings:", file=sys.stderr)
        for warning in warnings:
            print(f"- {warning}", file=sys.stderr)

    if mismatches:
        print("Version drift detected:", file=sys.stderr)
        for mismatch in mismatches:
            print(f"- {mismatch}", file=sys.stderr)
        raise SystemExit(1)

    print(f"Version sync OK: {EXPECTED}")


if __name__ == "__main__":
    main()
