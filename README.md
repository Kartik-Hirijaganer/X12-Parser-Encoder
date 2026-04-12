# X12-Parser-Encoder

Monorepo scaffold for a Python-native X12 270/271 library and a companion eligibility workbench.

## Phase 0 Status

- `packages/x12-edi-tools`: installable library skeleton with typed configuration models
- `apps/api`: FastAPI scaffold with PHI-safe middleware boundaries and smoke tests
- `apps/web`: Vite React TypeScript scaffold with Tailwind CSS v4 wiring
- `metadata/`: local-only reference content, ignored from source control

## Quick Start

```bash
make install
make lint
make test
```
