# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Canonical AWS Account

- The canonical AWS account for this project is `970385384114`.
- Do not infer the deployment account from the currently active default AWS CLI profile.
- Before any AWS bootstrap, Terraform, GitHub Actions deploy setup, or production deploy, verify the selected credentials:

```bash
aws sts get-caller-identity --query Account --output text
```

- Proceed with production deployment work only when the verified account is `970385384114`.
- GitHub Actions deploy configuration for this project should use repository variable `AWS_ACCOUNT_ID=970385384114`.
- The Terraform/GitHub Actions deploy path defaults to `AWS_REGION=us-east-2` unless the user explicitly changes it.

## Commands

All development is driven from the repo root via `make`. The first run creates `.venv/` and installs the Python library, the API, and the web app's npm deps.

```bash
make install        # bootstrap venv, pip install -e for lib + api, npm install for web
make lint           # ruff format --check + ruff check for lib & api, eslint for web
make typecheck      # mypy (strict) for lib/src and api/app, tsc --noEmit for web
make format         # ruff format + ruff check --fix; eslint --fix
make test           # runs test-lib, test-api, test-web in sequence
make coverage       # enforces --cov-fail-under=95 (lib), 85 (api), plus web coverage
```

Split test runs (prefer these when iterating on one surface):

```bash
make test-lib       # cd packages/x12-edi-tools && pytest
make test-api       # cd apps/api            && pytest
make test-web       # cd apps/web            && npm run test -- --run
```

Single test targeting (run from the package directory so `pyproject.toml` / `pythonpath` resolves):

```bash
cd packages/x12-edi-tools && pytest tests/test_parser/test_tokenizer.py::test_strips_isa_whitespace -x
cd apps/api               && pytest tests/test_validate_parse.py -k "validate" -x
cd apps/web               && npm run test -- --run src/__tests__/PreviewPage.test.tsx
```

Release & hygiene scripts (must be invoked with the venv active — `make install` prepends `.venv/bin` when called through make targets):

```bash
python scripts/bump_version.py <major|minor|patch|X.Y.Z>   # updates VERSION + release-bearing files
make check-version-sync                                     # CI gate: VERSION == every version string
make check-oss                                              # CI gate: no proprietary content leaked
make check-hygiene                                          # CI gate: metadata/ not re-introduced
make docs                                                   # validate docs/api/openapi.yaml, regenerate ERD if graphviz present
make docs-regenerate                                        # write generated OpenAPI, diagrams, ERD, and marker blocks
make docs-check                                             # verify generated docs in a temp copy and fail on drift
```

Dev servers:

```bash
cd apps/api  && uvicorn app.main:app --reload               # FastAPI on :8000
cd apps/web  && npm run dev                                 # Vite on :5173 (proxies /api → :8000, override via VITE_API_PROXY_TARGET)
make rebuild                                                 # docker compose down + up --build for full-stack local
```

## Architecture

### Three deliverables, one release train

The monorepo ships three artifacts that are versioned together through `VERSION` and `scripts/bump_version.py`:

- **`packages/x12-edi-tools/`** — the framework-agnostic Python library. Publishes to PyPI as `x12-edi-tools`.
- **`apps/api/`** — a FastAPI service (`app.main:create_app`) that wraps the library behind HTTP endpoints and is the only place that handles uploads, correlation IDs, origin-secret checks, and metrics.
- **`apps/web/`** — the React + Vite workbench (routed SPA) that calls the API. In Lambda production, CloudFront serves the SPA from private S3; in local/container mode the API can still serve `apps/web/dist` (see `_register_frontend` in `apps/api/app/main.py`).

### Library layout (`x12_edi_tools`)

The public surface is pinned in [packages/x12-edi-tools/src/x12_edi_tools/__init__.py](packages/x12-edi-tools/src/x12_edi_tools/__init__.py). **Any change to re-exports is an API change.** The three entry points are:

- `parse(raw_x12, strict=..., on_error=...)` → returns a `ParseResult` (not a bare `Interchange`). `ParseResult` preserves transaction-scoped recovery, warnings, and per-transaction errors even when `on_error="collect"`. Callers must never assume an `Interchange` return type.
- `encode(interchange, delimiters=None, config=None)` → roundtrip-safe. Preserves delimiters and control numbers from the source interchange unless the caller explicitly requests regeneration.
- `validate(interchange, levels=None, profile=None, custom_rules=None)` → layers SNIP 1–5 generic checks (`validator/snip1.py`…`snip5.py`) with payer-profile rules loaded by name (e.g. `profile="dc_medicaid"`).

Internal module layout — keep these boundaries; the Phase 1 layering guard enforces that `domain/` does not import from `parser/`, `encoder/`, or `validator/`:

- `models/` — typed `Interchange`, `FunctionalGroup`, `Transaction270/271/835/837i/837p` envelopes (`models/transactions/`) plus segment and loop primitives.
- `domain/` — reusable domain objects (`claim.py`, `remittance.py`, `patient.py`, …) independent of any wire format.
- `parser/` — tokenizer → segment parser → loop builder → transaction dispatch pipeline.
- `encoder/` — segment/ISA/x12/claim encoders that reverse the parser.
- `validator/` — SNIP levels plus `context.py` for registry lookups (member / provider).
- `payers/` — per-payer profile packs. The DC Medicaid pack has split profiles for 270/271, 835, 837I, 837P (`payers/dc_medicaid/profile*.py`).
- `builders/` + `readers/` — claim (`builders/claim_837i.py`, `claim_837p.py`) and remittance (`readers/remittance_835.py`) convenience layers.
- `convenience.py` — the spreadsheet-oriented helpers (`from_csv`, `from_excel`, `build_270`, `read_271`) the web app consumes indirectly via the API.

Phase 0/1/7 note: 837I/837P/835 symbols (`ClaimBuildOptions`, `PartitioningStrategy`, `ClaimValidationError`, `RemittanceParseError`, validator context types) are currently imported under `TYPE_CHECKING` only and are intentionally **not** in `__all__` until Phase 7 flips them to runtime exports. Don't promote them early.

### API layout (`apps/api/app`)

- `main.py` — `create_app()` wires middleware, `/healthz`, `/metrics`, the frontend mount, and the versioned API router.
- `core/` — `config` (pydantic-settings), `logging`, `metrics` (Prometheus registry + `render_metrics_response`), `middleware` (correlation ID, size limits, request metrics).
- `routers/` — one module per endpoint: `convert`, `generate`, `validate`, `parse`, `export`, `pipeline`, `profiles`, `templates`, `health`. All mount under `settings.api_v1_prefix` (`/api/v1`).
- `services/` — adapters that call into `x12_edi_tools` (`generator`, `validator`, `parser`, `exporter`, `patients`, `profiles`, `templates`, `uploads`, `health`). Routers should stay thin; business logic belongs here.
- `schemas/` — Pydantic request/response contracts.

**Statelessness invariant**: uploads are read in-memory, size-checked, hashed for sanitized audit logs, and discarded. Do **not** add a database, queue, or server-side file retention (see Safety below).

### Web layout (`apps/web/src`)

- `App.tsx` — `react-router-dom` v7 routes: `/`, `/preview`, `/generate/result`, `/validate/result`, `/dashboard`, `/templates`, `/settings`.
- `hooks/useSettings.tsx` — the `SettingsProvider` is the only sanctioned `localStorage` consumer (key `x12_submitter_config`).
- `components/ui/` — design-system primitives. UI code must compose these; see the Frontend conventions.
- `components/features/`, `pages/`, `services/` — feature components, routed pages, and API clients.
- `styles/tokens.css` — Tailwind v4 `@theme` tokens; the only place concrete hex / radius / shadow values live.

### Request lifecycle (browser → library)

1. Browser uploads a spreadsheet or raw X12 to the API.
2. Middleware assigns / propagates `X-Correlation-ID`, enforces request-size limits, and records Prometheus metrics.
3. The matching service in `apps/api/app/services/` normalizes input and calls `parse` / `encode` / `validate` with the correlation ID.
4. Library returns `ParseResult` / encoded text / `ValidationResult`; the router shapes the response and the upload is discarded.

### Documentation sources of truth

Conflicts between frontend docs: `apps/web/src/styles/tokens.css` wins for concrete values, `docs/design-spec.md` wins for enforceable rules and roles, and `docs/ui-components.md` remains the primitive API appendix. `docs/architecture.md` covers system-level boundaries.

Generated documentation uses marker blocks. Run `make docs-regenerate` after changing API routes, schemas, Python module imports, `VERSION`, or Terraform module docs. Run `make docs-check` before handing off changes that should not drift generated docs.

## Conventions

### Scope

- Implement work in the current phase only unless the user asks to go further.
- Keep the Python library reusable and framework-agnostic.
- Keep the web app stateless. Do not add databases, background queues, or server-side file retention.

### Safety

- Treat all fixture data as synthetic only. Never add real patient data.
- Do not log raw X12 payloads, filenames, names, member identifiers, or other sensitive values. Structured logs carry correlation IDs, endpoint names, status codes, durations, and sanitized upload metadata only.
- Keep `metadata/` local-only. It is a development reference and must not be reintroduced to source control (`make check-hygiene` gates this).

### Python

- Target Python 3.11+ and prefer standard-library solutions first.
- Use Pydantic v2 models for request/config/domain contracts where validation matters.
- Keep public package APIs explicit through `x12_edi_tools.__init__`. Phase 7 types stay in `TYPE_CHECKING` until promoted.
- `mypy` runs in strict mode for both `packages/x12-edi-tools/src` and `apps/api/app`.
- X12 segment IDs are domain identifiers. Filenames and symbols such as `sv2.py`,
  `sv3.py`, `SV2Segment`, and `SV3Segment` are allowed even though they contain
  numeric suffixes; they are not release/version markers and should not be
  renamed for generic banned-name checks.

### Frontend

- Use React + TypeScript + Vite.
- **Before writing any UI code, read `docs/design-spec.md`.** It is the single enforceable frontend design contract and links to the detailed visual and primitive appendices.
- **Token source of truth**: `apps/web/src/styles/tokens.css` is the only place concrete hex values, radii, shadows, fonts, and motion tokens live. Never hardcode hex values, pixel spacing, or arbitrary Tailwind values (`bg-[#...]`, `p-[13px]`). If you need a new value, add it to `tokens.css` first as a named token, then reference the token.
- **Primitive-first**: every interactive element, table, file input, card, badge, banner, and spinner must use the matching primitive under `apps/web/src/components/ui/` (`Button`, `Table`, `FileUpload`, `Card`, `Badge`, `Banner`, `Spinner`, `Icons`). Do not hand-roll raw `<button>`, `<table>`, or `<input type="file">`, and do not duplicate an existing primitive with a one-off component.
- **Storage boundary**: do not persist patient data in `localStorage`, `sessionStorage`, or `IndexedDB`. The only sanctioned `localStorage` key is `x12_submitter_config` for non-PHI submitter configuration.
- **Every new visual pattern lands as a triplet**: update `docs/design-spec.md`, update or add the primitive, and add or extend the primitive's test. If the pattern needs a new token, update `tokens.css` in the same change.
- **When rules conflict**: `tokens.css` wins for values, `docs/design-spec.md` wins for rules and roles, and `docs/ui-components.md` wins for primitive APIs. Fix the drift in the same PR rather than working around it.

### Release

- `VERSION` is the repo-wide source of truth. Do not hand-edit scattered version strings; use `scripts/bump_version.py`.
- `make check-version-sync`, `make check-oss`, and `make check-hygiene` back CI gates; run them locally before opening PRs that touch release metadata.

## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
