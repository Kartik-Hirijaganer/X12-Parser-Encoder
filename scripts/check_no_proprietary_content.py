#!/usr/bin/env python3
"""Guard local-only content from slipping into tracked files or build artifacts."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BANNED_PREFIXES = ("metadata/",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="*", help="Optional wheel/sdist paths to inspect")
    return parser.parse_args()


def tracked_file_violations() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return [
        path for path in tracked_files if any(path.startswith(prefix) for prefix in BANNED_PREFIXES)
    ]


def archive_members(path: Path) -> list[str]:
    if path.suffix == ".whl" or path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    if path.suffixes[-2:] == [".tar", ".gz"] or path.suffix == ".tgz":
        with tarfile.open(path, "r:*") as archive:
            return archive.getnames()
    raise SystemExit(f"Unsupported artifact format: {path}")


def main() -> None:
    args = parse_args()
    violations = tracked_file_violations()

    for artifact in args.artifacts:
        members = archive_members(Path(artifact))
        violations.extend(
            f"{artifact}:{member}"
            for member in members
            if any(f"/{prefix}" in member or member.startswith(prefix) for prefix in BANNED_PREFIXES)
        )

    if violations:
        print("Non-publishable content detected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        raise SystemExit(1)

    print("No proprietary or local-only content detected.")


if __name__ == "__main__":
    main()
