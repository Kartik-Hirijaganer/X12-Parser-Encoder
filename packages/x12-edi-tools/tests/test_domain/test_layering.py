"""Structural invariants for the domain layer.

Phase 1 DoD: no ``domain/*`` module may import from ``models/``, ``parser/``,
or ``encoder/``. This test is intentionally AST-based so it catches reach-
through even if ``from x import *`` or runtime imports sneak in.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

FORBIDDEN_PREFIXES = (
    "x12_edi_tools.models",
    "x12_edi_tools.parser",
    "x12_edi_tools.encoder",
    "x12_edi_tools.builders",
    "x12_edi_tools.readers",
    "x12_edi_tools.validator",
)

DOMAIN_ROOT = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "src" / "x12_edi_tools" / "domain"
)


def _domain_modules() -> list[pathlib.Path]:
    return sorted(DOMAIN_ROOT.glob("*.py"))


@pytest.mark.parametrize("module_path", _domain_modules(), ids=lambda p: p.name)
def test_no_cross_layer_imports(module_path: pathlib.Path) -> None:
    tree = ast.parse(module_path.read_text())
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith(FORBIDDEN_PREFIXES):
                offenders.append(module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(FORBIDDEN_PREFIXES):
                    offenders.append(alias.name)
    assert not offenders, (
        f"{module_path.name} imports from forbidden layer(s): {offenders}. "
        "Domain objects must remain X12-agnostic."
    )


def test_domain_root_exists() -> None:
    assert DOMAIN_ROOT.is_dir()
    assert (DOMAIN_ROOT / "__init__.py").exists()
