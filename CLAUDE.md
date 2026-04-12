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
