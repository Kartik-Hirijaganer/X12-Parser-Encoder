# Eligibility Workbench Web

Phase 6 React UI for the X12 Eligibility Workbench.

Implemented frontend scope:

- Routed home, preview, generate-result, validation-result, dashboard, templates, and settings pages
- Lean design-system primitives for buttons, badges, tables, banners, cards, and file uploads
- Smart file routing for spreadsheet vs X12 input
- Local settings persistence with JSON import/export
- Tested workflow coverage with Vitest and Testing Library

## Commands

```bash
npm install
npm run dev
npm run lint
npm run typecheck
npm run test -- --run
npm run build
```

## Local API Integration

`vite.config.ts` proxies `/api` requests to `http://localhost:8000` by default so the frontend can call the FastAPI app during local development. Override that target with `VITE_API_PROXY_TARGET` if your backend runs elsewhere.
