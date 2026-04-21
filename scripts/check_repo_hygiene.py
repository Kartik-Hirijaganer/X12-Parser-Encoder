#!/usr/bin/env python3
"""Repo-hygiene gate for proprietary companion-guide content.

Per \u00a73.9 of ``.agents/plans/837i-837p-835-implementation-plan.md`` the DC Medicaid
270/271 Companion Guide (and any other vendor companion guide marked
"Proprietary and Confidential") must NOT be committed to ``docs/``, ``packages/``,
or ``apps/``. The reference copy lives in the local-only ``metadata/`` directory.

This check fails CI if any tracked file under those roots contains the marker
string, or if a known proprietary filename (``docs/full_text.txt``) is tracked.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SCANNED_ROOTS: tuple[str, ...] = ("docs/", "packages/", "apps/")
BANNED_TRACKED_PATHS: tuple[str, ...] = ("docs/full_text.txt",)
PROPRIETARY_MARKERS: tuple[str, ...] = ("Proprietary and Confidential",)
SKIP_SUFFIXES: tuple[str, ...] = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
    ".woff",
    ".woff2",
    ".ttf",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    return parser.parse_args()


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def scan_for_markers(paths: list[str]) -> list[str]:
    violations: list[str] = []
    for relative in paths:
        if not any(relative.startswith(root) for root in SCANNED_ROOTS):
            continue
        # The hygiene script itself, the implementation plan, and the in-repo
        # README list the marker for documentation purposes; skip them.
        if relative == "scripts/check_repo_hygiene.py":
            continue
        if relative.startswith(".agents/"):
            continue
        path = REPO_ROOT / relative
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for marker in PROPRIETARY_MARKERS:
            if marker in text:
                violations.append(f"{relative}: contains marker '{marker}'")
                break
    return violations


def main() -> int:
    parse_args()
    paths = tracked_files()

    violations: list[str] = [
        f"{path}: file is on the proprietary-content blocklist"
        for path in BANNED_TRACKED_PATHS
        if path in paths
    ]
    violations.extend(scan_for_markers(paths))

    if violations:
        print("Repo-hygiene check failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(
            "\nThese files contain proprietary companion-guide content that must "
            "not be committed. See \u00a73.9 of the 837I/837P/835 implementation plan.",
            file=sys.stderr,
        )
        return 1

    print("Repo-hygiene check passed: no proprietary companion-guide content tracked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
