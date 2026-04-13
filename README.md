# X12 Parser Encoder

[![PyPI version](https://img.shields.io/pypi/v/x12-edi-tools.svg)](https://pypi.org/project/x12-edi-tools/)
[![Python versions](https://img.shields.io/pypi/pyversions/x12-edi-tools.svg)](https://pypi.org/project/x12-edi-tools/)
[![Coverage](docs/coverage-badge.svg)](docs/coverage.md)
[![CI](https://github.com/Kartik-Hirijaganer/X12-Parser-Encoder/actions/workflows/ci.yml/badge.svg)](https://github.com/Kartik-Hirijaganer/X12-Parser-Encoder/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/Kartik-Hirijaganer/X12-Parser-Encoder.svg)](LICENSE)

Python-native tooling for X12 270/271 eligibility workflows: a reusable parsing and validation library, a FastAPI backend, and a React workbench for spreadsheet-to-X12 and 271 dashboard workflows.

## What Is X12 EDI?

X12 is the transaction format used by US healthcare trading partners to exchange structured claims, eligibility, remittance, and enrollment data. In this repository, the focus is the 270 eligibility inquiry and 271 eligibility response pair used to ask a payer for coverage status and interpret the response safely.

## Release Info

<!-- version-table:start -->
| Artifact | Version |
| --- | --- |
| Monorepo | `0.1.0` |
| Python package | `0.1.0` |
| API app | `0.1.0` |
| Web app | `0.1.0` |
<!-- version-table:end -->

## Project Structure

| Path | Purpose |
| --- | --- |
| `packages/x12-edi-tools` | Installable Python library for parsing, encoding, validation, payer profiles, and public types |
| `apps/api` | FastAPI service exposing upload, generation, validation, parse, export, health, profile, and pipeline endpoints |
| `apps/web` | React workbench for settings management, preview, generation, validation, templates, and eligibility dashboards |
| `docs/architecture.md` | System-level architecture and production boundaries |
| `docs/frontend-standards.md` | Frontend rules for storage, workflow routing, and shared UI primitives |
| `metadata/` | Local-only reference content, intentionally excluded from source control and release artifacts |

## Installation

### Library

```bash
pip install x12-edi-tools
```

Optional extras:

```bash
pip install "x12-edi-tools[excel]"
pip install "x12-edi-tools[pandas]"
pip install "x12-edi-tools[all]"
```

### From Source

```bash
make install
```

## Quick Start

```python
from pathlib import Path

from x12_edi_tools import encode, parse, validate

raw_x12 = Path("request.270").read_text(encoding="utf-8")
parse_result = parse(raw_x12, strict=False, on_error="collect")
interchange = parse_result.interchange

validation = validate(interchange, profile="dc_medicaid", levels={1, 2, 3, 4, 5})
assert validation.is_valid

roundtripped = encode(interchange)
Path("roundtrip.270").write_text(roundtripped, encoding="utf-8")
```

## API Reference Summary

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/convert` | Canonical CSV/XLSX/TXT template to normalized patient JSON |
| `POST /api/v1/generate` | Patient JSON plus config to X12 270 document or ZIP batch |
| `POST /api/v1/validate` | Raw X12 to SNIP and payer-profile validation results |
| `POST /api/v1/parse` | Raw 271 to eligibility dashboard data |
| `POST /api/v1/export/xlsx` | Eligibility dashboard data to workbook export |
| `POST /api/v1/pipeline` | Single request convert plus generate plus validate flow |
| `GET /api/v1/templates/{name}` | Canonical CSV and XLSX templates plus template spec |
| `GET /api/v1/profiles` | Available payer profile packs |
| `GET /api/v1/profiles/{name}/defaults` | Defaults surfaced by a payer profile |
| `GET /api/v1/health` | Deep application health check |
| `GET /healthz` | Shallow process health probe |
| `GET /metrics` | Prometheus-formatted request and workload metrics |

## Web Application Usage

1. Open the home page and choose generate, validate, or parse.
2. Configure submitter and payer defaults on the Settings page. Only configuration lives in `localStorage`.
3. Upload a spreadsheet to preview corrections and row-level errors before generation, or upload raw X12 for validate and parse flows.
4. Download generated X12, ZIP batches, or Excel eligibility exports from the result screens.

## Templates

- `apps/api/templates/eligibility_template.csv`
- `apps/api/templates/eligibility_template.xlsx`
- `apps/api/templates/template_spec.md`

The template spec defines canonical column names, required inputs, and the normalization rules applied by the API before X12 generation.

## Development Setup

```bash
make install
make lint
make typecheck
make test
make coverage
```

Useful Phase 8 commands:

- `python scripts/check_version_sync.py`
- `python scripts/check_no_proprietary_content.py`
- `python scripts/bump_version.py patch`

## Deployment Guide

### Docker

```bash
docker build -f docker/Dockerfile -t x12-parser-encoder .
docker run --rm -p 8000:8000 x12-parser-encoder
```

### Web + API

- Vercel plus Render: deploy the React app and API separately for demo environments without PHI.
- Cloud Run: deploy the containerized API and static frontend together for production-style environments with external identity boundaries and metrics scraping.

The GitHub workflows in `.github/workflows/` cover CI, release publishing, and configurable deploy automation.

## PHI Handling Notes

- No real patient data belongs in tests, fixtures, or logs.
- Uploaded files are processed in memory and not persisted to disk.
- Structured logs carry correlation IDs, endpoint names, status codes, durations, and sanitized upload metadata only.
- Browser storage is limited to submitter and payer configuration; workflow data stays in memory.
- See [SECURITY.md](SECURITY.md) for the retention policy and production readiness gate.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch workflow, quality gates, documentation rules, and release expectations.

## License

MIT. See [LICENSE](LICENSE).
