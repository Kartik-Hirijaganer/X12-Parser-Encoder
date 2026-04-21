"""Tests for check_frontend_tokens.py."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "check_frontend_tokens.py"


def _run(content: str, suffix: str = ".tsx", path_override: str | None = None) -> subprocess.CompletedProcess[str]:
    """Write content to a temp file and run the guard against it."""
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, prefix="apps/web/src/pages/Test", delete=False
    ) as f:
        f.write(content)
        tmp = f.name

    target = path_override or tmp
    result = subprocess.run(
        [sys.executable, str(SCRIPT), target],
        capture_output=True,
        text=True,
    )
    Path(tmp).unlink(missing_ok=True)
    return result


# ---------------------------------------------------------------------------
# Passing cases — should exit 0 with no output
# ---------------------------------------------------------------------------


def test_token_reference_passes() -> None:
    code = '<p className="text-[var(--text-size-sm)] text-[var(--color-text-secondary)]">hello</p>'
    r = _run(code, path_override="apps/web/src/pages/OK.tsx")
    assert r.returncode == 0, r.stderr


def test_named_tailwind_class_passes() -> None:
    code = '<p className="text-sm text-base font-semibold leading-6">hello</p>'
    r = _run(code, path_override="apps/web/src/pages/OK.tsx")
    assert r.returncode == 0, r.stderr


def test_max_w_screen_breakpoint_passes() -> None:
    code = '<div className="mx-auto max-w-screen-xl px-6">hello</div>'
    r = _run(code, path_override="apps/web/src/pages/OK.tsx")
    assert r.returncode == 0, r.stderr


def test_non_web_path_skipped() -> None:
    code = '<p className="text-[13px]">should be ignored — not a web file</p>'
    r = _run(code, path_override="packages/x12-edi-tools/src/something.py")
    assert r.returncode == 0, r.stderr


def test_var_colour_passes() -> None:
    code = '<div className="bg-[var(--color-surface-dark)]">ok</div>'
    r = _run(code, path_override="apps/web/src/pages/OK.tsx")
    assert r.returncode == 0, r.stderr


# ---------------------------------------------------------------------------
# Failing cases — should exit 2 with descriptive stderr
# ---------------------------------------------------------------------------


def test_arbitrary_pixel_font_size_blocked() -> None:
    code = '<p className="text-[13px] text-[var(--color-text-secondary)]">hello</p>'
    r = _run(code, path_override="apps/web/src/pages/Bad.tsx")
    assert r.returncode == 2
    assert "text-[13px]" in r.stderr
    assert "token" in r.stderr.lower()


def test_max_w_pixel_blocked() -> None:
    code = '<div className="mx-auto max-w-[640px] gap-6">content</div>'
    r = _run(code, path_override="apps/web/src/pages/Bad.tsx")
    assert r.returncode == 2
    assert "max-w-[640px]" in r.stderr


def test_hardcoded_hex_bg_blocked() -> None:
    code = '<div className="bg-[#1c1e21]">dark</div>'
    r = _run(code, path_override="apps/web/src/pages/Bad.tsx")
    assert r.returncode == 2
    assert "#1c1e21" in r.stderr


def test_multiple_violations_all_reported() -> None:
    code = textwrap.dedent("""\
        <div className="text-[20px] max-w-[1200px]">
          <p className="text-[14px]">body</p>
        </div>
    """)
    r = _run(code, path_override="apps/web/src/pages/Bad.tsx")
    assert r.returncode == 2
    assert "text-[20px]" in r.stderr
    assert "max-w-[1200px]" in r.stderr
    assert "text-[14px]" in r.stderr


def test_rem_value_blocked() -> None:
    code = '<p className="text-[1.25rem]">hello</p>'
    r = _run(code, path_override="apps/web/src/pages/Bad.tsx")
    assert r.returncode == 2
    assert "1.25rem" in r.stderr
