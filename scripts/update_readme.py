#!/usr/bin/env python3
"""Update generated marker blocks in README.md and docs/architecture.md."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PROJECT_STRUCTURE: Mapping[str, str] = {
    "packages/x12-edi-tools": "Framework-agnostic Python library for parsing, encoding, validation, payer profiles, and public types",
    "apps/api": "FastAPI Lambda/container adapter exposing upload, generation, validation, parse, export, health, profile, and pipeline endpoints",
    "apps/web": "React workbench for settings management, preview, generation, validation, templates, and eligibility dashboards",
    "infra/terraform": "Terraform modules and staging/production environments for S3, CloudFront, Lambda, WAF, observability, and custom domains",
    "docs": "Architecture, API, design, runbook, diagram, and ADR documentation",
    "scripts": "Release, packaging, Terraform helper, Lambda pruning, and documentation regeneration scripts",
    ".github/workflows": "CI, deploy, release, Terraform, and documentation drift workflows",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the parent of scripts/.",
    )
    return parser.parse_args()


def replace_block(text: str, name: str, replacement: str) -> str:
    start = f"<!-- autogen:{name}:start -->"
    end = f"<!-- autogen:{name}:end -->"
    if start not in text:
        raise SystemExit(f"Missing marker {start}")
    if end not in text:
        raise SystemExit(f"Missing marker {end}")

    before, after_start = text.split(start, 1)
    _old, after = after_start.split(end, 1)
    return f"{before}{start}\n{replacement.rstrip()}\n{end}{after}"


def load_openapi(repo_root: Path) -> dict[str, Any]:
    spec_path = repo_root / "docs" / "api" / "openapi.yaml"
    return json.loads(spec_path.read_text(encoding="utf-8"))


def first_sentence(operation: Mapping[str, Any]) -> str:
    description = str(operation.get("description") or "").strip()
    if description:
        return description.splitlines()[0].strip()
    summary = str(operation.get("summary") or "").strip()
    if summary:
        return summary
    return "Documented API operation."


def build_api_table(spec: Mapping[str, Any]) -> str:
    rows = ["| Endpoint | Purpose |", "| --- | --- |"]
    paths = spec.get("paths", {})
    if not isinstance(paths, Mapping):
        raise SystemExit("Generated OpenAPI document has no paths object")

    for path in sorted(paths):
        operations = paths[path]
        if not isinstance(operations, Mapping):
            continue
        for method in sorted(operations):
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            operation = operations[method]
            if not isinstance(operation, Mapping):
                continue
            endpoint = f"`{method.upper()} {path}`"
            rows.append(f"| {endpoint} | {first_sentence(operation)} |")

    return "\n".join(rows)


def tracked_dirs(repo_root: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-d", "-r", "--name-only", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def build_project_structure_table(repo_root: Path) -> str:
    tracked = tracked_dirs(repo_root)
    rows = ["| Path | Purpose |", "| --- | --- |"]
    for path, purpose in PROJECT_STRUCTURE.items():
        if path in tracked or (repo_root / path).exists():
            rows.append(f"| `{path}` | {purpose} |")
    return "\n".join(rows)


def update_file(path: Path, replacements: Mapping[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for name, replacement in replacements.items():
        text = replace_block(text, name, replacement)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    spec = load_openapi(repo_root)
    api_table = build_api_table(spec)
    project_table = build_project_structure_table(repo_root)

    update_file(
        repo_root / "README.md",
        {
            "api-endpoints": api_table,
            "project-structure": project_table,
        },
    )
    update_file(
        repo_root / "docs" / "architecture.md",
        {
            "api-endpoints": api_table,
        },
    )
    print("Updated README.md and docs/architecture.md marker blocks")


if __name__ == "__main__":
    main()
