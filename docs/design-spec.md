# Design Spec - Eligibility Workbench

This is the single entry point for frontend design work. It condenses the visual rules from [`docs/design-system.md`](design-system.md) and the primitive APIs from [`docs/ui-components.md`](ui-components.md). Those documents remain detailed appendices; this file is the contract agents must read first.

## 1. Agent Contract

1. Read `docs/design-spec.md` before any UI change.
2. Never hardcode hex, px, or ms values in UI code. Use `apps/web/src/styles/tokens.css` tokens.
3. Never hand-roll `<button>`, `<input type="file">`, or `<table>` in page or feature code. Use primitives.
4. Every new visual pattern is a triplet PR: spec, primitive, and test.
5. Running `make design-lint` must pass locally before commit.

The design lint rules enforce the hard parts of this contract. When a rule fires, fix the code or promote the missing value into `tokens.css` before using it.

## 2. Source Order

When files disagree, use this order:

1. `apps/web/src/styles/tokens.css` wins for concrete values: colors, spacing, radii, shadows, type tokens, and motion timings.
2. `docs/design-spec.md` wins for rules and allowed patterns.
3. `docs/design-system.md` gives expanded rationale and visual examples.
4. `docs/ui-components.md` gives primitive prop APIs and usage details.

## 3. Visual Theme

Eligibility Workbench is a task-driven healthcare tool for bulk Medicaid eligibility, claim, and remittance workflows. It should feel quiet, legible, and operational. The interface is light-mode-first with a white canvas, soft secondary surfaces, clear status treatment, and a restrained action color.

The visual language is based on retail-grade clarity rather than enterprise density. Users should immediately understand where to upload, what is configured, what failed, and what to do next. Decorative visuals are not part of the system; icons are functional.

### Color Roles

Concrete values live only in `tokens.css`.

| Role | Token family | Use |
|---|---|---|
| Action | `--color-action-*` | Primary CTAs, links, focus rings, selected states |
| Surface | `--color-surface-*` | Page canvas, cards, secondary panels, code preview |
| Text | `--color-text-*` | Primary, secondary, tertiary, disabled, inverse text |
| Active | `--color-active-*` | Success, active eligibility, pass states |
| Inactive | `--color-inactive-*` | Errors, failures, inactive eligibility |
| Warning | `--color-warning-*` | Corrections, warnings, partial matches |
| Not found | `--color-notfound-*` | Unknown, no data, member not found |
| Border | `--color-border-*`, `--color-divider` | Form controls, cards, table structure |

Status color appears only in badges, stat cards, banners, and table status cells. It is not used for navigation or decorative emphasis.

### Typography

Use the system sans stack through `--font-sans`. Use `--font-mono` only for raw X12, segment content, control numbers, and technical labels.

| Role | Intended size | Weight | Use |
|---|---:|---:|---|
| Page title | 36px | 500 | Route headings |
| Section title | 28px | 500 | Major page sections |
| Card title | 20px | 600 | Cards and grouped panels |
| Subtitle | 18px | 400 | Support copy below headings |
| Body | 16px | 400 | Normal reading text |
| Label | 14px | 500 | Form labels, table headers, buttons |
| Caption | 13px | 400 | Metadata and secondary details |
| Small | 12px | 400 | Footer and compact metadata |
| Badge | 12px | 600 | Uppercase status labels |
| Stat value | 32px | 600 | Dashboard totals |
| Mono body | 14px | 400 | X12 preview |

Use three weights: 400 for reading, 500 for headings and labels, 600 for data emphasis. Uppercase is reserved for badges and table headers.

### Spacing

Spacing follows a 4px token scale exposed as `--space-1` through `--space-12` in `tokens.css`.

| Token | Value | Common use |
|---|---:|---|
| `--space-1` | 4px | Label gaps, tiny offsets |
| `--space-2` | 8px | Icon gaps, compact padding |
| `--space-3` | 12px | Input and cell padding |
| `--space-4` | 16px | Standard content gap |
| `--space-5` | 20px | Card internals |
| `--space-6` | 24px | Page and card gaps |
| `--space-8` | 32px | Dense section spacing |
| `--space-10` | 40px | Page vertical rhythm |
| `--space-12` | 48px | Large section separation |

Use existing Tailwind scale classes when they map to the token scale. Use `[...]` arbitrary values only when the value is a token reference such as `p-[var(--space-5)]`.

### Radius, Shadow, Motion

Radii are tokens: `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-xl`, `--radius-2xl`, `--radius-pill`. Inputs use `--radius-md`, banners and code previews use `--radius-lg`, cards use `--radius-xl` or `--radius-2xl`, and primary/secondary CTAs use `--radius-pill`.

Shadows are tokens: `--shadow-sm`, `--shadow-md`, `--shadow-lg`, `--shadow-xl`. Shadows are reserved for cards and floating elements, not table rows or flat content.

Motion timings are tokens: `--duration-fast`, `--duration-normal`, `--duration-slow`, and `--ease-out`. Inline `transition:` and `animation:` declarations are not allowed. Use token-backed classes or shared motion primitives.

**Route transitions** use `components/transitions/RouteTransition.tsx`, which wraps the router outlet in Framer Motion's `<AnimatePresence mode="wait">` and animates a 200 ms opacity + 6 px Y-axis fade+slide keyed on `useLocation().pathname`.

**Reduced motion is mandatory.** Every Framer Motion component, keyframe animation, toast entry, modal/drawer slide, skeleton pulse, and drop-zone pulse must branch on `hooks/useReducedMotionPreference.ts`. When the user's OS preference is `prefers-reduced-motion: reduce`, transitions become instant, entrance animations are skipped, and pulses are disabled. This is accessibility, not polish — audit every `motion.*` component for it. At least one primitive test must exercise the reduced-motion branch to prove the wiring is live (see `apps/web/src/__tests__/reduced-motion.test.tsx`).

## 4. Toast Policy

The old rule that banned toast notifications for important outcomes still stands for actionable failures. The amended policy is:

- Toasts are allowed for transient success confirmations and low-urgency information.
- Banners are mandatory for errors the user must act on.
- A 5xx or timeout may show a toast for awareness, but any retry path or corrective instruction still belongs in a banner or inline field error.
- Toast copy must never contain raw X12, filenames, member IDs, names, or other sensitive values.
- Feature code must call the sanctioned `toast` variants (`toast.success`, `toast.info`, `toast.warning`, `toast.error`) exported from `components/ui/Toast`. Do not import `sonner` directly — this keeps variants, styling, and copy policy enforceable.
- Mount exactly one `<Toaster />` from `components/ui/Toast` at the application root (`App.tsx`).

## 5. Primitive Catalog

Shared primitives live in `apps/web/src/components/ui/`. Page and feature code must compose them rather than reimplementing native controls.

| Primitive | File | Required for |
|---|---|---|
| `Button` | `Button.tsx` | Buttons, links styled as buttons, icon controls |
| `Input` | `Input.tsx` | Text, search, numeric, and scalar fields |
| `Select` | `Select.tsx` | Native select controls |
| `Card` | `Card.tsx` | Reusable content and action surfaces |
| `Badge` | `Badge.tsx` | Compact status indicators |
| `Banner` | `Banner.tsx` | Inline status, warning, and error messages |
| `FileUpload` | `FileUpload.tsx` | File browse and drop-zone interactions |
| `Spinner` | `Spinner.tsx` | Indeterminate loading indicators |
| `Table` | `Table.tsx` | Tabular data, sorting, pagination, expandable rows |
| `Icons` | `Icons.tsx` | Functional icon set using `currentColor` |
| `Toast` | `Toast.tsx` | Transient success / info / warning / error announcements (wraps `sonner`) |
| `Modal` | `Modal.tsx` | Centered focus-trapped dialogs with ESC/overlay dismiss (Radix Dialog) |
| `Drawer` | `Drawer.tsx` | Side-sheet dialogs sliding in from left or right (Radix Dialog) |
| `Tooltip` | `Tooltip.tsx` | Hover/focus descriptive tips with `--duration-slow` open delay (Radix Tooltip) |
| `Skeleton` | `Skeleton.tsx` | Pulsing placeholder surface for content that is being loaded |
| `ProgressBar` | `ProgressBar.tsx` | Determinate and indeterminate progress indicators |
| `EmptyState` | `EmptyState.tsx` | Shared empty-view composition (icon + title + copy + optional CTA) |
| `ErrorBoundary` | `ErrorBoundary.tsx` | React error boundary wrapping routes; renders an `EmptyState` fallback |
| `ConfirmationDialog` | `ConfirmationDialog.tsx` | Opinionated confirm/cancel dialog composed over `Modal` with `destructive` flag |

See `docs/ui-components.md` for prop APIs and usage snippets.

### Composition Rules

- `components/ui/` primitives own native markup, styling, focus states, and accessibility defaults.
- `components/features/` may combine primitives with domain behavior.
- `pages/` own route orchestration and layout only.
- `components/layout/` owns global chrome.

Feature and page code must not render raw `<button>`, `<input type="file">`, or `<table>`. Those elements are legal inside primitives.

### Pattern Changes

Any new visual pattern requires:

1. Update this file with the rule or role.
2. Update or add the primitive in `components/ui/`.
3. Add or extend a test under `apps/web/src/__tests__/`.

If the pattern needs a new color, spacing, radius, shadow, font, or motion value, add the token first.

## 6. Page Rules

### Home

The home page presents three action cards plus a smart drop zone. Action cards use `Card` with `variant="action"` and functional icons. The drop zone uses `FileUpload`.

### Preview

Spreadsheet preview must show corrections and excluded rows before generation. Processing states use `Spinner` until Phase 7 adds `ProgressBar` and `Skeleton`.

### Generate Result

Raw X12 preview uses the dark surface tokens and mono type. Copy/download controls use `Button`.

### Validation Result

Validation failures use `Banner` plus issue tables. Plain-English messages and concrete suggestions are required alongside any SNIP codes.

### Dashboard

Status summaries use semantic status tokens. Dashboard tables use the `Table` primitive and `Badge` status cells.

### Settings

Settings stay single-column with clear group headings. The only allowed browser storage for settings is `x12_submitter_config`, and it must not contain PHI.

## 7. Safety

Do not persist raw X12, uploaded filenames, names, member identifiers, parsed eligibility rows, claim data, or remittance data in browser storage. Workflow data stays in React state and API responses only.

Do not log or display sensitive payload values in diagnostic UI. Error and toast text must be operational and sanitized.

## 8. Lint Rules

The local `design-system` ESLint plugin enforces:

- `design-system/no-raw-color`: no raw hex values in JSX class names or style objects.
- `design-system/no-arbitrary-tw`: no non-token Tailwind arbitrary values for colors, spacing, sizing, radii, or motion-sensitive values.
- `design-system/primitive-required`: no raw buttons, file inputs, or tables in `components/features/**` or `pages/**`.
- `design-system/no-inline-animation`: no inline `transition` or `animation` style declarations.

Run `make design-lint` before committing frontend work.
