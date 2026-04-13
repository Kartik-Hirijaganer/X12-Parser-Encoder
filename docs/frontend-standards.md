# Frontend Standards

Phase 6 frontend rules for `apps/web`.

## Design System

- `DESIGN.md` is the visual source of truth.
- `apps/web/src/styles/tokens.css` is the token implementation. If a visual decision changes, update the token first.
- No inline hex values. Promote colors, radii, shadows, spacing, and motion to tokens.
- No inline `style={}` except for truly dynamic values that cannot be expressed another way.

## Composition

- Shared interactive controls must use `apps/web/src/components/ui/Button.tsx`.
- Shared file inputs must use `apps/web/src/components/ui/FileUpload.tsx`.
- Shared tabular data must use `apps/web/src/components/ui/Table.tsx`.
- Feature components compose UI primitives.
- Pages own layout and route orchestration, not repeated primitive markup.

## Workflow Rules

- The home page supports three explicit actions plus drag-and-drop smart routing.
- Spreadsheet uploads route to the Generate preview and require configured settings first.
- X12 uploads route by detected `ST01`: `270` -> Validate, `271` -> Parse.
- Corrections and partial-row failures must be visible in preview before generation.
- Validation issues must show plain-English messages and concrete suggestions.
- Parsed eligibility results stay in React state only. Do not persist PHI to browser storage.

## Storage Boundary

- `localStorage` is reserved for submitter settings under `x12_submitter_config`.
- Do not write patient rows, parsed eligibility results, raw X12, or uploaded filenames to client storage.
- Do not use `sessionStorage`, `IndexedDB`, or browser caches for workflow data.

## Development

- `apps/web/vite.config.ts` proxies `/api` to `http://localhost:8000` by default.
- Override the proxy target with `VITE_API_PROXY_TARGET` when needed.
- Use `npm run lint`, `npm run typecheck`, `npm run test -- --run`, and `npm run build` before closing frontend work.
