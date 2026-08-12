# UI Revamp Plan — Eligibility Workbench (Complete Visual Overhaul)

|  |  |
|---|---|
| **Status** | Draft, ready for design execution |
| **Date** | 2026-05-30 |
| **Scope** | `apps/web/src/**` — every routed screen, the app shell, and shared UI patterns |
| **Theme** | Keep the existing design system (Meta Store layout philosophy + Mastercard-inspired warm-orange accent). **Elevate the execution, do not replace the theme.** |
| **Audience** | A design-focused Claude agent generating React + Tailwind v4 screens against this repo's primitives |
| **Non-negotiables** | `tokens.css` is the only source of concrete values · primitive-first · stateless · no PHI in browser storage · WCAG AA · reduced-motion honored |

---

## 0. How to use this document

You are revamping the **visual design and screen composition** of an existing, fully-functional healthcare tool. The data, routes, and workflows are correct — they look flat and unfinished. Your job is to make every screen feel like a confident, calm, operational SaaS product **without changing the feature set, the theme, or the token system.**

**Read order before you touch a screen:**
1. This document, top to bottom.
2. [`docs/design-spec.md`](../design-spec.md) — the enforceable design contract.
3. [`apps/web/src/styles/tokens.css`](../../apps/web/src/styles/tokens.css) — the only place concrete values live.
4. [`docs/ui-components.md`](../ui-components.md) — primitive prop APIs.

**Hard rules (the design lint enforces these — violating them fails CI):**
- Never hardcode hex / px / ms. Reference tokens (`var(--…)` or token-backed Tailwind like `bg-[var(--color-action-500)]`). If you need a value that doesn't exist, **add a named token to `tokens.css` first**, then use it.
- Never hand-roll `<button>`, `<input type="file">`, or `<table>` in `pages/**` or `components/features/**`. Compose the primitives in `components/ui/`.
- No inline `transition:`/`animation:` — use token-backed classes or the shared motion helpers.
- Every **new** visual pattern is a triplet: update `docs/design-spec.md`, add/extend the primitive in `components/ui/`, add/extend a test in `apps/web/src/__tests__/`. If it needs a new value, add the token in the same change.
- Every animation branches on `hooks/useReducedMotionPreference.ts`.
- Copy never contains raw X12, filenames, member IDs, names, or other PHI. Operational, sanitized language only.

**In scope:** layout, hierarchy, surfaces, spacing rhythm, component polish, states (loading/empty/error/success), motion, the app shell, and ~9 new/upgraded shared patterns (§5).
**Out of scope:** API shapes, route structure, business logic, the four-color status semantics, adding new accent colors, dark mode (except the code-preview surface), databases/persistence.

---

## 1. Why we're revamping — honest critique of the current UI

Every current screen is `AppShell → <div className="space-y-6"> → <Card><Card><Card>`. That single pattern is the root of the "ugly" feeling. Concretely:

1. **Monotonous box-stacking.** Same radius (`--radius-xl`), same 1px border, same pale cream fill (`--color-surface-primary`), same faint `--shadow-sm`, stacked top to bottom. No size, weight, or surface contrast between cards. The eye finds no anchor — it reads as "a list of identical boxes."
2. **Timid page header.** Title is `clamp(1.75rem, 4vw, 2.25rem)` at weight 500 with a long gray subtitle paragraph. No eyebrow, no breadcrumb, no actions aligned to it, no separation from the body.
3. **Banner pile-up.** Corrections, excluded-row, timeout, and member-ID notices all render full-width at the top of Preview/Result and shove the real content down. A file with several corrections becomes a wall of amber before you see anything useful.
4. **Bland metric cards.** Preview/Generate/Validation summary tiles are "uppercase micro-label + big number" in gray-on-cream — no icon, no semantic color, no context. Forgettable.
5. **Underused palette.** The warm orange shows up only on buttons and one nav underline. Secondary/tertiary/wash surfaces and the dark surface exist as tokens but are barely used, so the whole app reads as flat grayish-cream rather than *warm* and layered.
6. **Tables feel raw.** The `Table` primitive works, but sections wrap it with ad-hoc headings and inconsistent toolbars; pagination and empty states feel bolted on.
7. **The workflow is invisible.** The product is a clear pipeline — **Upload → Preview → Process → Result** — but nothing shows "where am I / what's next." Preview and the result pages float context-free.
8. **The config status bar is visually heavy.** A full-width button repeated under every page title, competing with the title for attention.
9. **Inconsistent rhythm.** `p-6` cards next to `p-5` tiles; gaps vary screen to screen; Settings is a 2-col grid while everything else is one column. No applied spatial system.
10. **Thin states.** Loading = a few gray skeleton bars; empty = a dashed box; the footer is an afterthought (`Eligibility workbench / v1.2.0`).

**None of this is a theme problem.** The tokens are good. It's a *composition and hierarchy* problem. This plan fixes composition.

---

## 2. North star — the elevated direction

> **Calm, confident, operational.** A warm, legible clinic-desk tool that a non-technical biller uses once a week and instantly re-understands. Retail-grade clarity (Meta Store DNA) with one warm accent (Mastercard orange) and disciplined status color.

Seven moves carry the entire revamp:

1. **Layered surfaces create figure-ground.** The page sits on the warm wash (`--color-surface-wash`); foreground cards sit on `--color-surface-primary` with a real edge. Group/secondary regions use `--color-surface-secondary`. Stop painting everything one color.
2. **One canonical `PageHeader`.** Eyebrow + title + supporting line + right-aligned action cluster + (on pipeline screens) a slim stepper. Replaces the timid `AppShell` title block everywhere.
3. **Express the pipeline.** A `Stepper` on Upload → Preview → Result so the operator always knows where they are and what's next.
4. **Metric tiles, not labels.** Upgrade every summary number into a `StatTile`: icon chip + value + label + optional context line, with semantic tone where it carries meaning (status) and neutral tone where it doesn't (counts).
5. **Tame notices.** Replace stacked banners with a single consolidated `NoticeStack` (counted, collapsible) and a compact `ResultHero` for pass/fail outcomes. Banners remain mandatory only for actionable errors.
6. **Tables get a shell.** A consistent `Toolbar` (title + search + filters + primary action), refined zebra + sticky header, and first-class empty/loading.
7. **Intentional warmth + motion.** Use orange for the primary path, focus, and selection only. Add restrained hover lifts, route transitions (already wired), and a warm-wash page gradient. Never decorative color.

**Visual intensity:** bold revamp, not a tweak — strong hierarchy, richer surfaces, confident type — but strictly inside the existing token + primitive system. No new accent hues.

---

## 3. Design system foundation (the contract you build against)

All values below already exist in [`tokens.css`](../../apps/web/src/styles/tokens.css). Reproduced here so you don't have to leave the doc. **Do not hardcode these numbers — reference the variable.**

### 3.1 Color tokens

```
Action (the ONLY interactive color)
  --color-action-500 #ff5f00   600 #e35200   700 #bf4200   100 #ffd8bd   50 #fff2e8
Surfaces (light, warm; dark reserved for code)
  --color-surface-primary  #fffbf5   secondary #f7efe4   tertiary #fff6ec
  --color-surface-subtle (=tertiary)  wash #f4eadc   dark #1c1e21   dark-end #111314
Text
  --color-text-primary #1c2b33   secondary #5d6c7b   tertiary #65676b   disabled #bcc0c4   inverse #fff
Status (badges / stat tiles / banners / table status cells ONLY)
  active(green)  500 #007d1e  50 #ecfdf3  200 #a6f4c5
  inactive(red)  500 #eb001b  50 #fff1f2  200 #fecaca
  warning(amber) 500 #b45309  50 #fffbeb  200 #fde68a
  notfound(slate)500 #475569  50 #f1f5f9  200 #cbd5e1
Structure
  border-default #e8d7c6  border-subtle #f0e1d2  border-strong #9c7c63  divider #d8c4b0
  row-alt #fff8f0  focus-ring rgba(255,95,0,.28)  code-text #e2e8f0  required-asterisk #eb001b
```

### 3.2 Typography (`--font-sans` Inter · `--font-mono` JetBrains Mono)

Three weights only: **400** reading · **500** headings & labels · **600** data emphasis. Negative tracking only ≥28px. Uppercase only in badges and table headers. Mono only for X12/segment/control-number/code content.

| Role | Size / Wt / LH | Use |
|---|---|---|
| Page title | 36 / 500 / 1.22 | `PageHeader` title |
| Section title | 28 / 500 / 1.28 | major sections |
| Card title | 20 / 600 / 1.40 | card & panel headers |
| Subtitle | 18 / 400 / 1.44 | support copy under titles |
| Body | 16 / 400 / 1.50 | reading text, cells |
| Label | 14 / 500 / 1.43 | form labels, buttons, table headers |
| Caption | 13 / 400 / 1.38 | metadata, helper text |
| Badge | 12 / 600 / 1.0 (UPPER, 0.2px) | status pills |
| Stat value | 32 / 600 / 1.0 | metric tiles |
| Mono body | 14 / 400 / 1.57 | X12 preview |

### 3.3 Spacing · radius · shadow · motion

- **Spacing:** 4px grid, `--space-1`(4) … `--space-12`(48). Card padding `--space-6`(24). Section gaps `--space-6`/`--space-8`. Page rhythm `--space-10`(40).
- **Radius:** inputs/ghost `--radius-md`(8) · banners/code/toolbars `--radius-lg`(12) · cards `--radius-xl`(20) · action cards `--radius-2xl`(24) · buttons & badges `--radius-pill`.
- **Shadow:** `--shadow-sm` resting cards · `--shadow-md` action cards · `--shadow-lg` hover/dropdowns · `--shadow-xl` modals. **Shadows only on interactive/floating surfaces — never on flat content or table rows.**
- **Motion:** `--duration-fast/normal/slow/route`, `--ease-out`, `--motion-lift-sm/-md`, `--motion-route-slide`. Route transitions already live in `components/transitions/RouteTransition.tsx`. Every motion branch must respect reduced-motion.

### 3.4 Existing primitive catalog (compose these — don't reinvent)

`Button` (primary/secondary/ghost/quiet/table · sm/md/icon) · `Input` · `Select` · `Card` (content/action) · `Badge` (active/inactive/warning/notfound/snip) · `Banner` · `FileUpload` (dropzone/button) · `Spinner` · `Table` (sort/paginate/expand/empty) · `Icons` (currentColor) · `Toast` · `Modal` · `Drawer` · `Tooltip` · `Skeleton` · `ProgressBar` · `EmptyState` · `ErrorBoundary` · `ConfirmationDialog` · `UnsavedChangesBar`.

### 3.5 New tokens this revamp introduces

Add to `tokens.css` (named, then referenced):

```css
/* Layout */
--layout-sidebar-w: 0px;                 /* reserved; top-nav model keeps this 0 */
--layout-header-h: 64px;                 /* was an ad-hoc 56–72; standardize */
--layout-page-pad-x: var(--space-6);     /* 24 mobile */ /* lg overrides to --space-10 */
--layout-section-gap: var(--space-8);    /* 32: gap between major page sections */

/* Elevation accents for the revamp */
--surface-card-hover: var(--color-surface-tertiary);
--accent-tile-bar: var(--color-action-500);   /* top accent on primary metric tile */
--gradient-page: linear-gradient(180deg, var(--color-surface-primary) 0%, var(--color-surface-wash) 100%);
--gradient-hero: linear-gradient(135deg, var(--color-action-50) 0%, var(--color-surface-tertiary) 100%);
--gradient-code: linear-gradient(to bottom, var(--color-surface-dark), var(--color-surface-dark-end));

/* Stepper */
--stepper-dot: 28px;
--stepper-line: var(--color-divider);
--stepper-line-done: var(--color-action-500);
```

> The page background already uses a warm gradient + a faint blue radial in `global.css`. **Remove the blue radial** (`rgba(0,100,224,0.08)` — a leftover from the Meta-blue origin that muddies the warm canvas) and replace with `--gradient-page`, optionally a faint warm orange radial at top-right using `--color-action-50` at ~6% if more warmth is wanted.

---

## 4. Global chrome

### 4.1 App shell — `components/layout/AppShell.tsx`

**Decision: keep a top-nav model** (it's a focused, once-a-week tool — a left rail would over-weight it). A left-rail variant is documented as an alternative at the end of this section but is **not** the default build.

```
┌──────────────────────────────────────────────────────────────────────┐
│ HEADER  (sticky, 64px, surface-primary/95 + backdrop blur, 1px border) │
│  [◆ brand mark]  Eligibility Workbench        Home  Templates  Settings │
│                                               [⚙ config chip ▸]         │
├──────────────────────────────────────────────────────────────────────┤
│  PAGE HEADER (see §5.1)                                                 │
│    eyebrow · Title 36/500 · supporting line · [actions →]              │
│    [ Stepper on pipeline screens ]                                      │
│                                                                         │
│  PAGE BODY  (max 1200px, gap = --layout-section-gap)                    │
│    … screen sections …                                                  │
│                                                                         │
├──────────────────────────────────────────────────────────────────────┤
│ FOOTER  (surface-primary, 1px top border)                              │
│  Eligibility Workbench · stateless, no data retained   ·   v{VERSION}  │
└──────────────────────────────────────────────────────────────────────┘
```

Changes from today:
- **Brand mark.** Add a small functional logo mark (orange rounded square with a document/shield glyph from `Icons`) left of the wordmark. 18px/600 wordmark.
- **Nav as a real nav.** Add an explicit **Home** link (always visible, not just an icon that appears off-route). Active link: action-orange text + 2px orange bottom border (keep). Inactive: `--color-text-secondary`, hover `--color-action-50` tint.
- **Config status becomes a compact chip** in the header (not a full-width bar). See §4.2.
- **Page background** uses `--gradient-page` (warm), blue radial removed.
- **Footer** gains a one-line reassurance ("stateless · no patient data retained") — reinforces the safety story.

`AppShell` props evolve to delegate the header block to `PageHeader` (§5.1): `AppShell` renders chrome + `<main>` container; pages render a `<PageHeader …/>` as their first child. Keep `title`/`subtitle` working via a thin compatibility shim during migration, then remove.

### 4.2 Config status — from full-width bar to header chip + contextual banner

The current `ConfigStatusBar` (a giant full-width quiet button under every title) becomes:
- **Header chip** (always visible, compact): a pill in the top bar showing readiness at a glance.
  - Ready: `--color-action-50` bg, `--color-action-100` border, orange dot, label `Ready · Next ICN 000123457`. Click → `/settings`.
  - Not ready: `--color-warning-50` bg, `--color-warning-200` border, `WarningIcon`, label `Setup needed`. Click → `/settings`.
- **Contextual banner** only where it blocks an action (Home "Generate" card, Preview generate flow) — not on every page. Keeps the warning where the user can act on it.

Keep the exact readiness logic from `useSettings` (`hasRequiredSettings`, `hasUsableIcn`, ICN-exhausted at `999999999`) and the messages — only the *presentation* changes.

---

## 5. Shared revamp patterns (build these first)

These are the reusable building blocks every screen composes. Build and test them before the screens. Each is a triplet (spec note here + primitive + test).

### 5.1 `PageHeader` — `components/layout/PageHeader.tsx`
The single titling pattern. Props: `eyebrow?`, `title`, `supporting?`, `actions?` (ReactNode, right-aligned cluster), `steps?` (Stepper config), `breadcrumb?`.
Layout: vertical stack; eyebrow = caption uppercase tracking-0.04em `--color-text-tertiary`; title 36/500; supporting 18/400 `--color-text-secondary` (max 65ch); actions row wraps below on mobile, inline-right on ≥md. Bottom: optional `Stepper`. Bottom border `--color-border-subtle` separating header from body.

### 5.2 `Stepper` — `components/ui/Stepper.tsx`
Horizontal pipeline indicator. Steps: `Upload → Preview → Result`. Each: 28px dot (`--stepper-dot`) + label (13/500). Done = filled orange dot + check; current = orange ring + filled; upcoming = `--color-divider` outline. Connector line `--stepper-line`, completed segment `--stepper-line-done`. Collapses to "Step 2 of 3 · Preview" text on <640px. Reduced-motion: no fill animation.

### 5.3 `StatTile` — `components/ui/StatTile.tsx`
Replaces every ad-hoc summary card. Props: `value`, `label`, `icon?`, `tone?` ('neutral'|'active'|'inactive'|'warning'|'notfound'), `context?` (sub-line), `interactive?`, `selected?`, `onClick?`.
Layout: `--radius-xl`, `--space-5` padding. Top row: 36×36 icon chip (tone-50 bg, tone-500 icon) + optional context pill. Value 32/600 (tone-500 when tone≠neutral, else text-primary). Label 14/500 text-primary. Neutral tiles: `--color-surface-primary` + `--color-border-default`, **no shadow**. Status tiles: tone-50 bg + tone-200 border. Interactive (dashboard filters): `as="button"`, hover lift `--motion-lift-sm`, `selected` → focus-ring outline. This unifies Preview/Generate/Validation/Dashboard metrics.

### 5.4 `Toolbar` — `components/ui/Toolbar.tsx`
Wraps the controls above a table/section. Slots: `title?`, `search?`, `filters?` (SegmentedControl/Select), `actions?`. Responsive: stacks on mobile, single row ≥md with title left, controls right. Used by Dashboard, Validation, Templates, Generate archive.

### 5.5 `SegmentedControl` — `components/ui/SegmentedControl.tsx`
Replaces the ad-hoc tab buttons (Validation) and pill filters (FilterBar/DashboardFilterBar). Options array, single-select. Track `--color-surface-secondary` `--radius-pill`; selected thumb `--color-surface-primary` + `--shadow-sm` + text-primary; unselected text-secondary. Keyboard arrow-navigable, `role="tablist"` when used as tabs.

### 5.6 `NoticeStack` — `components/features/NoticeStack.tsx`
Consolidates the banner pile-up. Takes an array of notices `{variant, title, body, actions?, dismissible?}`. Renders: if ≤1 notice → a single `Banner`. If >1 → a compact summary header ("3 notices · 1 needs attention") with each notice collapsible underneath; errors/actionable always expanded, corrections collapsed by default. Preserves dismiss behavior. Actionable errors still use `Banner variant="error"` and stay visible.

### 5.7 `ResultHero` — `components/features/ResultHero.tsx`
The compact pass/fail header for result screens (Validation, Generate). Props: `tone` ('success'|'error'|'warning'|'info'), `icon`, `headline`, `summary`, `metrics?` (inline StatTile-lite chips), `primaryAction?`, `secondaryAction?`.
Layout: `--radius-2xl`, tone-50 bg, tone-200 border, large status icon in a tone chip, headline 28/500, summary 16/400, metrics as a horizontal chip row, actions right/below. This replaces "plain banner + separate status card."

### 5.8 `DescriptionList` / `KeyValueGrid` — `components/ui/DescriptionList.tsx`
For file summaries, control numbers, entity details. Term (13/500 caption, tertiary) over value (16/400 primary, mono when technical). Responsive 1→2→3 column grid. Replaces hand-built `<p>` pairs in Preview file card and DashboardRow.

### 5.9 `CodeBlock` — `components/ui/CodeBlock.tsx`
Promote the inline dark `<pre>` (Generate raw X12) to a primitive. `--gradient-code` bg, `--color-code-text`, mono 14/1.57, `--radius-lg`, `--space-5` pad, max-height with scroll, right-aligned line-number gutter (48px), built-in **Copy** button (uses `toast.success`), and a segment-count caption. Used by Generate (X12) and Generate batch-summary (mono, light variant).

> All nine land as triplets. Where one supersedes existing feature code (e.g. `FilterBar` → `Toolbar`+`SegmentedControl`), refactor callers and delete the old component in the same change.

---

## 6. Screen-by-screen specifications

Each screen: **Purpose · Route & entry · Layout (wireframe) · Sections · States · Interactions · Responsive · Copy.** Keep all existing data and logic; restyle and recompose only.

---

### 6.1 Home — `pages/HomePage.tsx` · route `/`

**Purpose.** The launchpad: pick one of three actions or drop any file for smart routing.

**Entry.** Default route and `*` fallback.

**Layout (revamped):**
```
PageHeader
  eyebrow:  WORKBENCH
  title:    What would you like to do?
  support:  Generate a 270 from a spreadsheet, validate a 270, or review a 271 — or just drop a file.
  (no stepper on Home; the pipeline starts after a file is chosen)

[ NoticeStack ]  ← only when error / timeout present

HERO ACTION TRIAD  (grid lg:grid-cols-3, gap --space-6)
 ┌── Generate 270 ──┐ ┌── Validate 270 ─┐ ┌── Parse 271 ────┐
 │ ▣ icon chip      │ │ ▣ icon chip     │ │ ▣ icon chip     │
 │ Generate 270     │ │ Validate 270    │ │ Parse 271       │
 │ desc (2–3 lines) │ │ desc            │ │ desc            │
 │ [Select File]    │ │ [Select File]   │ │ [Select File]   │
 │ ⚠ gate helper    │ │                 │ │                 │
 └──────────────────┘ └─────────────────┘ └─────────────────┘

SMART DROPZONE  (full-width Card, gradient-hero wash)
   ⬆  Drag & drop any file here
      Spreadsheets route to Generate · X12 auto-detects 270 vs 271
   [ FileUpload dropzone ]      (Spinner + "Processing…" inline when busy)

HOW IT WORKS  (3-step mini-strip, muted, secondary surface)
   1 Configure provider once → 2 Upload → 3 Download / review
```

**Sections.**
- **Action triad.** Keep `ActionCard` (variant="action") but upgrade: icon chip 56×56 `--color-action-50`/`--color-action-500`, title 20/600, description 14/400 (clamp 3 lines), `FileUpload variant="button"` pinned to card bottom (`mt-auto`). The **Generate** card shows the settings/ICN gate helper (`WarningIcon` + warning-500 caption) and is disabled exactly as today (`!hasRequiredSettings || !hasUsableIcn || isProcessing`).
- **Smart dropzone.** Keep the window-drag pulse affordance (`useFileDropAffordance`, reduced-motion aware) but move it onto a `--gradient-hero` card so it reads as the "or just drop it" path, visually distinct from the triad. Inline `Spinner` + "Processing upload…" on busy.
- **How-it-works strip (new).** Three numbered chips on `--color-surface-secondary`, 13–14px, no shadow. Pure orientation; links step 1 to `/settings`.

**States.** Idle (default) · Processing (cards disabled, dropzone shows spinner) · Error (`NoticeStack` error: unsupported file / API error + suggestion) · Timeout (`NoticeStack` warning with Retry/Cancel — keep `timeoutFile` retry logic).

**Interactions.** Card file select → `handleFile(file, preferredFlow)`. Dropzone → `handleFile(file)` (auto-detect). Generate gate → inline banner, never a dead click. All exactly as today.

**Responsive.** Triad 3-col ≥1024 → 2-col ≥768 → stacked. Dropzone full-width always (reduce vertical pad on mobile). How-it-works wraps to vertical on mobile.

**Copy.** Keep the existing helper/gate strings verbatim (they're carefully scoped). Eyebrow + how-it-works are new and must stay generic/non-PHI.

**Before → After.** Three identical cards + a big box → a clear primary triad with iconography and gating, a visually distinct smart-drop path, and a one-glance "how it works" that orients first-time users.

---

### 6.2 Preview — `pages/PreviewPage.tsx` · route `/preview`

**Purpose.** Show the file summary, corrections, and excluded rows so the operator decides whether to process. Two flows: **generate** (spreadsheet) and **validate/parse** (X12).

**Entry.** From Home via `navigate('/preview', { state })`. No state → "Preview unavailable" fallback (see §6.8).

**Layout:**
```
PageHeader
  eyebrow: STEP 2
  title:   Preview
  support: Review the summary before processing. Corrections and excluded rows are shown here.
  stepper: Upload ●──Preview ◉──Result ○      actions: [Cancel] [Process ▸]

FILE SUMMARY  (Card, DescriptionList)
  File · {filename}      Size · {bytes}      Rows · {n}      [generate] Next ICN · {icn} (Edit ▸)

[ NoticeStack ]   corrections (collapsed) · excluded-rows (with Show details) · member-ID confirm · ICN-not-set · errors · timeout

METRICS  (StatTile row, 4-up)
  generate:  Rows ready | Warnings | Corrections | Excluded
  x12:       Transaction Type | Segments | Sender | Receiver

DETAIL
  generate:  Card "First five rows" → Table (Member, DOB, Member ID, Service Date)
             + Card "Excluded row details" (only when Show details toggled)
  x12:       Card "Detected subscribers" → list (or empty note)

STICKY ACTION BAR (bottom):  [Cancel]              [Process ▸]
```

**Sections.**
- **File summary** → `DescriptionList` (replaces stacked `<p>` tags). For generate, the "Next ICN + Edit in Settings" affordance stays.
- **NoticeStack** consolidates today's separate banners: per-row corrections (collapsed by default, dismissible), excluded-rows summary (with Show/Hide details), the member-ID confirmation prompt (Continue anyway / Review rows), ICN-not-set warning, generic error, timeout (Retry/Cancel). Keep every condition and handler.
- **Metrics** → `StatTile` row (neutral tone for counts; `Excluded`>0 uses warning tone, `Corrections`>0 uses warning tone — a light, meaningful use of color).
- **Detail** keeps the first-five `Table` (generate) and the subscriber list (x12). Excluded-row details remain behind the toggle.
- **Loading.** When processing, show `ProgressBar` (indeterminate) with the live `processingLabel` **and** the skeleton table (keep both — they're good); wrap in one card, not two.

**States.** Ready · Processing (button shows Spinner+"Processing", skeleton+progress) · Member-ID-confirm pending · ICN-not-set (Process disabled + Tooltip "Set ICN in Settings first") · Error · Timeout · Unavailable (no route state).

**Interactions.** `Process` → `handleProcess()` (generate → `/generate/result`; validate → `/validate/result`; parse → `/dashboard`), with ICN bump via `updateLastIcn`. Member-ID warning short-circuits to confirm. `Cancel` → `/`. Keep all.

**Responsive.** StatTiles 4→2→1. Action bar sticky bottom on mobile. Tables horizontal-scroll under 768.

**Before → After.** Banner-wall + gray metric strip + stacked p-tags → a stepper that shows you're mid-pipeline, a tidy `DescriptionList` summary, consolidated notices, meaningful metric tiles, and a sticky decisive action bar.

---

### 6.3 Generate Result — `pages/GenerateResultPage.tsx` · route `/generate/result`

**Purpose.** Confirm the generated 270 package and let the operator download/copy it for submission.

**Entry.** From Preview (generate). No state → fallback.

**Layout:**
```
PageHeader  eyebrow STEP 3 · title "Generate Result" · stepper(…Result ◉)
  actions: [Download X12 / ZIP ▸] [Download Batch Summary] [Copy] [Upload Another]

ResultHero  tone=success (or warning if partial/errors)
  ✔  "270 generated"   summary: {transactions} transactions · {segments} segments · {size}
  metric chips: Transactions | Segments | File Size | Split Count
  primary: Download   secondary: Copy to clipboard

SUBMISSION PACKAGE  (Card)
  Recommended download name → mono chip {primaryDownloadName}
  guidance: submit to Gainwell, keep filename + ISA13 for audit matching

[ ARCHIVE MANIFEST ]  (Card + Toolbar, only when splitCount>1)
  Table: File | Record Range | ISA13

[ BATCH SUMMARY ]  (Card, only when present)
  CodeBlock (light mono variant) {batchSummaryText}   caption: {batchSummaryFileName}

RAW X12 PREVIEW  (Card)
  CodeBlock (dark) — first 10 segments / full toggle · caption "ISA13 … · GS06 …"
```

**Sections.**
- **ResultHero** replaces the lone "Partial result" banner + the standalone summary grid. Success tone normally; warning tone when `response.partial || errors.length>0`, summarizing excluded rows. Metric chips reuse `StatTile`-lite.
- **Submission package** keeps the recommended-name mono chip and audit guidance.
- **Archive manifest** → wrap the `Table` in a `Toolbar` titled "Archive manifest" (only `splitCount>1`).
- **Batch summary** → `CodeBlock` light variant (mono on `--color-surface-subtle`), with its own Copy/Download.
- **Raw X12** → `CodeBlock` dark variant with line numbers, built-in Copy, and the existing 10-segment/full toggle + ISA13/GS06 caption.

**States.** Success · Partial (warning hero) · No content (download/copy disabled) · Unavailable.

**Interactions.** Keep all download handlers (`downloadBlob`/`downloadTextFile`/`decodeBase64ToBlob`), clipboard copy → `toast.success`, "Upload Another" → `/`.

**Responsive.** Hero metrics wrap; CodeBlocks full-width with horizontal scroll preserved.

**Before → After.** A flat "partial banner + 4 gray tiles + raw `<pre>`" → a confident success hero, a clear submission-package callout, and polished code blocks with real copy/line-number affordances.

---

### 6.4 Validation Result — `pages/ValidationResultPage.tsx` · route `/validate/result`

**Purpose.** Per-patient 270 validation: pass/fail, drill into issues, export workbook.

**Entry.** From Preview (validate). No state → fallback.

**Layout:**
```
PageHeader  title "Validation Result" · stepper(…Result ◉)
  actions: [Export Excel ▸] [Download Report (JSON)] [Upload Another]

ResultHero  tone = success | error
  PASS: ✔ "All patients validated"  summary "{total} passed every SNIP check"
  FAIL: ✕ "Validation failed"       summary "{errors} critical, {warnings} warnings"
  metric chips: Total | Valid | Invalid | Errors | Warnings   (StatTile-lite, tone-coded)

RESULTS PANEL  (Card)
  SegmentedControl tabs:  [ Patients ] [ Issues ] [ Summary ]
  Patients:
    Toolbar:  SegmentedControl(All/Valid/Invalid)   +   search "member name or ID"
    PatientValidationTable  (# · Member▸ · Member ID · Service Date · Status badge · Errors · Warnings)
    → row "Member" opens PatientIssueDrawer (right Drawer) with SNIP issue detail
  Issues:  IssueTable (grouped by severity; SNIP-level Badge variant="snip")
  Summary: StatTile grid (Total/Valid/Invalid/Errors/Warnings)
```

**Sections.**
- **ResultHero** merges today's pass/fail `Banner` + the separate status `Card` (badge + metric row) into one tone-coded hero. Keep the auto-scroll/auto-focus-to-export behavior (reduced-motion aware) targeting the hero's primary action.
- **Tabs** → `SegmentedControl` (replaces hand-rolled tab buttons). Keep `Patients/Issues/Summary`.
- **Patients tab** → `Toolbar` with the status `SegmentedControl` + search; `PatientValidationTable` (keep columns; the Member cell stays a `quiet` Button that opens the drawer). `PatientIssueDrawer` stays a right `Drawer`.
- **Fail-collapse behavior** stays: when failed and details hidden, the panel is collapsed until "Show details."
- **Issues / Summary tabs** keep `IssueTable` and metric grid; SNIP codes always shown with plain-English text (contract requirement).

**States.** Pass · Fail (collapsed → expanded) · Export error (`Banner` error) · Unavailable. Empty filter → table empty state.

**Interactions.** Tab switch, filter, debounced search (`useDeferredValue`), row→drawer toggle, `handleExportExcel` (xlsx), JSON report download. Keep all.

**Responsive.** Hero chips wrap; Toolbar stacks; table horizontal-scroll with Name+Status sticky; Drawer full-width sheet on mobile.

**Before → After.** "Banner + status card + DIY tabs + filter bar" → a single tone-coded outcome hero and a clean tabbed results panel with a proper toolbar and segmented controls.

---

### 6.5 Eligibility Dashboard — `pages/EligibilityDashboardPage.tsx` · route `/dashboard`

**Purpose.** Review parsed 271 eligibility: status mix, drill into benefit entities/segments/AAA errors, export workbook. The most data-dense screen — make it feel like a real dashboard.

**Entry.** From Preview (parse). No state → fallback.

**Layout:**
```
PageHeader  title "Eligibility Results" · support "Filter by status, inspect benefits, export."
  actions: [Export Excel ▸]

[ NoticeStack ]  parser-issues warning (when parserIssueCount>0) · export error

STATUS SUMMARY  (StatTile row — interactive filters, 5-up)
  [Errors] [Not Found] [Unknown] [Inactive] [Active]   ← click toggles filter (keep behavior)

RESULTS  (Card)
  Toolbar:  title "Results"  ·  Select "Plan view"  ·  search(member/ID/program/payer/category/note/reason/trace)  ·  [Export Excel]
  DashboardTable  (# · Name · Member ID · Status badge · Program · Payer Code(mono) · Category badge · Notes)
    → expandable row: DashboardRow (Status Reason · Eligibility Segments · Benefit Entities grouped P3/P5/1I · AAA Errors)
  empty filter → EmptyState
```

**Sections.**
- **Status summary** → reuse the **interactive `StatTile`** (this is exactly today's clickable `DashboardSummary` cards, upgraded): tone-coded (Active=active, Inactive=inactive, Errors=warning, Not Found/Unknown=notfound), `selected` ring on active filter, hover lift, value 32–40/600. Keep click-to-toggle-filter and `aria-pressed`.
- **Results** → `Toolbar` (plan-view `Select` + search + Export) above `DashboardTable`. Keep all columns, the multi-plan `PlanValueList`, category badges (BUY-IN→warning else notfound), and the expandable `DashboardRow` detail. Tighten `DashboardRow` into a 3-column `DescriptionList`-style detail with section subheads (Status Reason / Eligibility Segments / Benefit Entities / AAA Errors).
- **Parser issues** → `NoticeStack` warning (keep count + "export includes details").

**States.** Has rows · No rows at all (`EmptyState` in a card — keep) · Filtered-to-empty (table empty state) · Export error (banner) · Parser issues (notice) · Unavailable.

**Interactions.** StatTile filter toggle, plan-view change, debounced search across many fields (keep), row expand/collapse, export per plan view. Keep all.

**Responsive.** StatTiles 5→3→2→1 (`xl:grid-cols-5`). Toolbar stacks. Table horizontal-scroll, Name+Status priority columns; expanded detail goes single-column.

**Before → After.** Already the strongest screen; the revamp standardizes its tiles into `StatTile`, gives the table a real `Toolbar`, and structures the expanded row so dense benefit data is scannable.

---

### 6.6 Templates — `pages/TemplatesPage.tsx` · route `/templates`

**Purpose.** Download canonical import templates and understand required columns.

**Layout:**
```
PageHeader  title "Import Templates" · support "Provider/payer identity lives in Settings, not the sheet."
  actions: [Open Template Spec ↗]

REQUIRED COLUMNS  (Card + Toolbar title "Required columns")
  Table: Column(mono) | Required(badge) | Format | Example(mono)
   Required cell → Badge: Yes=active · Conditional=warning · No=notfound

DOWNLOAD  (grid md:grid-cols-2, gap --space-6)
  ┌ Excel template ┐   ┌ CSV template ┐
  │ ▣ xlsx icon    │   │ ▣ csv icon   │
  │ desc           │   │ desc         │
  │ [Download .xlsx]│  │ [Download .csv]│
  └────────────────┘   └──────────────┘
```

**Sections.**
- **Required columns** → keep the static `Table` but render the `Required` column as a `Badge` (Yes/Conditional/No → active/warning/notfound) so the table isn't all gray text. Column + Example in mono.
- **Download cards** → keep the two cards; add a file-type icon chip (consistent with `ActionCard`) and keep the primary download buttons.

**States.** Static — single state. (Optional: a small "What's a 270?" helper link.)

**Responsive.** Download cards 2→1; table horizontal-scroll.

**Before → After.** Two plain cards + a gray spec table → a badge-coded column reference and iconographic download cards.

---

### 6.7 Settings — `pages/SettingsPage.tsx` · route `/settings`

**Purpose.** Provider/payer/envelope/transaction defaults + ICN management. Explicit draft → Save/Discard. The only `localStorage` consumer (`x12_submitter_config`, non-PHI).

**Layout:**
```
PageHeader  title "Settings" · support "Provider, payer, envelope, and ICN defaults. Save explicitly before generating."
  actions: [Import JSON] [Export JSON] [Save Changes ▸(disabled until dirty)]

[ Banner ]  validation / import errors (dismissible)

TWO-COLUMN CARD GRID  (md:grid-cols-2, gap --space-6, max --layout-settings-max, centered)
  ┌ Interchange Control Number ┐   ┌ Submitter / Provider Identity ┐
  │ ICN warnings (required/exh)│   │ Org, NPI(✓/✕), Entity, TPID … │
  │ ReadOnly: last / next ICN  │   └───────────────────────────────┘
  │ Input: set last ICN        │   ┌ Payer / Receiver ┐
  │ help list + [Save ICN][Clr]│   │ Profile→autofill, names, ISA08│
  └────────────────────────────┘   └───────────────────────────────┘
  ┌ Envelope Defaults ┐            ┌ Transaction Defaults ┐
  │ qualifiers, usage, ack, ver│   │ service type/date, batch size │
  └────────────────────────────┘   └───────────────────────────────┘

UnsavedChangesBar (sticky bottom, only when dirty):  Unsaved changes  [Discard] [Save Changes]
```

**Sections.** Keep all five `SettingsGroup` cards and every field/validation rule exactly. Visual upgrades only:
- Group header: card title 20/600 + description 14/400, bottom border `--color-border-subtle` (keep). Add a small section icon chip per group for scannability (functional icon, action-50 chip).
- Field polish: standardize on the `Input`/`Select` primitives via the existing `TextField`/`SelectField` wrappers; keep the inline NPI `CheckIcon`/`CloseIcon` validity affordance and email validity, required asterisks (`--color-required-asterisk`).
- ICN group stays prominent (it gates generation): keep the two `ReadOnlyField`s (last/next), the digits-only input, the "where to find your ICN" list, Save/Clear, and both warning banners (required / exhausted).
- Import/Export/Save move into the `PageHeader` actions cluster; `UnsavedChangesBar` stays as the sticky safety net.

**States.** Clean · Dirty (Save enabled, UnsavedChangesBar visible) · Field errors (red border + helper, `saveAttempted` gating) · ICN required / exhausted (warning banners) · Import error / success (`toast`). Keep all.

**Interactions.** Draft edits don't persist on blur; `Save Changes` validates then `replaceSettings` + `toast.success`; `Discard` reverts; profile select auto-fills receiver defaults; ICN Save/Clear is independent of the main draft (keep the `preserveDraftOnNextSettingsSyncRef` dance). Import JSON → draft; Export JSON → file.

**Responsive.** 2-col ≥768 → single column; sticky bars remain reachable; ICN card spans full width on mobile.

**Before → After.** A long 2-col form with floating top buttons → the same form with header-anchored actions, per-group iconography for scanning, and unchanged, fully-preserved validation/draft behavior.

---

### 6.8 Shared: route-unavailable fallback & error boundary

- **Unavailable fallback** (Preview/Generate/Validation/Dashboard when `location.state` is null): replace the plain "card + Go Home button" with an `EmptyState` inside a centered card — neutral icon, title (e.g. "Nothing to preview yet"), one-line guidance, primary `Go Home` and secondary `Upload a file`. Consistent across all four pages.
- **ErrorBoundary fallback** (`components/ui/ErrorBoundary.tsx` → `EmptyState`): give it a friendly inactive-tone icon, "Something went wrong on this screen," and a `Reload` action. Never surface raw errors/PHI.

---

## 7. Cross-cutting standards

### 7.1 States (apply to every screen)
- **Loading:** `Skeleton` mirrors final layout (tile row → tile-shaped skeletons; table → header + N row bars). Pair with `ProgressBar` indeterminate only for active server work with a label. Pulses respect reduced-motion.
- **Empty:** always `EmptyState` (icon + title + guidance + optional CTA) — never a bare sentence.
- **Error (actionable):** `Banner variant="error"` with plain-English message + suggestion; stays until resolved/dismissed. **Toasts** only for transient success/info (`toast.success/info/warning/error` from `components/ui/Toast` — never import `sonner`).
- **Success:** `ResultHero` (result pages) or `toast.success` (inline confirmations like copy/save).

### 7.2 Motion choreography
- Route changes: existing `RouteTransition` (opacity + `--motion-route-slide` Y), keyed on pathname.
- Card/tile hover: `--motion-lift-sm` (tiles) / `--motion-lift-md` (action cards) + shadow step, `--duration-normal`, `--ease-out`.
- Drawer/Modal: existing keyframes in `global.css`; Stepper fill `--duration-normal`.
- **Every** motion checks `useReducedMotionPreference` → instant/none. At least one primitive test exercises the reduced-motion branch.

### 7.3 Accessibility
- WCAG AA contrast (4.5:1 body, 3:1 large) — verify tone-50/tone-500 pairings on tiles/badges.
- 44×44 min touch targets (buttons already `min-h-11`).
- Visible focus via `--color-focus-ring` (3px) on every interactive element.
- Semantics: `SegmentedControl` tabs use `role="tablist"`/`tab`; interactive tiles use `as="button"` + `aria-pressed`; tables keep sortable header buttons; Drawer/Modal keep focus traps + ESC.
- Icons are `aria-hidden` when decorative; status conveyed by text/label too, never color alone.

### 7.4 Responsive system
| Breakpoint | Width | Behavior |
|---|---|---|
| Mobile | <768 | single column; PageHeader actions wrap below title; tiles 1–2 up; tables horizontal-scroll (priority cols sticky); sticky action/unsaved bars |
| Tablet | 768–1024 | 2-col grids (Settings, Templates, triad); Toolbars single-row where they fit |
| Desktop | 1024–1280 | 3-col triad, 5-up dashboard tiles, full nav |
| Large | >1280 | content capped at `--layout-container-max` (1200), centered |

Page padding: `--space-6` (mobile) → `--space-8` (tablet) → `--space-10` (desktop).

---

## 8. Build sequence (suggested)

Build shared pieces first so screens compose cleanly:

1. **Foundation** — add §3.5 tokens; fix `global.css` page gradient (drop blue radial); standardize header height.
2. **Chrome** — `AppShell` top-nav + brand mark + footer line; `PageHeader`; header config chip (retire full-width `ConfigStatusBar`).
3. **Shared patterns (triplets)** — `Stepper`, `StatTile`, `Toolbar`, `SegmentedControl`, `NoticeStack`, `ResultHero`, `DescriptionList`, `CodeBlock`. Refactor `FilterBar`/`DashboardFilterBar`/`DashboardSummary` onto them.
4. **Screens** in this order (low-risk → high-value): Templates → Home → Generate Result → Validation Result → Preview → Dashboard → Settings.
5. **States & polish** — unify empty/loading/error/unavailable; ErrorBoundary fallback; motion + reduced-motion audit.
6. **Docs & gates** — update `docs/design-spec.md` + `docs/ui-components.md` for each new primitive; run `make design-lint`, `npm run lint`, `npm run typecheck`, `npm run test -- --run`, `npm run build`.

Each step is independently shippable; nothing changes API or routes.

---

## 9. Acceptance checklist

**Global**
- [ ] No hardcoded hex/px/ms anywhere (`make design-lint` passes).
- [ ] No raw `<button>`/`<input type=file>`/`<table>` in `pages/**` or `components/features/**`.
- [ ] Page background is the warm gradient; the blue radial is gone.
- [ ] Header has brand mark, full nav (incl. Home), and a compact config chip.
- [ ] Pipeline screens show the `Stepper`; non-pipeline screens don't.
- [ ] Every screen uses one `PageHeader` with an action cluster.
- [ ] All summary numbers are `StatTile`s; tables sit under a `Toolbar`.
- [ ] Banner pile-ups are gone (consolidated via `NoticeStack`); result screens use `ResultHero`.
- [ ] Loading/empty/error/unavailable states use the shared patterns.
- [ ] Reduced-motion verified on every animated surface; ≥1 test covers it.
- [ ] WCAG AA contrast + visible focus on all interactive elements.

**Per screen** — feature parity preserved (all data, handlers, validations, downloads, filters, drawers, ICN logic intact) and the §6 layout realized.

**Docs** — `design-spec.md`, `ui-components.md`, and tests updated for every new/changed primitive (the triplet rule).

---

## Appendix A — Component → screen usage map

| Pattern | Home | Preview | Gen. Result | Valid. Result | Dashboard | Templates | Settings |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| PageHeader | ● | ● | ● | ● | ● | ● | ● |
| Stepper | | ● | ● | ● | | | |
| StatTile | | ● | ● | ● | ●(interactive) | | |
| Toolbar | | | ●(archive) | ●(patients) | ● | ●(columns) | |
| SegmentedControl | | | | ●(tabs+filter) | ●(filter) | | |
| NoticeStack | ● | ● | | | ● | | ●(banner) |
| ResultHero | | | ● | ● | | | |
| DescriptionList | | ● | ●(package) | | ●(row detail) | | ●(read-only) |
| CodeBlock | | | ●(X12+summary) | | | | |
| ActionCard | ● | | | | | ●(downloads) | |
| Table | | ● | ● | ●(patients) | ● | ● | |
| Drawer | | | | ●(issues) | | | |
| UnsavedChangesBar | | | | | | | ● |

## Appendix B — Documented alternative: left-rail shell

If the toolset grows beyond ~7 routes, switch `AppShell` to a 2-pane layout: a 240px left rail (`--layout-sidebar-w`) with brand + vertical nav + config card pinned bottom, and a scrolling content pane. Reuse `PageHeader` unchanged inside the pane. Not the default — the top-nav model fits a focused, once-a-week tool better and keeps the Meta-Store retail-clarity feel.
