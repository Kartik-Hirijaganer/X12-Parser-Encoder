# Design System — Eligibility Workbench

> **This is the visual and frontend source of truth.** It merges the former `DESIGN.md` (visual spec) and `docs/frontend-standards.md` (frontend rules) into a single document.
>
> Inspired by **Meta (Store)** via [awesome-design-md](https://github.com/VoltAgent/awesome-design-md), adapted for a healthcare eligibility workbench serving non-technical users doing bulk Medicaid 270/271 workflows — and extended to cover 837I/837P/835 claim and remittance workflows.

**Related:**
- **Token values** live in [`apps/web/src/styles/tokens.css`](../apps/web/src/styles/tokens.css) (Tailwind v4 `@theme`). That file is authoritative for concrete hex values, radii, shadows, spacing, and motion timings. If a visual decision changes, **update the token first**, then update this document.
- **Component catalog** lives in [`docs/ui-components.md`](./ui-components.md) — API and usage for every primitive in [`apps/web/src/components/ui/`](../apps/web/src/components/ui/).
- **Reset / base styles** live in [`apps/web/src/styles/global.css`](../apps/web/src/styles/global.css).

---

## 1. Visual Theme & Atmosphere

The Eligibility Workbench is a task-driven healthcare tool — not a marketing site, not a dashboard for power users. The design is light-mode-first, rooted in Meta's retail-grade clarity: a generous white canvas where content, status, and actions are instantly legible. Every pixel serves the workflow. Non-technical users should feel confident, not overwhelmed.

The surface strategy is predominantly light — pure white for browsing and configuration, soft gray for secondary sections, and a controlled dark palette reserved exclusively for immersive data moments (raw X12 preview, code blocks). This is a tool people use once a week for 20 minutes; it must be self-evident every time they return.

The color system is built around a single action blue (`--color-action-500` — Meta Blue) that drives all CTAs, links, and interactive focus. Status is communicated through a disciplined four-color semantic system: green for active/success, red for inactive/error, amber for warnings/corrections, and slate for not-found/unknown. These status colors appear only in badges, stat cards, and table cells — never in chrome or navigation.

Typography uses the system's native sans-serif stack (Inter as the preferred render, with system-ui fallbacks) paired with JetBrains Mono for X12 segment previews and technical labels. The type scale is compact — this is a tool, not an editorial experience. Headlines stay at 28–36px, body at 16px, and captions at 13–14px. Weight 500 (Medium) dominates headings; 400 (Regular) handles body; 600 (Semibold) marks emphasis in tables and stat cards.

Buttons are pill-shaped, fully rounded, and unmistakable. Cards have generous 16–20px radius. The overall impression is clean, approachable, and medical-grade trustworthy — the visual equivalent of a well-organized clinic reception desk.

**Key characteristics:**

- Light-mode-first: white canvas with soft-gray sections.
- Single action blue for all interactive elements — no competing accent colors.
- Four-color semantic status system: green / red / amber / slate.
- Pill-shaped CTAs (fully rounded) — the primary call to action is always obvious.
- 8px spacing grid with 16px base rhythm.
- Cards at 16–20px radius — smooth, approachable, never sharp.
- System font stack with Inter preferred, JetBrains Mono for X12/code content.
- WCAG AA contrast compliance on all text — non-negotiable for healthcare.

---

## 2. Color Palette & Roles

> **Concrete hex values live in [`tokens.css`](../apps/web/src/styles/tokens.css).** This section describes **what each token is for** — when a new role is introduced, add the role here and the value in tokens.css. Do not duplicate hex values into this document.

### Primary action — one blue, one job

`--color-action-500` is the only interactive color in the system. It drives primary CTA backgrounds, active link text, focus rings, and selected states. Variants (`-600`, `-700` for hover/pressed, `-50` for tinted backgrounds, `-100` for subtle accents) are listed in tokens.css.

### Surface & background

Neutral surfaces go from pure white (page canvas and cards) through soft grays (secondary sections, warm card fill, web wash) to near black (reserved for code / X12 preview backgrounds only). A full-screen modal overlay tints the page at 50% opacity.

### Text & content

Five text roles: primary (main headings and body — warmer than black), secondary (descriptions, labels, help text), tertiary (placeholders, timestamps, metadata), disabled (inactive labels), and inverse (text on blue or dark backgrounds).

### Semantic status — used only in badges, stat cards, and table cells

| Role | Meaning | Use |
|---|---|---|
| Active / green | Active eligibility, pass, success | Badges, stat cards, row-level status |
| Inactive / red | Inactive eligibility, fail, denial, critical error | Badges, stat cards, row-level status, error banners |
| Warning / amber | Auto-correction applied, non-critical warning, partial match | Badges, banners, settings-gate warnings |
| Not-found / slate | Member not found, unknown status, no data | Badges, empty-state markers |

Each role has a 500 (foreground text) token, a 50 (background) token, and a 200 (border) token in tokens.css. **Status color never appears in chrome, buttons, or navigation.**

### Border & divider

Default borders on inputs, cards, and table rows; subtle borders for minimal separation; a strong variant for focused input strokes behind the focus ring; a divider tone for horizontal rules; and a semi-transparent focus ring (3px, action-blue at ~25% alpha).

### Gradients

A near-black `--color-surface-dark` → `--color-surface-dark-end` gradient for X12 raw preview backgrounds, and a soft-gray → wash gradient for drag-and-drop target areas.

---

## 3. Typography Rules

### Font families

- **Sans (UI):** Inter, with system-ui fallbacks. Variable: `--font-sans`.
- **Mono (code / X12):** JetBrains Mono, with SF Mono / Menlo fallbacks. Variable: `--font-mono`.

### Hierarchy

| Role | Size | Weight | Line height | Letter spacing | Use |
|------|------|--------|-------------|----------------|-----|
| Page Title | 36px | 500 | 1.22 | -0.5px | Page-level headings: "Eligibility Results", "Settings" |
| Section Title | 28px | 500 | 1.28 | -0.3px | Section headings |
| Card Title | 20px | 600 | 1.40 | -0.1px | Action card headers, stat card labels |
| Subtitle | 18px | 400 | 1.44 | normal | Descriptive text under headings |
| Body | 16px | 400 | 1.50 | normal | Standard body text, form descriptions, table cells |
| Body Medium | 16px | 500 | 1.50 | normal | Navigation links, emphasized body, field values |
| Label | 14px | 500 | 1.43 | -0.1px | Form labels, table headers, button text |
| Caption | 13px | 400 | 1.38 | normal | Help text, timestamps, secondary metadata |
| Small | 12px | 400 | 1.33 | normal | Footer text, version numbers, legal copy |
| Badge | 12px | 600 | 1.00 | 0.2px | Status badges (uppercase): "ACTIVE", "FAIL", "PASS" |
| Stat Value | 32px | 600 | 1.00 | -0.5px | Dashboard stat-card numbers |
| Mono Body | 14px | 400 | 1.57 | normal | X12 raw preview, segment content |
| Mono Caption | 12px | 400 | 1.33 | normal | Segment IDs, technical labels, SNIP codes |

### Principles

- **500 for headings, 400 for reading, 600 for data emphasis.** Three-tier weight system. Medium for authority without heaviness. Regular for comfortable reading. Semibold for at-a-glance scanning of numbers and table highlights.
- **Negative tracking only at display sizes.** Letter-spacing tightens at 28px+; below that, spacing stays normal for readability.
- **Uppercase only in badges.** Status pills use uppercase + weight 600. Nothing else is uppercased — this is a medical tool, not a marketing page.
- **Mono for X12 only.** JetBrains Mono appears exclusively in raw X12 previews, segment content, and technical labels. Never use it for general UI text.

---

## 4. Component Styling Rules

> For each primitive's implementation and prop API, see [`ui-components.md`](./ui-components.md). This section captures *visual rules* — how primitives should look, not how to call them.

### Buttons

- **Primary (pill).** Action-blue background, white text, no border, fully rounded (`--radius-pill`). Padding `10px 24px`, label weight 500. Hover darkens to `--color-action-600` with a subtle lift. Pressed uses `--color-action-700`. Focus ring 3px at 25% blue. **Use for:** Process, Download X12, Save Changes, Export.
- **Secondary (outlined pill).** Transparent background, primary-text label, 2px default border. Hover tints to soft gray and darkens the border. **Use for:** Cancel, Upload Another, Copy to Clipboard.
- **Ghost.** Transparent background, action-blue label, 8px radius. Hover fills with `--color-action-50`. **Use for:** View Details, inline links, navigation.
- **Quiet.** Tertiary tone, 8px radius, subtle hover. **Use for:** card-corner controls, dismiss actions.
- **Table.** No padding, left-aligned 13px uppercase label. **Use for:** sortable column headers.
- **Disabled (any variant).** Border-default background, disabled-text label, no hover. **Use for:** settings-gate blocking (e.g., "Generate 270" when submitter config is incomplete).

### Cards & containers

- **Content card (generic).** White, 1px default border, `--radius-xl` (16px), `--shadow-sm`. Padding 20px.
- **Action card (home page).** White, 1px default border, `--radius-2xl` (20px), `--shadow-md`. Hover translates up 2px and raises to `--shadow-lg`. 48px blue icon top-aligned; 20px/600 title; 14px/400 secondary description (max 3 lines); ghost button or file input at bottom.
- **Stat card (dashboard).** Uses the status 50-background and 200-border tokens. 16px radius, 20px padding. Stat value 32px/600 in the status 500 color; label 14px/500 in primary text. No shadow — color differentiation is sufficient.

### Inputs & forms

- White background, 1px default border, 8px radius (`--radius-md`), 10×14 padding, 16px body text.
- Label above at 14px/500 with 4px gap. Helper text 13px below at 4px gap.
- Text fields use the `Input` primitive; dropdowns use the `Select` primitive. Feature and page code should not render raw form controls directly.
- Focus: border switches to action-blue, 3px ring at 25% blue.
- Error: border in inactive-500, label and helper text in inactive-500.
- Disabled: warm-gray fill, disabled text.
- Select dropdowns reuse the same styling with a right-aligned chevron.
- **NPI validator:** green check icon inline on valid; red X + "Invalid NPI (Luhn check failed)" helper text on invalid.

### Badges & pills

- **Status badge.** 50-background + 500-foreground, pill radius, 2×10 padding, 12px/600 uppercase with 0.2px tracking. Variants: active, inactive, warning, notfound.
- **SNIP level badge.** Soft-gray background, slate text, 1px default border, 6px radius (`--radius-sm`), mono 12px/500. Shown as `SNIP 1`, `SNIP 2`, etc.

### Tables

- Header: warm-gray background, 13px/600 uppercase with 0.04em tracking, 2px default border-bottom.
- Rows: alternate white / `--color-row-alt`. 1px subtle border between rows.
- Cell padding: `12px 16px`, 14px body text.
- Hover tint: soft gray. Selected or expanded row: action-50 with a 3px action-blue left border.
- Expandable row: right-chevron icon; rotates 90° when expanded.

### Navigation

- White background, sticky top, 56px tall, 1px default border-bottom.
- Logo/title: 18px/600, left-aligned. Links: 14px/500 secondary. Active link: action-blue with a 2px bottom border. Collapses to a hamburger below 768px.

### File upload / drop zone

- Gradient background (`--color-surface-tertiary` → `--color-surface-wash`), 2px dashed border, 16px radius, 40px padding.
- Icon: 48px upload cloud, secondary-text color. Primary text 16px/500; secondary text 14px/400 lists accepted extensions.
- Hover / drag-over: background shifts to `--color-action-50`, border turns solid action-blue.

### Config status bar (home page)

- `--color-action-50` background, 1px action-100 border, 12px radius, 10×16 padding.
- 14px/500 content: `Provider: ACME HOME HEALTH | NPI: 1234567890 | DC Medicaid`. Entire bar is clickable → Settings.
- Missing-config variant: warning-50 background, warning-200 border, inline amber warning icon.

### Raw X12 preview (generate result)

- `--color-surface-dark` background, `--color-code-text` foreground.
- JetBrains Mono 14px/1.57. 12px radius, 20px padding. Max height 400px with scroll. Line numbers right-aligned in a 48px gutter.

### Toast / banner notifications

- **Info / auto-correction banner.** Warning-50 background, 4px warning-500 left border, 8px radius, info-circle icon. Dismissible via the `onDismiss` prop on the `Banner` primitive.
- **Error banner.** Inactive-50 background, 4px inactive-500 left border, inactive-500 text.
- **Settings-gate warning (inline on disabled action card).** 13px warning-500 text with a lock/warning-triangle icon: "Configure your provider details in Settings first."

---

## 5. Layout Principles

### Spacing system

Base unit: 8px. Tokens range from 2px (`space-1`) hairlines through 80px (`space-12`) maximum section separation. See [`tokens.css`](../apps/web/src/styles/tokens.css) for exact values. All spacing aligns to multiples of 4 or 8.

Typical applications:
- Label-to-input gap: 4px.
- Icon gaps / compact padding: 8px.
- Input and cell padding: 12px.
- Standard paragraph and card internal sections: 16px.
- Card padding: 20–24px.
- Section vertical padding: 40–64px.

### Grid & container

- Max container width: 1200px, centered.
- Page horizontal padding: 24px (mobile) / 32px (tablet) / 40px (desktop).
- Home page: 3-column card grid on desktop, 24px gap.
- Dashboard: full-width table, 16px cell padding.
- Settings: single-column form, max-width 640px, centered.
- Templates: 2-column card grid, 24px gap.

### Whitespace philosophy

This is a task-focused tool. Whitespace communicates hierarchy and breathing room, not luxury. Sections use 40–64px vertical padding — generous enough to feel uncluttered, compact enough to keep the workflow visible without scrolling. Action cards float in moderate negative space to feel approachable and tappable. The settings form is narrow (640px max) to keep field labels and inputs close together, reducing eye travel.

### Border radius scale

| Token | Use |
|---|---|
| `--radius-sm` (6px) | SNIP badges, small tags |
| `--radius-md` (8px) | Inputs, ghost buttons, small containers |
| `--radius-lg` (12px) | Config status bar, banners, X12 preview |
| `--radius-xl` (16px) | Content cards, stat cards, drop zone |
| `--radius-2xl` (20px) | Action cards (home page) |
| `--radius-pill` (100px) | Pill buttons, status badges (fully rounded) |

---

## 6. Depth & Elevation

| Level | Token | Use |
|---|---|---|
| Flat | — | Default state, table rows, form sections |
| Level 1 | `--shadow-sm` | Content cards, resting state |
| Level 2 | `--shadow-md` | Action cards, resting |
| Level 3 | `--shadow-lg` | Action card hover, dropdown menus |
| Level 4 | `--shadow-xl` | Modals, dialogs |
| Overlay | `rgba(0,0,0,0.5)` | Modal backdrop |

The Eligibility Workbench uses a flat elevation model. Most differentiation comes from background shifts (white → soft gray) and borders, not shadows. Shadows appear only on interactive cards (home page) and floating elements (modals, dropdowns). This keeps the interface grounded and utilitarian — appropriate for a healthcare tool where trust matters more than flair.

---

## 7. Do's and Don'ts

### Do

- Use pill-shaped buttons (`--radius-pill`) for all primary and secondary CTAs.
- Use `--color-action-500` exclusively for interactive elements — never decoratively.
- Use the four-color status system consistently: green=active/pass, red=inactive/fail, amber=warning, slate=unknown.
- Keep body copy brief and scannable — this is a task tool, not documentation.
- Use generous whitespace (40–64px section padding) to keep the interface breathable.
- Use uppercase only in status badges.
- Always show form validation errors inline, immediately below the field.
- Use JetBrains Mono exclusively for X12 content and technical labels.
- Ensure all text meets WCAG AA contrast (4.5:1 body, 3:1 large text).
- Show the Config Status Bar on every page so users always know their context.
- Use the disabled button state + inline warning for settings-gate enforcement.
- Maintain the 8px spacing grid — all spacing values should be multiples of 4 or 8.

### Don't

- Don't use sharp corners (< 6px radius) — the system is all smooth curves.
- Don't introduce additional accent colors beyond action-blue.
- Don't use shadows on flat content — shadows are reserved for interactive cards and floating elements.
- Don't place critical actions in hard-to-find locations.
- Don't use dark mode for any page except the X12 raw preview component.
- Don't use decorative icons or illustrations — icons are functional only.
- Don't use more than 2 levels of text hierarchy in a single card.
- Don't make the user guess file routing — the drop zone auto-detects and action cards have clear descriptions.
- Don't show raw SNIP codes without plain-English explanations alongside.
- Don't use toast notifications for important outcomes — use inline banners that persist until dismissed.
- Don't crowd the settings form — one field per row, generous vertical spacing, clear group headers.
- Don't write hex values, raw radii, or shadow values into components. **Always use tokens.** If a token doesn't exist yet, add it to `tokens.css` first.

---

## 8. Responsive Behavior

### Breakpoints

| Name | Width | Key changes |
|------|-------|-------------|
| Mobile | <768px | Single column, hamburger nav, page title shrinks to 28px, cards stack vertically, 24px page padding |
| Tablet | 768–1024px | 2-column card grid (home), compact nav, settings form at full width with 32px padding |
| Desktop | 1024–1280px | 3-column card grid (home), full horizontal nav, settings form at 640px centered, 40px page padding |
| Large Desktop | >1280px | Max-width container (1200px) centered, increased margins |

### Touch targets

- Minimum touch target: 44×44px (WCAG 2.1 AAA).
- Mobile button height: minimum 44px with 12px vertical padding.
- Nav hamburger: 48×48px touch area.
- Action cards: full card surface is tappable.
- Table rows: full row surface is tappable for expand.
- Drop zone: full area is tappable for file browser.

### Collapsing strategy

- **Navigation.** Horizontal links collapse to hamburger at 768px; logo and Settings CTA remain visible.
- **Action cards (home).** 3-column ≥1024px → 2-column at 768px → stacked single column below.
- **Stat cards (dashboard).** 4-column ≥1024px → 2×2 grid at 768px → horizontal scroll or 2×2 below.
- **Tables.** Horizontal scroll with sticky first column below 768px; key columns (Name, Status) always visible.
- **Settings form.** Single column at all sizes; max-width 640px on desktop.
- **Drop zone.** Maintains full width; reduces vertical padding on mobile (40 → 24px).
- **Page titles.** 36 → 28px below 768px.
- **Section padding.** 64 → 40 → 24px as viewport narrows.

### Image behavior

- No hero images — this is a tool, not a marketing site.
- File-type icons (Excel, X12, CSV): SVG, proportional scaling, crisp at all sizes.
- Status icons: inline SVG, 16–20px, color-matched to semantic status.

---

## 9. Frontend Composition Rules

> These were formerly in `docs/frontend-standards.md`. They describe **how React code must be composed** on top of the design system.

### Shared primitives

- Interactive controls must use [`Button`](../apps/web/src/components/ui/Button.tsx).
- Text fields must use [`Input`](../apps/web/src/components/ui/Input.tsx).
- Select dropdowns must use [`Select`](../apps/web/src/components/ui/Select.tsx).
- File inputs must use [`FileUpload`](../apps/web/src/components/ui/FileUpload.tsx).
- Tabular data must use [`Table`](../apps/web/src/components/ui/Table.tsx).
- Status indicators must use [`Badge`](../apps/web/src/components/ui/Badge.tsx).
- Page-level notifications must use [`Banner`](../apps/web/src/components/ui/Banner.tsx).

See [`ui-components.md`](./ui-components.md) for the full catalog and each primitive's API.

### Layering

- **Primitives** (`components/ui/`) are token-driven, headless, and free of domain logic.
- **Feature components** (`components/features/`) compose primitives with domain-aware behavior (e.g., `EligibilityDashboard`, `IssueTable`).
- **Pages** (`pages/`) own route orchestration and layout. Pages do not reimplement primitive markup.
- **Layout** (`components/layout/AppShell.tsx`) owns global chrome (nav, footer, container).

### Token discipline

- No inline hex values in TSX or CSS.
- No inline `style={}` except for truly dynamic values that cannot be expressed another way (e.g., a progress bar width).
- Promote colors, radii, shadows, spacing, and motion to tokens.css **first**, then reference the token variable from components.

### Workflow rules

- The home page supports three explicit actions plus drag-and-drop smart routing.
- Spreadsheet uploads route to the Generate preview and require configured settings first.
- X12 uploads route by detected `ST01`: `270` → Validate, `271` → Parse, `835` → Remittance parse, `837` → Claim validate.
- Corrections and partial-row failures must be visible in preview before generation.
- Validation issues must show plain-English messages and concrete suggestions.
- Parsed eligibility, claim, and remittance results stay in React state only. **Do not persist PHI to browser storage.**

### Storage boundary

- `localStorage` is reserved for submitter settings under `x12_submitter_config`.
- Do not write patient rows, parsed eligibility results, parsed remittances, raw X12, or uploaded filenames to client storage.
- Do not use `sessionStorage`, `IndexedDB`, or browser caches for workflow data.

### Development workflow

- [`apps/web/vite.config.ts`](../apps/web/vite.config.ts) proxies `/api` to `http://localhost:8000` by default.
- Override the proxy target with `VITE_API_PROXY_TARGET` when needed.
- Before closing frontend work, run: `npm run lint`, `npm run typecheck`, `npm run test -- --run`, `npm run build`.

---

## 10. Agent Quick Reference

### Token recall (roles, not values)

- Primary CTA → `--color-action-500`
- Backgrounds → `--color-surface-primary` (white), `--color-surface-secondary` (soft gray), `--color-surface-tertiary` (warm gray), `--color-surface-wash` (wash), `--color-surface-dark` (code)
- Text → `--color-text-primary` / `-secondary` / `-tertiary` / `-disabled` / `-inverse`
- Borders → `--color-border-default` / `-subtle` / `-strong`
- Status → `active` / `inactive` / `warning` / `notfound` families (each with `-500`, `-50`, `-200`)
- Radii → `--radius-sm` / `-md` / `-lg` / `-xl` / `-2xl` / `-pill`
- Shadows → `--shadow-sm` / `-md` / `-lg` / `-xl`
- Motion → `--duration-fast` / `-normal` / `-slow`, `--ease-out`

### Example component prompts

- "Create the Home Page with 3 action cards in a grid. Use the `Card` primitive with `variant='action'`. Each card: 48px blue icon at top, 20px/600 title, 14px/400 secondary description, ghost button at bottom. Below the cards, render `FileUpload` in `dropzone` variant."
- "Create the Eligibility Dashboard with 4 stat cards (one per status) and a `Table` primitive showing patient rows. Status cells use `Badge` with the matching variant."
- "Build the Settings page as a single-column form (max-width 640px centered). Group headers at 20px/600 with a subtle bottom border. Save button: `Button` with `variant='primary'`, bottom-right aligned."
- "Create the raw X12 preview: dark surface background via `--color-surface-dark`, 12px radius, 20px padding, max-height 400px with scroll. JetBrains Mono 14px via `--font-mono`."

### Iteration guide

1. Always use `--color-action-500` for interactive elements — no other blue variants in chrome.
2. Status colors appear only in badges, stat cards, and table status cells.
3. Three font weights: 400 / 500 / 600.
4. All spacing aligns to the 8px grid — if a value isn't a multiple of 4, question it.
5. Pill buttons for CTAs, 8px radius for inputs, 16–20px for cards.
6. When in doubt, Meta Store's retail clarity: simple, obvious, no visual noise.
7. X12/code content always uses mono on dark — never mix code styling into the light UI.
8. Every interactive element needs a visible focus state (3px action-blue ring).
9. **Read [`ui-components.md`](./ui-components.md) before adding new UI surface** — the primitive you need may already exist.

---

## 11. Change Log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-04-17 | Consolidated from former `DESIGN.md` (visual spec) and `docs/frontend-standards.md` (composition rules). Hex values and `@theme` block removed; `tokens.css` is now the sole source of truth for concrete values. Added Section 9 (composition rules) and Section 11 (change log). Added cross-link to `ui-components.md`. |
