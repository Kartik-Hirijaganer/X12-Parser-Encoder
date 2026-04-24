#!/usr/bin/env python3
"""Generate the Python module dependency graph with pydeps."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


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
        help="Output SVG. Defaults to docs/diagrams/generated/module-deps.svg.",
    )
    return parser.parse_args()


def resolve_pydeps() -> str:
    candidate = shutil.which("pydeps")
    if candidate:
        return candidate

    sibling = Path(sys.executable).resolve().parent / "pydeps"
    if sibling.exists():
        return str(sibling)

    raise SystemExit(
        "pydeps is required to generate docs/diagrams/generated/module-deps.svg. "
        "Run `make install` to install the repository dev dependencies."
    )


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output = (
        args.output or repo_root / "docs" / "diagrams" / "generated" / "module-deps.svg"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    pythonpath = os.pathsep.join(
        [
            str(repo_root / "apps" / "api"),
            str(repo_root / "packages" / "x12-edi-tools" / "src"),
            env.get("PYTHONPATH", ""),
        ]
    )
    env["PYTHONPATH"] = pythonpath

    command = [
        resolve_pydeps(),
        str(repo_root / "apps" / "api" / "app"),
        "--noshow",
        "-T",
        "svg",
        "-o",
        str(output),
        "--only",
        "app",
        "x12_edi_tools",
        "--max-module-depth",
        "2",
        "--rankdir",
        "LR",
    ]
    subprocess.run(command, cwd=repo_root, env=env, check=True)

    if not output.exists():
        raise SystemExit(f"pydeps completed but did not write {output}")

    print(f"Generated {output.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
