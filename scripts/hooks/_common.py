"""Shared helpers for Claude Code hook scripts.

Each hook script is invoked in two modes:
  - Hook mode: stdin carries the JSON payload from Claude Code.
  - CLI mode: a file path is passed as a positional argument (used by tests
    and by `make check-guards`).
"""

from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path
from typing import NoReturn


def read_hook_payload() -> dict:
    """Parse the JSON payload from Claude Code on stdin."""
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def get_file_path(payload: dict) -> str:
    """Extract the affected file path from a hook payload.

    PostToolUse Edit/Write payloads carry tool_input.file_path.
    PreToolUse Bash payloads carry tool_input.command (not a path).
    """
    tool_input = payload.get("tool_input", {})
    return tool_input.get("file_path", "")


def get_bash_command(payload: dict) -> str:
    """Extract the bash command from a PreToolUse Bash payload."""
    tool_input = payload.get("tool_input", {})
    return tool_input.get("command", "")


def path_matches(path: str, include: list[str], exclude: list[str] | None = None) -> bool:
    """Return True if path matches any include glob and no exclude glob.

    Globs are matched against the full path string using fnmatch, which
    supports ``*`` (any segment chars) and ``**`` (any path prefix/suffix).
    The ``**`` matching is approximated by stripping the ``**/`` prefix and
    matching the remainder against the basename + any trailing portion.
    """
    if not path:
        return False

    def _matches_glob(p: str, pattern: str) -> bool:
        if "**" in pattern:
            # Treat **/ as "anywhere in the path tree".
            stripped = pattern.replace("**/", "")
            return fnmatch.fnmatch(Path(p).name, stripped) or fnmatch.fnmatch(p, pattern)
        return fnmatch.fnmatch(p, pattern)

    included = any(_matches_glob(path, g) for g in include)
    if not included:
        return False
    if exclude:
        excluded = any(_matches_glob(path, g) for g in exclude)
        if excluded:
            return False
    return True


def emit_block(message: str) -> NoReturn:
    """Print message to stderr and exit 2 (Claude Code blocking exit code)."""
    print(message, file=sys.stderr)
    sys.exit(2)
