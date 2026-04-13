#!/usr/bin/env python3
"""Fail when version-bearing files drift away from the repo VERSION."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
README_FILE = REPO_ROOT / "README.md"


def check_text_pattern(path: Path, pattern: str) -> str | None:
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def main() -> None:
    mismatches: list[str] = []

    checks = {
        "packages/x12-edi-tools/pyproject.toml": check_text_pattern(
            REPO_ROOT / "packages" / "x12-edi-tools" / "pyproject.toml",
            r'^version = "([^"]+)"$',
        ),
        "packages/x12-edi-tools/src/x12_edi_tools/__about__.py": check_text_pattern(
            REPO_ROOT
            / "packages"
            / "x12-edi-tools"
            / "src"
            / "x12_edi_tools"
            / "__about__.py",
            r'^__version__ = "([^"]+)"$',
        ),
        "apps/api/pyproject.toml": check_text_pattern(
            REPO_ROOT / "apps" / "api" / "pyproject.toml",
            r'^version = "([^"]+)"$',
        ),
        "README.md": check_text_pattern(
            README_FILE,
            r"\| Monorepo \| `([^`]+)` \|",
        ),
    }

    package_json = json.loads(
        (REPO_ROOT / "apps" / "web" / "package.json").read_text(encoding="utf-8")
    )
    checks["apps/web/package.json"] = str(package_json.get("version"))

    package_lock = json.loads(
        (REPO_ROOT / "apps" / "web" / "package-lock.json").read_text(encoding="utf-8")
    )
    checks["apps/web/package-lock.json"] = str(package_lock.get("version"))

    for path, actual in checks.items():
        if actual != EXPECTED:
            mismatches.append(f"{path}: expected {EXPECTED}, found {actual}")

    if mismatches:
        print("Version drift detected:", file=sys.stderr)
        for mismatch in mismatches:
            print(f"- {mismatch}", file=sys.stderr)
        raise SystemExit(1)

    print(f"Version sync OK: {EXPECTED}")


if __name__ == "__main__":
    main()
