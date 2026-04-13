# Architecture

## Overview

This repository ships three deliverables behind one versioned release train:

- `x12-edi-tools`: the Python library for typed models, parser, encoder, validator, and payer profiles.
- `apps/api`: the FastAPI layer for browser and agent-friendly workflows.
- `apps/web`: the React workbench for spreadsheet import, generation preview, validation, and 271 dashboards.

## Core Flow

1. The browser uploads a spreadsheet or X12 file to the API.
2. Middleware assigns or propagates `X-Correlation-ID`, enforces request limits, and records request metrics.
3. Services normalize spreadsheet rows, call library parse or encode or validate functions with the correlation ID, and emit workload metrics such as row counts or segment counts.
4. The response is returned without retaining uploaded content on disk.

## Library Boundaries

- Parser output is `ParseResult`, never a bare interchange. This keeps transaction-scoped recovery and warnings available to callers.
- Encoder preserves delimiter choices and control numbers for single-interchange roundtrips unless explicit regeneration is requested.
- Validator layers generic SNIP checks with payer-profile rules.

## API Boundaries

- Uploads are read into memory, size checked, hashed for sanitized audit metadata, and never logged by filename.
- `/metrics` exposes Prometheus histograms and counters for request latency, errors, upload sizes, record counts, segment counts, and concurrent requests.
- `/api/v1/health` verifies library import, parser smoke behavior, payer profile registry, and metrics registry availability.

## Browser Boundaries

- `localStorage` is reserved for submitter configuration only.
- Patient rows, generated X12, filenames, and parsed eligibility results remain in React state and are discarded on navigation or tab close.
- `sessionStorage`, `IndexedDB`, and browser caches are intentionally unused for workflow data.

## Release Discipline

- `VERSION` is the repo-wide source of truth.
- `scripts/bump_version.py` updates release-bearing files and the changelog.
- `scripts/check_version_sync.py` and `scripts/check_no_proprietary_content.py` back CI gates.
- GitHub Actions cover linting, type checking, coverage thresholds, secret scanning, build publishing, and deploy automation.
