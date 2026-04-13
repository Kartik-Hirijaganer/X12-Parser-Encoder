#!/usr/bin/env python3
"""Print a changelog section for a specific release version."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Release version without the leading v")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    changelog = CHANGELOG_FILE.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(?ms)^## \[{re.escape(args.version)}\][^\n]*\n(?P<body>.*?)(?=^## \[|\Z)"
    )
    match = pattern.search(changelog)
    if match is None:
        raise SystemExit(f"Could not find CHANGELOG section for version {args.version}")
    print(match.group("body").strip())


if __name__ == "__main__":
    main()
