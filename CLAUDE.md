# Project Conventions

## Scope

- Implement work in the current phase only unless the user asks to go further.
- Keep the Python library reusable and framework-agnostic.
- Keep the web app stateless. Do not add databases, background queues, or server-side file retention.

## Safety

- Treat all fixture data as synthetic only. Never add real patient data.
- Do not log raw X12 payloads, filenames, names, member identifiers, or other sensitive values.
- Keep `metadata/` local-only. It is a development reference and must not be reintroduced to source control.

## Python

- Target Python 3.11+ and prefer standard-library solutions first.
- Use Pydantic v2 models for request/config/domain contracts where validation matters.
- Keep public package APIs explicit through `x12_edi_tools.__init__`.

## Frontend

- Use React + TypeScript + Vite.
- Keep styling token-driven and centralized under `apps/web/src/styles/`.
- Do not persist patient data in browser storage. Only non-patient configuration belongs there.

## Tooling

- Use `ruff` for formatting and linting.
- Keep mypy clean for committed Python code.
- Prefer small smoke tests early so `make test` stays meaningful during scaffolding.

<!-- code-review-graph MCP tools -->
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
