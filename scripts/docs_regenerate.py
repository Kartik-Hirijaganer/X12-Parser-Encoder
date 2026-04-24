#!/usr/bin/env python3
"""Regenerate all mechanically derived documentation artifacts."""

from __future__ import annotations

import argparse
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
    return parser.parse_args()


def run(command: list[str], *, cwd: Path) -> None:
    printable = " ".join(command)
    print(f"==> {printable}")
    subprocess.run(command, cwd=cwd, check=True)


def run_erd(repo_root: Path) -> None:
    erd_source = repo_root / "docs" / "erd.er"
    erd_output = repo_root / "docs" / "erd.svg"
    if not erd_source.exists():
        raise SystemExit("docs/erd.er is missing; cannot regenerate docs/erd.svg")

    if shutil.which("dot") is None:
        raise SystemExit(
            "Graphviz `dot` is required to regenerate docs/erd.svg. "
            "Install graphviz before running make docs-regenerate."
        )
    if shutil.which("eralchemy") is None:
        sibling = Path(sys.executable).resolve().parent / "eralchemy"
        if sibling.exists():
            eralchemy = str(sibling)
        else:
            raise SystemExit(
                "eralchemy is required to regenerate docs/erd.svg. "
                "Run `make install` to install repository dev dependencies."
            )
    else:
        eralchemy = "eralchemy"

    run([eralchemy, "-i", str(erd_source), "-o", str(erd_output)], cwd=repo_root)


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    scripts_dir = repo_root / "scripts"

    run(
        [
            sys.executable,
            str(scripts_dir / "generate_openapi.py"),
            "--repo-root",
            str(repo_root),
        ],
        cwd=repo_root,
    )
    run(
        [
            sys.executable,
            str(scripts_dir / "generate_route_diagram.py"),
            "--repo-root",
            str(repo_root),
        ],
        cwd=repo_root,
    )
    run(
        [
            sys.executable,
            str(scripts_dir / "generate_module_graph.py"),
            "--repo-root",
            str(repo_root),
        ],
        cwd=repo_root,
    )
    run_erd(repo_root)
    run(
        [
            sys.executable,
            str(scripts_dir / "update_readme.py"),
            "--repo-root",
            str(repo_root),
        ],
        cwd=repo_root,
    )


if __name__ == "__main__":
    main()
