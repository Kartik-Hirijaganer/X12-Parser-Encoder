---
name: Frontend UI
description: Write or modify React UI for apps/web while honoring the design system, token contract, and primitive-first rule
---

## Frontend UI

Use this skill any time you are about to add or change UI in `apps/web/`. The goal is to keep the design system coherent and prevent token drift, ad-hoc markup, and PHI leaks into browser storage.

### Read before writing

1. `docs/design-system.md` — visual theme, color roles, typography, depth, composition rules, storage boundary.
2. `docs/ui-components.md` — primitive catalog with import paths, variants, props, and usage snippets for `Button`, `Card`, `Badge`, `Banner`, `FileUpload`, `Spinner`, `Table`, `Icons`.
3. `apps/web/src/styles/tokens.css` — authoritative hex values, radii, shadows, fonts, motion. This is the only file that defines concrete values.

Skip these reads only if you have just read them in the current session.

### Hard rules

1. **No hardcoded values.** No hex codes in `.tsx`. No `bg-[#...]` or `p-[13px]` arbitrary Tailwind. If the token you need doesn't exist, add it to `tokens.css` first, then use it.
2. **Primitive-first.** Always use `Button`, `Table`, `FileUpload`, `Card`, `Badge`, `Banner`, `Spinner`, `Icons` from `apps/web/src/ui/`. Do not hand-roll raw `<button>`, `<table>`, `<input type="file">`, or ad-hoc badge/banner/card markup.
3. **Variants, not new components.** If a primitive almost fits, extend its variants rather than creating a parallel component. A new primitive is justified only when ≥2 call sites need it.
4. **No `style={{ ... }}`** except for truly dynamic values (computed widths, positions). All static styling goes through tokens + Tailwind classes.
5. **Storage boundary.** Never write patient data to `localStorage`, `sessionStorage`, or `IndexedDB`. The only sanctioned key is `x12_submitter_config` for non-PHI submitter configuration.
6. **Feature components compose primitives; pages compose features.** Pages should contain layout and routing, not UI logic.

### When you add or change a visual pattern

Land all four of these in the same change:

- `apps/web/src/ui/<Primitive>.tsx` — implementation (new variant, new prop, or new primitive).
- `apps/web/src/styles/tokens.css` — only if a new token is needed.
- `docs/design-system.md` — describe the role / rule in prose. Never restate hex values here.
- `docs/ui-components.md` — update the primitive's row in the index table and its detailed section (variants, props, usage snippets).
- Extend the primitive's test (`apps/web/src/ui/__tests__/<Primitive>.test.tsx`).

### Workflow

1. Locate the primitive you need in `docs/ui-components.md`. If it exists, use it with an existing variant.
2. If no existing variant fits, decide whether to extend variants on the existing primitive or (rarely) introduce a new primitive. Document the decision in the commit message.
3. Implement the change and update the triplet above.
4. Run `cd apps/web && npm run lint && npm run test` before handing the change back.

### Token Efficiency Rules

- Prefer opening `docs/ui-components.md` over reading every `.tsx` in `apps/web/src/ui/` — the catalog is the index.
- Use `semantic_search_nodes` from `code-review-graph` to find existing callers of a primitive before adding a new variant; that's cheaper than Grep.
- Target: any UI change completes in ≤8 tool calls with no `<button>`, hex value, or new top-level component introduced without justification.
