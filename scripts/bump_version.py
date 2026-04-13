#!/usr/bin/env python3
"""Synchronize the repository version across release-bearing files."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = REPO_ROOT / "VERSION"
README_FILE = REPO_ROOT / "README.md"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"

TEXT_VERSION_FILES = {
    REPO_ROOT / "packages" / "x12-edi-tools" / "pyproject.toml": (
        re.compile(r'(?m)^(version = ")([^"]+)(")$'),
        r"\g<1>{version}\g<3>",
    ),
    REPO_ROOT
    / "packages"
    / "x12-edi-tools"
    / "src"
    / "x12_edi_tools"
    / "__about__.py": (
        re.compile(r'(?m)^(__version__ = ")([^"]+)(")$'),
        r"\g<1>{version}\g<3>",
    ),
    REPO_ROOT / "apps" / "api" / "pyproject.toml": (
        re.compile(r'(?m)^(version = ")([^"]+)(")$'),
        r"\g<1>{version}\g<3>",
    ),
}

README_VERSION_TABLE_START = "<!-- version-table:start -->"
README_VERSION_TABLE_END = "<!-- version-table:end -->"


def read_current_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="major, minor, patch, or an explicit X.Y.Z version")
    return parser.parse_args()


def normalize_version(target: str, current: str) -> str:
    explicit = re.fullmatch(r"\d+\.\d+\.\d+", target)
    if explicit:
        return target

    current_match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", current)
    if current_match is None:
        raise SystemExit(f"Current version '{current}' is not valid semantic versioning")

    major, minor, patch = [int(value) for value in current_match.groups()]
    if target == "major":
        return f"{major + 1}.0.0"
    if target == "minor":
        return f"{major}.{minor + 1}.0"
    if target == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SystemExit("Target must be one of: major, minor, patch, or X.Y.Z")


def replace_in_text_file(path: Path, *, version: str) -> None:
    pattern, replacement = TEXT_VERSION_FILES[path]
    text = path.read_text(encoding="utf-8")
    updated, count = pattern.subn(replacement.format(version=version), text, count=1)
    if count != 1:
        raise SystemExit(f"Could not update version in {path}")
    path.write_text(updated, encoding="utf-8")


def update_json_version(path: Path, *, version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    packages = data.get("packages")
    if isinstance(packages, dict) and "" in packages and isinstance(packages[""], dict):
        packages[""]["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def update_readme_version_table(*, version: str) -> None:
    table = "\n".join(
        [
            README_VERSION_TABLE_START,
            "| Artifact | Version |",
            "| --- | --- |",
            f"| Monorepo | `{version}` |",
            f"| Python package | `{version}` |",
            f"| API app | `{version}` |",
            f"| Web app | `{version}` |",
            README_VERSION_TABLE_END,
        ]
    )
    text = README_FILE.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"{re.escape(README_VERSION_TABLE_START)}.*?{re.escape(README_VERSION_TABLE_END)}",
        re.DOTALL,
    )
    updated, count = pattern.subn(table, text, count=1)
    if count != 1:
        raise SystemExit("README version table markers were not found")
    README_FILE.write_text(updated, encoding="utf-8")


def update_changelog(*, version: str) -> None:
    text = CHANGELOG_FILE.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^## \[Unreleased\]\n(?P<body>.*?)(?=^## \[|\Z)", text)
    if match is None:
        raise SystemExit("CHANGELOG.md does not contain an [Unreleased] section")

    unreleased_body = match.group("body").strip("\n")
    release_header = f"## [{version}] - {date.today().isoformat()}"
    release_block = f"## [Unreleased]\n\n{release_header}\n"
    if unreleased_body:
        release_block += f"\n{unreleased_body}\n"
    else:
        release_block += "\n- No user-facing changes yet.\n"
    updated = text[: match.start()] + release_block + "\n" + text[match.end() :].lstrip("\n")
    CHANGELOG_FILE.write_text(updated.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    current = read_current_version()
    target = normalize_version(args.target, current)

    VERSION_FILE.write_text(f"{target}\n", encoding="utf-8")
    for path in TEXT_VERSION_FILES:
        replace_in_text_file(path, version=target)
    update_json_version(REPO_ROOT / "apps" / "web" / "package.json", version=target)
    update_json_version(REPO_ROOT / "apps" / "web" / "package-lock.json", version=target)
    update_readme_version_table(version=target)
    if CHANGELOG_FILE.exists():
        update_changelog(version=target)

    print(f"{current} -> {target}")
    print("Updated files:")
    for path in [
        VERSION_FILE,
        *TEXT_VERSION_FILES,
        REPO_ROOT / "apps" / "web" / "package.json",
        REPO_ROOT / "apps" / "web" / "package-lock.json",
        README_FILE,
        CHANGELOG_FILE,
    ]:
        if path.exists():
            print(f"- {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
