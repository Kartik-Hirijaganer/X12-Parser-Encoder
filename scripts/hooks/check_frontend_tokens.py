"""Guard #1 — Frontend token discipline.

Blocks arbitrary Tailwind values that should be CSS custom properties defined
in apps/web/src/styles/tokens.css. Patterns caught:
  - text-[13px]          arbitrary pixel font sizes
  - p-[13px]             arbitrary pixel padding
  - m-[13px]             arbitrary pixel margin
  - gap-[13px]           arbitrary pixel gap
  - w-[640px]            arbitrary pixel width
  - h-[640px]            arbitrary pixel height
  - max-w-[640px]        arbitrary pixel max-width
  - min-w-[640px]        arbitrary pixel min-width
  - max-h-[640px]        arbitrary pixel max-height
  - bg-[#abc123]         hardcoded hex background colour
  - text-[#abc123]       hardcoded hex text colour
  - border-[#abc123]     hardcoded hex border colour

Allowed (not flagged):
  - text-[var(--my-token)]   CSS variable reference — correct usage
  - text-sm / text-base       Tailwind design-scale classes — fine
  - max-w-screen-xl           named breakpoint — fine
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Add scripts/ root to path so _common is importable directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit_block, get_file_path, path_matches, read_hook_payload

INCLUDE_GLOBS = [
    "apps/web/src/**/*.tsx",
    "apps/web/src/**/*.ts",
    "apps/web/src/**/*.css",
]

# Patterns that indicate a hardcoded value instead of a token reference.
# The key is the human-readable description; the value is a compiled regex.
_VIOLATIONS: list[tuple[str, re.Pattern[str]]] = [
    (
        "arbitrary pixel value (e.g. text-[13px])",
        re.compile(
            r'\b(?:text|p|px|py|pt|pr|pb|pl|m|mx|my|mt|mr|mb|ml|gap|space-x|space-y|'
            r'w|h|max-w|min-w|max-h|min-h|top|right|bottom|left|inset|'
            r'rounded|border|ring|translate-x|translate-y|rotate|skew-x|skew-y|'
            r'basis|grow|shrink)-\[(?!var\()[^\]]*\d+px[^\]]*\]'
        ),
    ),
    (
        "hardcoded hex colour (e.g. bg-[#abc123])",
        re.compile(r'\b(?:bg|text|border|ring|shadow|fill|stroke|from|via|to|caret|accent)-\[#[0-9a-fA-F]{3,8}\]'),
    ),
    (
        "hardcoded rem/em value (e.g. text-[1.25rem])",
        re.compile(
            r'\b(?:text|p|px|py|pt|pr|pb|pl|m|mx|my|mt|mr|mb|ml|gap|w|h|'
            r'max-w|min-w|max-h|min-h|top|right|bottom|left|inset|leading|tracking)-'
            r'\[(?!var\()[^\]]*\d+(?:rem|em)[^\]]*\]'
        ),
    ),
]


def check_file(path: str) -> list[str]:
    """Return a list of violation messages for a single file."""
    p = Path(path)
    if not p.exists():
        return []
    source = p.read_text(encoding="utf-8")
    violations: list[str] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        for description, pattern in _VIOLATIONS:
            for match in pattern.finditer(line):
                violations.append(
                    f"  {path}:{lineno}  {match.group()!r}  — {description}"
                )
    return violations


def scan_directory(root: str) -> list[str]:
    """Scan all matching files under root and return all violations."""
    all_violations: list[str] = []
    for p in Path(root).rglob("*"):
        if p.suffix in {".tsx", ".ts", ".css"} and "node_modules" not in str(p):
            all_violations.extend(check_file(str(p)))
    return all_violations


def main() -> None:
    if len(sys.argv) >= 2:
        arg = sys.argv[1]
        if arg == "--scan":
            root = sys.argv[2] if len(sys.argv) >= 3 else "apps/web/src"
            violations = scan_directory(root)
            if violations:
                emit_block(
                    "GUARD #1 — Frontend token violations found:\n"
                    + "\n".join(violations)
                    + "\n\nFix: add a named CSS custom property to apps/web/src/styles/tokens.css "
                    "and reference it as e.g. text-[var(--my-token)]."
                )
            sys.exit(0)
        # Direct path invocation (used by make check-guards and tests).
        file_path = arg
    else:
        payload = read_hook_payload()
        file_path = get_file_path(payload)

    if not path_matches(file_path, INCLUDE_GLOBS):
        sys.exit(0)

    violations = check_file(file_path)
    if violations:
        emit_block(
            "GUARD #1 — Frontend token discipline violation(s) in "
            + file_path
            + ":\n"
            + "\n".join(violations)
            + "\n\nFix: add a named CSS custom property to apps/web/src/styles/tokens.css "
            "and reference it as e.g. text-[var(--my-token)] instead of a raw value."
        )


if __name__ == "__main__":
    main()
