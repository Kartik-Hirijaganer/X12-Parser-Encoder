# Hooks Implementation Plan — Claude Code + Codex

## Context

This repo (X12 EDI parser/encoder monorepo) already has strong conventions codified in [CLAUDE.md](../../CLAUDE.md) — token discipline, primitive-first UI, localStorage boundary, structured logging, public API surface, TYPE_CHECKING quarantine for Phase 7 symbols, statelessness invariant. The problem is that **Claude (and Codex) will drift past those rules mid-flow when they are only documented in prose**. An Explore pass found 7 live token-discipline violations already in `apps/web/src/` today, and no runtime guard exists for the public `__all__` in [packages/x12-edi-tools/src/x12_edi_tools/__init__.py](../../packages/x12-edi-tools/src/x12_edi_tools/__init__.py) or for accidental Phase 7 symbol promotion.

The goal: make the documented rules *deterministically enforceable* via hooks, for zero marginal token cost at runtime, and mirror that enforcement for Codex through a hierarchical `AGENTS.md` layout and a shared `make check-guards` command. We are explicitly **not** building skills for "new feature / new endpoint / new table" — the recommendation template came from a DB-backed stack, but this repo is stateless by invariant (no DB, no queue), so those skills would be solving a problem we don't have. The existing `.claude/skills/` catalog already covers audit/refactor/review.

## Disagreements with the original recommendation

1. **Cut auto-format-on-save hook.** It mutates the file Claude just wrote, which makes the next `Edit` hit a stale `old_string` and fail mid-turn. It also doubles the existing `code-review-graph update` hook churn. Format belongs in `pre-commit`, which is already wired.
2. **Cut the "new-table / new-endpoint / migration" skills and the `duplicate_guard.py` for migrations.** This repo has no Alembic, no DB, no server-side persistence — CLAUDE.md's statelessness invariant forbids them. Duplicate-fixture detection was considered but current fixture drift is low and this would be speculative.
3. **Cut PreToolUse redirect on VERSION edits.** `scripts/check_version_sync.py` + `make check-version-sync` already gate drift in CI; an in-turn redirect is noise.
4. **Hooks must block with `exit 2`, not warn with `exit 1`.** Per Claude Code hook semantics, only `exit 2` feeds stderr back to the model as corrective input; `exit 1` shows the user but not the model. Advisory-only hooks get ignored.
5. **Pre-commit additions become a `make check-guards` command, not new `.pre-commit-config.yaml` hooks.** Avoids adding slow pre-commit wrappers and gives Codex, CI, and humans a single explicit command to run.

## Hooks being added

All Python hook scripts live under [scripts/hooks/](../../scripts/hooks/) and use **stdlib only** (`ast`, `re`, `pathlib`, `json`, `sys`, `tomllib`) unless noted. Each script reads the hook payload from stdin as JSON per Claude Code's hook contract, extracts the `tool_input.file_path`, runs its check, and exits 0 (silent pass) or 2 (block with stderr).

### Claude Code hooks — `.claude/settings.json`

| # | Hook | Event / Matcher | Script | Trigger | Tokens | Libs | Benefit | Exit behavior |
|---|------|-----------------|--------|---------|--------|------|---------|---------------|
| 1 | **Frontend token discipline** | `PostToolUse` matcher `Edit\|Write`, path filter `apps/web/src/**/*.{tsx,ts,css}` | `scripts/hooks/check_frontend_tokens.py` | After any web write | 0 on pass, ~50 on block | stdlib `re` | Catches `text-[13px]`, `bg-[#ffffff]`, `max-w-[1200px]`, `p-[13px]` and forces use of `tokens.css`. 7 live violations exist today. | Exit 2 with list of offending lines |
| 2 | **Primitive-first guard** | `PostToolUse` matcher `Edit\|Write`, path filter `apps/web/src/{pages,components/features}/**/*.tsx`, excludes `*.test.tsx` | `scripts/hooks/check_primitives.py` | After feature/page writes | 0 on pass, ~40 on block | stdlib `re` | Flags raw `<button>`, `<table>`, `<input type="file">` in feature code; directs to `components/ui/` primitives. | Exit 2 |
| 3 | **localStorage boundary** | `PostToolUse` matcher `Edit\|Write`, path filter `apps/web/src/**/*.{ts,tsx}`, excludes `*.test.tsx`, `setupTests.ts`, `hooks/useSettings.tsx` | `scripts/hooks/check_localstorage.py` | After web writes | 0 on pass, ~30 on block | stdlib `re` | Any `localStorage.setItem/getItem/removeItem` must reference `SETTINGS_STORAGE_KEY` constant, not a string literal. | Exit 2 |
| 4 | **Structured logging enforcer** | `PostToolUse` matcher `Edit\|Write`, path filter `packages/x12-edi-tools/src/**/*.py`, `apps/api/app/**/*.py` | `scripts/hooks/check_logging.py` | After Python writes in lib/api | 0 on pass, ~60 on block | stdlib `ast` | Flags `logger.{info,debug,warning,error}` calls that use f-strings, `%` formatting, or `.format()`, or omit `extra=build_log_extra(...)`. Enforces the pattern already used at `x12_parser.py:51`, `x12_encoder.py:91`, `x12_validator.py:42`. | Exit 2 |
| 5 | **Public API gate** | `PostToolUse` matcher `Edit\|Write`, path filter `packages/x12-edi-tools/src/x12_edi_tools/__init__.py` | `scripts/hooks/check_api_surface.py` | After `__init__.py` edits | 0 on pass, ~80 on block | stdlib `ast` + `difflib` against a committed `api_surface.lock` | Detects changes to `__all__` or top-level re-exports. Blocks with directive to run `python scripts/bump_version.py <level>` and add `CHANGELOG.md` entry. | Exit 2 (block — warn-only gets ignored) |
| 6 | **TYPE_CHECKING quarantine** | `PostToolUse` matcher `Edit\|Write`, path filter `**/*.py` | `scripts/hooks/check_type_checking.py` | After any Python write | 0 on pass, ~50 on block | stdlib `ast` | Flags runtime imports of `ClaimBuildOptions`, `PartitioningStrategy`, `ClaimValidationError`, `RemittanceParseError`, `ValidationContext`, `MemberRegistryLookup`, `ProviderRegistryLookup` from `x12_edi_tools` outside `if TYPE_CHECKING:` blocks. Keeps Phase 7 quarantine intact. | Exit 2 |
| 7 | **Statelessness invariant** | `PostToolUse` matcher `Edit\|Write`, path filter `apps/api/app/**/*.py` | `scripts/hooks/check_statelessness.py` | After API writes | 0 on pass, ~40 on block | stdlib `ast` | Flags any new import of `sqlalchemy`, `redis`, `celery`, `rq`, or `boto3.resource('s3')`-style retention. CLAUDE.md "no database, queue, or server-side file retention" becomes machine-checked. | Exit 2 |
| 8 | **Routers-stay-thin nudge** | `PostToolUse` matcher `Edit\|Write`, path filter `apps/api/app/routers/**/*.py` | `scripts/hooks/check_router_thinness.py` | After router writes | 0 on pass, ~40 on block | stdlib `ast` | Flags routers that import `x12_edi_tools` directly (should go through `services/`) or contain function bodies > 40 lines. | Exit 2 |
| 9 | **Design-system triplet reminder** | `PostToolUse` matcher `Edit\|Write`, path filter `docs/design-system.md`, `docs/ui-components.md`, `apps/web/src/styles/tokens.css` | `scripts/hooks/check_design_triplet.py` | After any doc/token edit | 0 on pass, ~30 on block | stdlib `re` + git plumbing | Reminds that edits to one of the three must touch or justify skipping the other two per CLAUDE.md. Uses `git diff --name-only HEAD` to check. | Exit 2 unless all three touched |
| 10 | **Destructive Bash safety net** | `PreToolUse` matcher `Bash`, regex on command string | `scripts/hooks/check_bash_destructive.py` | Before any Bash | 0 on pass, ~30 on block | stdlib `re` | Blocks `rm -rf`, `git push --force`, `git reset --hard`, `git checkout --`, `git clean -f`, `git branch -D` without explicit user authorization. | Exit 2 with reminder to ask user first |
| 11 | **Stop gate — fast lint** | `Stop` matcher `""` | `make lint` (inline command) | Before turn ends | ~0 on pass, ~200 on block (lint output) | ruff, eslint (already installed) | Final deterministic gate: if the turn shipped unformatted or lint-broken code, Claude sees the failure and fixes before ending. Only `make lint` — NOT `make typecheck` or `make test`. | Exit 2 on lint failure |

**Preserve existing hooks**: the current `PostToolUse → code-review-graph update --skip-flows` and `SessionStart → code-review-graph status` entries stay intact; new hooks are additive entries in the same arrays.

### `make check-guards` — shared command for Codex + CI + humans

Replaces adding new entries to `.pre-commit-config.yaml`. A single command iterates `git diff --name-only --cached` (staged files), dispatches each path to the matching guard script, collects non-zero exits, prints a summary, and exits with the max exit code. This is the enforcement bridge for Codex (no PostToolUse equivalent), CI, and manual pre-commit runs.

Also wire the existing CI gates (`check-version-sync`, `check-oss`, `check-hygiene`) as dependencies of `make check-guards` so one command covers everything. The existing `.pre-commit-config.yaml` stays unchanged.

## Codex strategy

Codex has no PostToolUse equivalent — it reads `AGENTS.md` at session start and relies on explicit commands at commit time.

1. **Hierarchical `AGENTS.md`** (Codex's native idiom):
   - `AGENTS.md` (repo root) — references CLAUDE.md, summarizes the invariants Codex needs before any edit, instructs Codex to run `make check-guards` before committing.
   - `apps/web/AGENTS.md` — token discipline, primitive-first, localStorage boundary, design-system triplet rule.
   - `apps/api/AGENTS.md` — statelessness invariant, router thinness, structured logging.
   - `packages/x12-edi-tools/AGENTS.md` — layering guard, public API surface, TYPE_CHECKING quarantine, Phase 7 rules.

2. **`make check-guards` is the enforcement bridge**: Codex runs `make check-guards` → same scripts that power Claude Code hooks run → violations surface before commit.

3. **Document recommended Codex config** in repo-root `AGENTS.md`:
   - `approval_policy = "on-request"` — statelessness/API-surface guards are too important to auto-approve around.
   - `sandbox_mode = "workspace-write"` — Codex needs to run `make check-guards` and `ruff format`.
   - Do not use `--dangerously-bypass-approvals-and-sandbox`.

## Files to create or modify

**Created**:
- `scripts/hooks/_common.py` — shared helpers: `read_hook_payload()`, `path_matches()`, `emit_block()`
- `scripts/hooks/check_frontend_tokens.py`
- `scripts/hooks/check_primitives.py`
- `scripts/hooks/check_localstorage.py`
- `scripts/hooks/check_logging.py`
- `scripts/hooks/check_api_surface.py`
- `scripts/hooks/check_type_checking.py`
- `scripts/hooks/check_statelessness.py`
- `scripts/hooks/check_router_thinness.py`
- `scripts/hooks/check_design_triplet.py`
- `scripts/hooks/check_bash_destructive.py`
- `scripts/hooks/api_surface.lock` — committed snapshot of current `__all__`
- `scripts/hooks/tests/` — one `test_<guard>.py` per script, table-driven (violating + passing fixtures)
- `AGENTS.md` (repo root)
- `apps/web/AGENTS.md`
- `apps/api/AGENTS.md`
- `packages/x12-edi-tools/AGENTS.md`

**Modified**:
- [.claude/settings.json](../../.claude/settings.json) — add `PostToolUse`, `PreToolUse`, `Stop` entries; existing `code-review-graph` hooks preserved.
- [Makefile](../../Makefile) — add `check-guards` target.
- [CLAUDE.md](../../CLAUDE.md) — append "Hook enforcement" section (~40 lines) listing what each guard blocks.

**Not modified**: `.pre-commit-config.yaml` — stays as-is.

**Reused (do not reimplement)**:
- AST-walking pattern from [packages/x12-edi-tools/tests/test_domain/test_layering.py](../../packages/x12-edi-tools/tests/test_domain/test_layering.py) — reuse in `check_type_checking.py`, `check_statelessness.py`, `check_router_thinness.py`, `check_logging.py`.
- `build_log_extra` at `packages/x12-edi-tools/src/x12_edi_tools/_logging.py` — guard #4 checks calls conform to this.
- `SETTINGS_STORAGE_KEY` at `apps/web/src/hooks/useSettings.tsx` — guard #3 enforces reference to this.
- `scripts/check_version_sync.py`, `scripts/check_no_proprietary_content.py`, `scripts/check_repo_hygiene.py` — called by `make check-guards`, not rewritten.

## Implementation steps (agent-executable)

1. **Scaffold**. Create `scripts/hooks/` and `scripts/hooks/tests/`. Write `scripts/hooks/_common.py` with:
   - `read_hook_payload() -> dict` — parses stdin JSON, returns the full payload
   - `get_file_path(payload: dict) -> str` — extracts `tool_input.file_path` or `tool_input.command`
   - `path_matches(path: str, include: list[str], exclude: list[str]) -> bool` — fnmatch-based glob matching
   - `emit_block(message: str) -> NoReturn` — prints to stderr, `sys.exit(2)`

2. **Write each guard script TDD**: test fixtures (violating + passing code snippets) first in `scripts/hooks/tests/test_<guard>.py`, then the script. Each script:
   - CLI dual-mode: reads stdin JSON when invoked as a hook; accepts a path positional arg when invoked directly (for tests and `make check-guards`).
   - Exit 0 silent on pass.
   - Exit 2 with a short, fix-directive stderr message — e.g., `"GenerateResultPage.tsx:120 uses text-[13px]. Add --text-sm-note to tokens.css and reference it as text-[var(--text-sm-note)]."` Terse and actionable.
   - Complete in <200ms for a single file.

3. **Generate `api_surface.lock`** by running `python scripts/hooks/check_api_surface.py --snapshot` after writing the script, and committing the output.

4. **Fix 7 live frontend token violations** in `GenerateResultPage.tsx`, `SettingsPage.tsx`, `AppShell.tsx` before enabling guard #1. Add named tokens to [apps/web/src/styles/tokens.css](../../apps/web/src/styles/tokens.css) first.

5. **Add `make check-guards`** to Makefile. Iterates `git diff --name-only --cached --diff-filter=ACM`, dispatches each file to matching guards, also calls `make check-version-sync check-oss check-hygiene`, exits non-zero on any failure.

6. **Wire `.claude/settings.json`**: preserve existing entries; add each guard as a new `PostToolUse` / `PreToolUse` / `Stop` entry with `timeout: 5`. Path filtering is done inside the scripts via `path_matches()`.

7. **Write the four `AGENTS.md` files** — each 30–60 lines, referencing CLAUDE.md for detail and listing which guards will fire at `make check-guards` time.

8. **Append "Hook enforcement" section to CLAUDE.md** (~40 lines) documenting each guard, its file, and what it blocks.

9. **Run validation suite** (see below).

## Verification plan

```bash
# 1. Unit test all guards
pytest scripts/hooks/tests/ -x

# 2. Confirm 7 live token violations are gone
python scripts/hooks/check_frontend_tokens.py --scan apps/web/src

# 3. Smoke-test make check-guards on clean tree (should pass)
git add -A && make check-guards

# 4. Full existing suite must still pass
make lint typecheck test
```

Manual Claude Code smoke tests (new session):
- Add `max-w-[500px]` to any `.tsx` file → guard #1 blocks with stderr.
- Add a symbol to `__all__` in `__init__.py` → guard #5 blocks with bump directive.
- Add `import sqlalchemy` to any `apps/api/app/*.py` → guard #7 blocks.
- Run `rm -rf /tmp/test` via Bash tool → guard #10 blocks with user-confirmation prompt.

CI regression test:
- Add `localStorage.setItem('foo', 'bar')` to a non-test `.ts` file, run `make check-guards` → guard #3 must fail.
- Revert.

Performance gate:
- `time python scripts/hooks/check_logging.py packages/x12-edi-tools/src/x12_edi_tools/parser/x12_parser.py` → must be <200ms.
- `time make lint` on a clean tree → must be <5s.

## Out of scope (explicit non-goals)

- No duplicate-fixture or duplicate-test detection — current drift is low.
- No auto-format on save.
- No new skills.
- No replacement for `test_domain/test_layering.py` — keep the test-based guard; hooks are complementary.
- No `.pre-commit-config.yaml` modifications — `make check-guards` replaces that role.
