#!/usr/bin/env python3
"""Validate a tag-triggered release before publishing artifacts."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from versioning import parse_semver

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = REPO_ROOT / "VERSION"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tag",
        nargs="?",
        default=os.environ.get("GITHUB_REF_NAME"),
        help="Release tag, with leading v. Defaults to GITHUB_REF_NAME.",
    )
    parser.add_argument(
        "--github-output",
        default=os.environ.get("GITHUB_OUTPUT"),
        help="Optional GitHub Actions output file to populate.",
    )
    return parser.parse_args()


def changelog_has_section(version: str) -> bool:
    changelog = CHANGELOG_FILE.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(?m)^## \[{re.escape(version)}\](?:\s+-\s+\d{{4}}-\d{{2}}-\d{{2}})?$"
    )
    return pattern.search(changelog) is not None


def write_github_outputs(path: str | None, *, version: str, prerelease: bool) -> None:
    if not path:
        return
    make_latest = not prerelease
    with Path(path).open("a", encoding="utf-8") as output:
        output.write(f"version={version}\n")
        output.write(f"prerelease={str(prerelease).lower()}\n")
        output.write(f"make_latest={str(make_latest).lower()}\n")


def main() -> None:
    args = parse_args()
    if not args.tag:
        raise SystemExit(
            "Release validation requires a tag argument or GITHUB_REF_NAME"
        )
    if not args.tag.startswith("v"):
        raise SystemExit(f"Release tag '{args.tag}' must start with 'v'")

    version = args.tag.removeprefix("v")
    try:
        parsed_version = parse_semver(version)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    expected = VERSION_FILE.read_text(encoding="utf-8").strip()
    if version != expected:
        raise SystemExit(
            f"Release tag {args.tag} does not match VERSION {expected}. "
            "Run scripts/bump_version.py before tagging."
        )
    if not changelog_has_section(version):
        raise SystemExit(f"CHANGELOG.md does not contain a section for {version}")

    write_github_outputs(
        args.github_output,
        version=version,
        prerelease=parsed_version.is_prerelease,
    )
    release_kind = "prerelease" if parsed_version.is_prerelease else "final release"
    print(f"Release validation OK: {args.tag} ({release_kind})")


if __name__ == "__main__":
    main()
