#!/usr/bin/env python3
"""Generate the FastAPI OpenAPI document from the application object."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the parent of scripts/.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file. Defaults to docs/api/openapi.yaml under the repo root.",
    )
    return parser.parse_args()


def add_import_paths(repo_root: Path) -> None:
    for path in (
        repo_root / "apps" / "api",
        repo_root / "packages" / "x12-edi-tools" / "src",
    ):
        sys.path.insert(0, str(path))


def generate_spec(repo_root: Path) -> dict[str, Any]:
    os.environ.setdefault("X12_API_REPO_ROOT", str(repo_root))
    os.environ.setdefault("X12_API_DEPLOYMENT_TARGET", "lambda")
    add_import_paths(repo_root)

    from app.main import app  # noqa: PLC0415

    return app.openapi()


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output = args.output or repo_root / "docs" / "api" / "openapi.yaml"

    spec = generate_spec(repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(spec, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {output.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
