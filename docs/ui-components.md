# UI Component Catalog

> **Frontend agents start at [`docs/design-spec.md`](./design-spec.md).** This document remains the primitive API appendix; `design-spec.md` is the single enforceable contract for UI work.

> One-page reference for every shared primitive in [`apps/web/src/components/ui/`](../apps/web/src/components/ui/). Each entry lists import path, purpose, prop API, usage snippet, and accessibility notes.
>
> **Rules of engagement:**
> - Always compose existing primitives before adding new ones.
> - New primitives belong in `components/ui/`; feature-specific components belong in `components/features/`.
> - Token values (colors, radii, shadows, spacing, motion) must come from [`tokens.css`](../apps/web/src/styles/tokens.css). Never hardcode hex values.
> - Visual and composition rules live in [`design-system.md`](./design-system.md).

---

## Quick index

| Primitive | File | Purpose |
|---|---|---|
| [`Button`](#button) | [`ui/Button.tsx`](../apps/web/src/components/ui/Button.tsx) | The one button component. Renders `<button>` or `<a>` depending on `href`. |
| [`Input`](#input) | [`ui/Input.tsx`](../apps/web/src/components/ui/Input.tsx) | Token-driven text, search, and scalar form fields. |
| [`Select`](#select) | [`ui/Select.tsx`](../apps/web/src/components/ui/Select.tsx) | Token-driven native dropdown with a shared chevron treatment. |
| [`Card`](#card) | [`ui/Card.tsx`](../apps/web/src/components/ui/Card.tsx) | Surface container: content card (flat) or action card (interactive). |
| [`Badge`](#badge) | [`ui/Badge.tsx`](../apps/web/src/components/ui/Badge.tsx) | Status pill with active / inactive / warning / notfound / snip variants. |
| [`Banner`](#banner) | [`ui/Banner.tsx`](../apps/web/src/components/ui/Banner.tsx) | Inline page-level notification with icon and optional dismiss. |
| [`FileUpload`](#fileupload) | [`ui/FileUpload.tsx`](../apps/web/src/components/ui/FileUpload.tsx) | Drop-zone or button file input. Keyboard- and drag-aware. |
| [`Spinner`](#spinner) | [`ui/Spinner.tsx`](../apps/web/src/components/ui/Spinner.tsx) | Indeterminate loading indicator. |
| [`Table`](#table) | [`ui/Table.tsx`](../apps/web/src/components/ui/Table.tsx) | Sortable, paginated, expandable typed data table. |
| [`Icons`](#icons) | [`ui/Icons.tsx`](../apps/web/src/components/ui/Icons.tsx) | Stroke-based inline SVG icon set (upload, document, shield, etc.). |

---

## Button

**Path:** [`apps/web/src/components/ui/Button.tsx`](../apps/web/src/components/ui/Button.tsx)

The canonical interactive control. Polymorphic over `<button>` vs `<a>`: pass `href` to get an anchor, omit it to get a button.

### Variants

| Variant | When |
|---|---|
| `primary` *(default)* | Main CTA: Process, Download X12, Save. |
| `secondary` | Secondary CTA: Cancel, Upload Another, Copy. |
| `ghost` | Tertiary action / inline link inside a card. |
| `quiet` | Corner controls, dismiss buttons, subtle controls. |
| `table` | Sortable table header button. No padding, uppercase label. |

### Sizes

`sm` (compact, 9-unit min-height) · `md` *(default)* · `icon` (square, for icon-only buttons).

### Props

```ts
type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'quiet' | 'table'
type ButtonSize    = 'sm' | 'md' | 'icon'

// Renders <button> when href is absent, <a> when href is present.
interface ButtonProps {
  children: ReactNode
  variant?: ButtonVariant   // default: 'primary'
  size?:    ButtonSize      // default: 'md'
  leftIcon?:  ReactNode
  rightIcon?: ReactNode
  className?: string
  // plus any native <button> or <a> attributes (onClick, disabled, href, target, …)
}
```

### Usage

```tsx
import { Button } from '../components/ui/Button'
import { DownloadIcon } from '../components/ui/Icons'

<Button onClick={handleGenerate}>Generate 270</Button>

<Button variant="secondary" size="sm" onClick={handleCancel}>Cancel</Button>

<Button variant="ghost" leftIcon={<DownloadIcon className="h-4 w-4" />} href="/api/v1/export">
  Download X12
</Button>
```

### Accessibility

- Focus state: 3px action-blue ring at 25% alpha (`--color-focus-ring`).
- Min touch target: 44px height (`min-h-11`).
- Disabled state uses `disabled` attribute, not pointer-events tricks — screen readers announce correctly.
- Icon-only buttons must pass `aria-label`.

---

## Input

**Path:** [`apps/web/src/components/ui/Input.tsx`](../apps/web/src/components/ui/Input.tsx)

Native `<input>` wrapper for text, search, date-like, and scalar form fields. Feature code owns labels and helper text; the primitive owns the control styling and state treatment.

### Props

```ts
type InputProps = InputHTMLAttributes<HTMLInputElement>
```

### Usage

```tsx
import { Input } from '../components/ui/Input'

<label className="flex flex-col gap-2 text-sm font-medium text-[var(--color-text-primary)]">
  Search
  <Input
    type="search"
    value={search}
    onChange={(event) => setSearch(event.currentTarget.value)}
    placeholder="Search member, ID, plan, reason, or trace"
  />
</label>

<Input disabled value="Settings locked" />
```

### Accessibility

- Pair with a visible `<label>` or an `aria-label`.
- Use `disabled` for unavailable controls so browsers and assistive tech expose the state correctly.
- Use native `type` values for keyboard and autofill behavior; do not simulate text fields with divs.

---

## Select

**Path:** [`apps/web/src/components/ui/Select.tsx`](../apps/web/src/components/ui/Select.tsx)

Native `<select>` wrapper for compact option sets. It keeps browser keyboard behavior and applies the shared field styling plus a consistent chevron.

### Props

```ts
type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  wrapperClassName?: string
}
```

### Usage

```tsx
import { Select } from '../components/ui/Select'

<label className="flex flex-col gap-2 text-sm font-medium text-[var(--color-text-primary)]">
  Filter
  <Select value={filter} onChange={(event) => setFilter(event.currentTarget.value)}>
    <option value="all">All</option>
    <option value="active">Active</option>
  </Select>
</label>

<Select wrapperClassName="max-w-xs" aria-label="Status">
  <option value="valid">Valid</option>
  <option value="invalid">Invalid</option>
</Select>
```

### Accessibility

- Prefer a visible label; use `aria-label` only for compact tool surfaces where surrounding text already gives context.
- Keep option labels short and concrete.
- Use the native `disabled` attribute for unavailable dropdowns.

---

## Card

**Path:** [`apps/web/src/components/ui/Card.tsx`](../apps/web/src/components/ui/Card.tsx)

Surface container rendered as `<section>`.

### Variants

| Variant | When |
|---|---|
| `content` *(default)* | Flat content card: 16px radius, `--shadow-sm`. |
| `action` | Interactive action card: 16px radius, `--shadow-md`, lifts on hover (`-2px`, `--shadow-lg`). |

### Props

```ts
interface CardProps {
  children:   ReactNode
  variant?:   'content' | 'action'   // default: 'content'
  className?: string
}
```

### Usage

```tsx
import { Card } from '../components/ui/Card'

<Card>
  <h2 className="text-[20px] font-semibold">Submitter Identity</h2>
  <p className="text-[14px] text-[var(--color-text-secondary)]">…</p>
</Card>

<Card variant="action">
  {/* icon → title → description → ghost button */}
</Card>
```

### Accessibility

- Rendered as `<section>`; supply a heading inside so screen readers can land on it.
- Action variant is visual-only; wrap its interactive content in an actual `Button` or anchor — don't make the whole card a click target unless the card itself is a link.

---

## Badge

**Path:** [`apps/web/src/components/ui/Badge.tsx`](../apps/web/src/components/ui/Badge.tsx)

Short, uppercase status pill. Appears only in badges, stat cards, and table status cells.

### Variants

| Variant | Meaning | Tokens |
|---|---|---|
| `active` | Active eligibility, pass | `--color-active-50` bg, `--color-active-500` text |
| `inactive` | Inactive, fail, denial | `--color-inactive-50` / `-500` |
| `warning` | Auto-correction, partial match | `--color-warning-50` / `-500` |
| `notfound` | Member not found, unknown | `--color-notfound-50` / `-500` |
| `snip` | SNIP level badge (mono, bordered) | `--color-surface-secondary` with border |

### Props

```ts
interface BadgeProps {
  children:   ReactNode
  variant:    'active' | 'inactive' | 'warning' | 'notfound' | 'snip'
  className?: string
}
```

### Usage

```tsx
import { Badge } from '../components/ui/Badge'

<Badge variant="active">ACTIVE</Badge>
<Badge variant="inactive">FAIL</Badge>
<Badge variant="warning">CORRECTED</Badge>
<Badge variant="notfound">NOT FOUND</Badge>
<Badge variant="snip">SNIP 2</Badge>
```

### Accessibility

- Treat badges as decorative reinforcement of text. Always include a machine-readable status elsewhere (e.g., table cell text) so screen readers don't rely on color alone.

---

## Banner

**Path:** [`apps/web/src/components/ui/Banner.tsx`](../apps/web/src/components/ui/Banner.tsx)

Inline page-level notification with an icon, optional title, body, optional actions, and optional dismiss button.

### Variants

| Variant | Use |
|---|---|
| `info` | Informational message (action-blue accent). |
| `warning` | Auto-correction applied, non-critical warning (amber accent). |
| `error` | Validation failure, network error (inactive-red accent). |
| `success` | Confirmation (active-green accent). |

### Props

```ts
interface BannerProps {
  children:       ReactNode                            // body content
  variant:        'info' | 'warning' | 'error' | 'success'
  title?:         string                               // optional bold title line
  actions?:       ReactNode                            // buttons / links below body
  onDismiss?:     () => void                           // shows close button when provided
  dismissLabel?:  string                               // aria-label for dismiss (default: 'Dismiss')
  className?:     string
}
```

### Usage

```tsx
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'

<Banner
  variant="warning"
  title="Corrections applied"
  onDismiss={() => setBannerOpen(false)}
>
  2 rows had missing middle initials — auto-corrected from prior submissions.
</Banner>

<Banner
  variant="error"
  title="Generation failed"
  actions={<Button variant="secondary" size="sm" onClick={retry}>Retry</Button>}
>
  Submitter NPI failed Luhn validation.
</Banner>
```

### Accessibility

- Rendered with `role="status"` — screen readers announce changes politely.
- Use `error` sparingly for true failures; prefer inline field errors for form validation.

---

## FileUpload

**Path:** [`apps/web/src/components/ui/FileUpload.tsx`](../apps/web/src/components/ui/FileUpload.tsx)

Single-file input. Two visual modes: full drop zone or a compact secondary button.

### Variants

| Variant | Use |
|---|---|
| `dropzone` *(default)* | Hero area on the home page: drag-and-drop + click to browse. |
| `button` | Compact "Upload another" control inline on preview pages. |

### Props

```ts
interface FileUploadProps {
  onFileSelect: (file: File) => void
  variant?:     'dropzone' | 'button'   // default: 'dropzone'
  accept?:      string                  // e.g., '.xlsx,.csv,.x12,.edi'
  disabled?:    boolean
  title?:       string                  // dropzone only — default: 'Drag & drop any file here'
  description?: string                  // dropzone only — default: 'or click to browse (.xlsx .csv .x12 .edi)'
  buttonLabel?: string                  // default: 'Select File'
}
```

### Usage

```tsx
import { FileUpload } from '../components/ui/FileUpload'

// Home page drop zone
<FileUpload
  accept=".xlsx,.csv,.x12,.edi,.txt"
  onFileSelect={handleFile}
  description="or click to browse (.xlsx .csv .x12 .edi)"
/>

// Inline "Upload another" button
<FileUpload
  variant="button"
  accept=".xlsx,.csv"
  buttonLabel="Upload another"
  onFileSelect={handleAnotherUpload}
/>
```

### Accessibility

- Dropzone acts as a `role="button"` with `tabIndex=0`, activatable by `Enter` or `Space`.
- Drag-over state (`isDragging`) is purely visual; keyboard users see the solid focus ring.
- `disabled` state removes both keyboard and pointer affordances.

---

## Spinner

**Path:** [`apps/web/src/components/ui/Spinner.tsx`](../apps/web/src/components/ui/Spinner.tsx)

Indeterminate loading indicator. 20×20px action-blue ring, CSS animation.

### Props

None.

### Usage

```tsx
import { Spinner } from '../components/ui/Spinner'

{isGenerating ? <Spinner /> : 'Generate 270'}
```

### Accessibility

- Rendered with `aria-hidden="true"` — pair with an accessible label in the surrounding container (e.g., a button's text content changes to "Generating…").

---

## Table

**Path:** [`apps/web/src/components/ui/Table.tsx`](../apps/web/src/components/ui/Table.tsx)

Generic, type-parameterized data table with sorting, pagination, and optional expandable rows.

### Props

```ts
interface TableColumn<T> {
  id:              string
  header:          string
  cell:            (row: T, index: number) => ReactNode
  sortValue?:      (row: T) => number | string   // absent → column is not sortable
  className?:      string                        // applied to <td>
  headerClassName?: string                       // applied to <th>
}

interface TableProps<T> {
  rows:              T[]
  columns:           Array<TableColumn<T>>
  rowKey:            (row: T, index: number) => string
  pageSize?:         number                              // default: 10
  emptyMessage?:     string                              // default: 'No rows to display.'
  renderExpandedRow?: (row: T) => ReactNode              // enables expand/collapse chevron
}
```

### Usage

```tsx
import { Table, type TableColumn } from '../components/ui/Table'
import { Badge } from '../components/ui/Badge'

type Row = { id: string; name: string; status: 'active' | 'inactive' }

const columns: Array<TableColumn<Row>> = [
  { id: 'name', header: 'Name', cell: (r) => r.name, sortValue: (r) => r.name },
  { id: 'status', header: 'Status', cell: (r) => (
      <Badge variant={r.status}>{r.status.toUpperCase()}</Badge>
  ) },
]

<Table
  rows={rows}
  columns={columns}
  rowKey={(r) => r.id}
  renderExpandedRow={(r) => <SegmentList segments={r.segments} />}
/>
```

### Accessibility

- Header sort buttons reuse `Button` with `variant='table'` — focusable and keyboard-operable.
- Expand/collapse chevrons use `Button` with `variant='quiet'` and carry `aria-label='Expand row' | 'Collapse row'`.
- Pagination controls are disabled at list boundaries; screen readers announce the disabled state.

### Performance

- Sorting is client-side and memoized on `(columns, rows, sort)`.
- Pagination is client-side; for large datasets, pre-filter before passing to the table.

---

## Icons

**Path:** [`apps/web/src/components/ui/Icons.tsx`](../apps/web/src/components/ui/Icons.tsx)

Stroke-based inline SVG icon set. All icons share a common `IconBase` (stroke 1.8, round caps/joins, `currentColor`).

### Available icons

`UploadIcon` · `DocumentIcon` · `ShieldIcon` · `SearchIcon` · `SettingsIcon` · `ChevronRightIcon` · `ChevronDownIcon` · `DownloadIcon` · `CopyIcon` · `InfoIcon` · `WarningIcon` · `CheckIcon` · `CloseIcon`.

### Props

Each icon is typed as `SVGProps<SVGSVGElement>` — pass any SVG attribute. Size the icon via Tailwind classes; color follows `currentColor`.

### Usage

```tsx
import { UploadIcon, DownloadIcon, ChevronRightIcon } from '../components/ui/Icons'

<UploadIcon className="h-8 w-8 text-[var(--color-text-secondary)]" />

<Button leftIcon={<DownloadIcon className="h-4 w-4" />}>Download X12</Button>

<ChevronRightIcon className={cn('h-4 w-4 transition-transform', expanded && 'rotate-90')} />
```

### Rules

- All icons are `aria-hidden` by default. If an icon conveys meaning on its own (not paired with text), wrap it and add `aria-label` to the wrapper.
- Icons never introduce color — they inherit from `currentColor`. Style the parent, not the icon.
- Prefer composition (icon inside a labeled button) over decorative icons.

---

## Adding a new primitive

Before creating a new file in `components/ui/`:

1. **Check this page first.** If the behavior fits an existing primitive, extend that primitive instead.
2. Confirm it is reusable — 2+ unrelated callers. One-off visuals belong in `components/features/`.
3. Use tokens from [`tokens.css`](../apps/web/src/styles/tokens.css) for every color, radius, shadow, spacing, and motion value. If a token doesn't exist, add it there first.
4. Add the primitive to the [Quick index](#quick-index) above with a one-line purpose.
5. Document its prop API and minimum two usage snippets.
6. Add tests in [`apps/web/src/__tests__/`](../apps/web/src/__tests__/).

---

## Change log

| Version | Date | Change |
|---|---|---|
| 1.1 | 2026-04-24 | Added Input and Select primitives for shared form controls. |
| 1.0 | 2026-04-17 | Initial catalog. Covers all 8 primitives currently in `components/ui/`. |
