# Plan — ICN Duplicate Fix + Mastercard Theme + UX Pass

> **Status:** Approved 2026-04-30. Revised 2026-04-30 after engineering review.
> **Implementation rule:** ship in phases. The ICN duplicate fix is the urgent safety fix and must not be coupled to the larger visual refresh.

## Context

DC Medicaid / Gainwell rejects 270 submissions when ISA13, the Interchange Control Number, repeats for the same trading partner. The current web app stores the last ISA13 only in browser `localStorage` under `x12_submitter_config.lastIsaControlNumber`. A fresh browser, incognito window, cleared storage, or another machine starts from `null`; today `nextIsaControlNumber(null)` returns `1`, which can regenerate `000000001`.

Project constraints still apply:

- Keep the app stateless. Do not add a database, queue, server-side counter, or server-side file retention.
- Treat upload and fixture data as healthcare-adjacent. Do not persist patient data in browser storage or logs.
- Use `CLAUDE.md` as the project source for commands, architecture, design-contract rules, and release process.

The revised approach is:

- The biller remains the source of truth for the last ICN submitted to Gainwell.
- The app refuses to generate a 270 until it has an explicit, user-provided last submitted ICN.
- The API also refuses blind generation without an explicit `isaControlNumberStart` / `gsControlNumberStart`, so the invariant is enforced outside the browser UI.
- Because the system is stateless, this prevents the known `null -> 000000001` failure mode but cannot coordinate simultaneous users sharing the same trading partner ID. Multi-user offices still need an operational rule: one active generator at a time, or export/import Settings JSON after each submission batch.

## Scope

| Phase | Scope | Why |
|---|---|---|
| 1 | ICN duplicate prevention | Urgent production rejection fix; smallest safe blast radius. |
| 2 | Excel and dashboard eligibility improvements | Operator reporting improvements independent from ICN. |
| 3 | Templates, Settings UX, Mastercard theme, icons, animations | Visual and workflow polish after the core safety fix is stable. |
| 4 | Version bump and docs regeneration | Release metadata after the functional changes land. |

## Phase 1 — ICN Duplicate Prevention

### What

Make ICN state explicit and enforceable:

- `nextIsaControlNumber(null)` returns `null`.
- `lastIsaControlNumber = null` means generation is blocked.
- `lastIsaControlNumber >= 999999999` also blocks generation; do not wrap to `000000001`, because the payer uniqueness rule is not window-scoped.
- Settings exposes the last submitted ICN and the next ICN that will be sent.
- Preview shows the next ICN and disables Process when unset.
- API generation rejects requests missing explicit control-number starts.

### Why

UI-only blocking is not enough. The backend currently defaults missing control numbers to `1` in `apps/api/app/services/generator.py`, and `ApiSubmitterConfig` allows `isa_control_number_start` / `gs_control_number_start` to be `None`. Any non-browser caller, stale UI, or `/pipeline` path could still generate a duplicate `000000001`.

### How

#### 1. Utility changes

File: `apps/web/src/utils/constants.ts`

```ts
export function nextIsaControlNumber(last: number | null): number | null {
  if (last === null) return null
  if (last >= MAX_ISA_CONTROL_NUMBER) return null
  return last + 1
}

export function hasUsableNextIsaControlNumber(last: number | null): boolean {
  return nextIsaControlNumber(last) !== null
}

export function formatIsaControlNumber(value: number): string {
  return String(value).padStart(9, '0')
}
```

Tests:

- `nextIsaControlNumber(null) === null`
- `nextIsaControlNumber(19) === 20`
- `nextIsaControlNumber(999_999_998) === 999_999_999`
- `nextIsaControlNumber(999_999_999) === null`
- `hasUsableNextIsaControlNumber(null) === false`
- `hasUsableNextIsaControlNumber(19) === true`
- `hasUsableNextIsaControlNumber(999_999_999) === false`

#### 2. Settings hook changes

File: `apps/web/src/hooks/useSettings.tsx`

Add pure parsing/validation helpers and expose ICN readiness without conflating it with general required settings.

```ts
interface SettingsContextValue {
  settings: SubmitterConfig
  hasRequiredSettings: boolean
  hasUsableIcn: boolean
  replaceSettings: (nextSettings: SubmitterConfig) => void
  parseSettingsJson: (rawValue: string) => SubmitterConfig
  updateLastIcn: (isa13: string) => void
}
```

Rules:

- `hasRequiredSettings` remains the provider/payer/profile completeness check.
- `hasUsableIcn` is true only when `lastIsaControlNumber` is non-null and below `MAX_ISA_CONTROL_NUMBER`.
- `updateLastIcn` must parse strictly with `/^\d{1,9}$/`; do not use `parseInt` on arbitrary strings.
- JSON import should parse and sanitize into a draft in `SettingsPage`; persistence happens only through explicit Save, unless the import UI clearly labels import as an immediate save action. Prefer draft + Save for consistency with the new save model.
- `lastIsaControlNumber` remains the only ICN state. Do not add submission history.

Tests:

- Valid generated ISA13 persists to localStorage.
- Non-numeric, mixed, zero, negative, and >9-digit values are ignored.
- Imported settings preserve valid `lastIsaControlNumber`.
- Invalid imported `lastIsaControlNumber` sanitizes to `null`.

#### 3. Settings ICN UI

File: `apps/web/src/pages/SettingsPage.tsx`

Add a Settings group anchored as `id="icn"` titled **Interchange Control Number**.

Required elements:

- Non-dismissible warning banner when `draft.lastIsaControlNumber === null`.
- Read-only **Last submitted ICN** value, formatted as 9 digits or `— not set —`.
- Read-only **Next ICN to be used**, formatted as 9 digits or `— not set —`.
- Input labeled **Set your last submitted ICN**.
- Helper text telling the biller where to find the last ICN:
  - Gainwell submission portal.
  - Most recent generated/downloaded 270 filename.
  - 999 acknowledgements.
  - Settings JSON exported from the browser that last generated files.
- Dedicated **Save ICN** button plus **Clear** action.

Input semantics:

- Accept digits only, length 0-9.
- Empty or `000000000` clears `lastIsaControlNumber` to `null`.
- Values `1..999999998` are usable and show a next ICN.
- Value `999999999` can be stored as the last submitted ICN but blocks generation with copy instructing the operator to contact Gainwell or confirm a new trading-partner control-number policy. Do not wrap.
- On blur, display non-empty values zero-padded to 9 digits.

Save semantics:

- Page-level **Save Changes** persists the whole draft.
- **Save ICN** persists only `lastIsaControlNumber`, preserves the rest of the saved settings, and patches the draft to match.
- **Clear** sets the input/draft to the unset sentinel; persistence still requires **Save ICN** or **Save Changes**.
- The sticky unsaved-changes bar compares draft vs saved settings and must update correctly after **Save ICN**.

#### 4. Preview generation gate

File: `apps/web/src/pages/PreviewPage.tsx`

For generate flow:

- Compute `const nextIcn = nextIsaControlNumber(settings.lastIsaControlNumber)`.
- Show **Next ICN: 000000020 · Edit in Settings** when available.
- Show **Next ICN: — not set —** when unavailable.
- Render a blocking warning banner when unavailable:

  > Cannot generate — ICN not set. Each 270 file submitted to DC Medicaid must use a unique ISA13. Set the last submitted ICN in Settings before continuing.

- Disable Process when `nextIcn === null`.
- Wrap disabled Process with the existing `Tooltip` primitive: `Set ICN in Settings first`.
- During processing, disable Process and show a `Spinner` in the button in addition to the existing progress state.
- After successful generation, continue setting `lastIsaControlNumber` to `highestIsa13(response)`.

#### 5. Home and configuration readiness

Files:

- `apps/web/src/pages/HomePage.tsx`
- `apps/web/src/components/features/ConfigStatusBar.tsx`

Generate should require both provider settings and usable ICN:

- Keep parse/validate workflows independent from ICN.
- Disable the Generate 270 action card when provider settings are incomplete or ICN is not usable.
- Config status should distinguish:
  - Provider settings incomplete.
  - ICN not set.
  - ICN exhausted at `999999999`.
  - Ready to generate.

#### 6. API invariant

Files:

- `apps/api/app/schemas/common.py`
- `apps/api/app/services/generator.py`
- `apps/api/app/routers/generate.py`
- `apps/api/app/routers/pipeline.py`

Backend behavior:

- `/api/v1/generate` must reject missing `isa_control_number_start` or `gs_control_number_start`.
- `/api/v1/pipeline` must do the same for JSON and multipart flows before calling `generate_270_response`.
- Reject values outside `1..999999999`.
- Return a 422 with clear copy:

  > ISA control number start is required. Set the last submitted ICN in Settings so the app can send the next unique ISA13.

Implementation options:

- Add a request-level validator in `GenerateRequest` that requires `config.isa_control_number_start` and `config.gs_control_number_start`.
- Or add a service guard at the top of `generate_270_response` and have both routers map it to 422.

Preferred option: request-level validation for `/generate`, plus explicit pipeline guard where multipart form config is converted before `GenerateRequest` is created.

Tests:

- `/generate` without control-number starts returns 422.
- `/generate` with starts returns 200 and emits the requested ISA13.
- `/pipeline` without starts returns 422.
- Split generation with `maxBatchSize` increments ISA13/GS06 from the provided start.

#### 7. ICN limitations in copy

Add concise copy in Settings:

> This app is stateless. If multiple people generate files under the same trading partner ID, coordinate who generates next or export/import Settings JSON after each accepted batch.

This avoids promising a cross-device lock the architecture cannot provide.

## Phase 2 — Excel And Dashboard Improvements

### What

Improve 271 review outputs:

- Add a user-friendly `Errors` sheet to eligibility Excel exports.
- Split pipe-delimited benefit descriptions into structured columns.
- Highlight error rows in the `Eligibility Results` sheet.
- Mirror the same structured plan columns in the dashboard.

### Why

Operators currently see summary counts but need readable row-level explanations and sortable benefit metadata.

### How

#### 1. Shared plan parsing behavior

Server helper in `apps/api/app/services/exporter.py`:

```python
def _split_plan_description(description: str | None) -> tuple[str, str, str]:
    if not description:
        return ("", "", "")
    parts = [part.strip() for part in description.split("|")]
    if len(parts) < 3:
        return (description, "", "")
    return (parts[0], parts[1], parts[2])
```

Client mirror in `apps/web/src/utils/plan.ts`:

```ts
export interface ParsedPlan {
  programName: string
  payerCode: string
  category: string
}
```

Keep server and client tests in sync. Do not codegen unless this rule set grows.

#### 2. Excel export

File: `apps/api/app/services/exporter.py`

Use one predicate for both sheet inclusion and row tint:

```python
def _is_error_row(result: EligibilityResult) -> bool:
    return result.overall_status in {"error", "not_found"} or bool(result.aaa_errors)
```

Create the `Errors` sheet when `any(_is_error_row(result) for result in payload.results)`.

Sheet order:

1. `Summary`
2. `Errors` when present
3. `Eligibility Results`
4. `Parser Issues` when present

`Errors` columns:

| Column | Source |
|---|---|
| `member_name` | `result.member_name` |
| `member_id` | `result.member_id` |
| `error_type` | `AAA` when `aaa_errors`, else `STATUS` |
| `aaa_code` | `aaa_error.code` or blank |
| `error_summary` | AAA message or `result.status_reason` |
| `recommended_action` | AAA suggestion or fallback action |
| `follow_up_action_code` | `aaa_error.follow_up_action_code` |
| `st_control_number` | `result.st_control_number` |
| `trace_number` | `result.trace_number` |

`Eligibility Results` replaces `primary_plan_summary` with:

- `program_name`
- `payer_code`
- `category`
- `billing_note`

Rows where `_is_error_row(result)` is true get a light red fill. Document the fill value in `docs/design-system.md` because server-side openpyxl cannot consume CSS variables.

Tests go in existing `apps/api/tests/test_export.py`:

- Clean payload keeps sheet order `["Summary", "Eligibility Results"]`.
- Payload with `not_found` but `summary.error === 0` still gets `Errors`.
- AAA error row gets readable message/suggestion.
- Pipe-delimited plan splits into the new columns.
- Plain plan description stays in `program_name`.
- Error rows are filled; header and non-error rows are not.

#### 3. Dashboard

Files:

- `apps/web/src/components/features/DashboardTable.tsx`
- `apps/web/src/components/features/EligibilityDashboard.tsx`
- `apps/web/src/components/features/DashboardSummary.tsx`
- `apps/web/src/components/features/FilterBar.tsx`

Changes:

- KPI cards center contents and increase stat value size using existing typography tokens or token-backed classes.
- Move Export Excel to its own row above Filter/Search.
- Replace the raw Plan column with Program, Payer Code, Category, Notes.
- Use `Badge` for category; `BUY-IN` uses warning variant.
- Search matches `programName`, `payerCode`, `category`, and billing note in addition to existing fields.

Tests:

- `splitPlanDescription` parses pipe-delimited and plain descriptions.
- Dashboard renders Program/Payer/Category/Notes columns.
- Search for `BUY-IN` and `853Q` filters correctly.
- Export button remains reachable and not compressed on narrow layouts.

## Phase 3 — UX, Theme, Templates, Icons, Animations

### What

Refresh the UI while keeping workflow density:

- Mastercard-inspired warm theme.
- Explicit Settings save model.
- Settings 2-column layout on medium+ screens.
- Required-field red asterisks.
- Header `?` becomes Home icon.
- Templates page is simplified.
- Limited token-backed motion.
- Optional Material Symbols migration.

### Why

These are usability and polish improvements, but they are not required to stop duplicate ICNs. They should follow the safety fix.

### How

#### 1. Design docs and tokens

Files:

- `apps/web/src/styles/tokens.css`
- `docs/design-system.md`
- `docs/design-spec.md`
- `docs/ui-components.md`

Use the radius token names that already exist in `tokens.css`.

Token updates:

| Token | New role |
|---|---|
| `--color-action-500` | Mastercard orange primary CTA/focus |
| `--color-action-600` | CTA hover |
| `--color-action-700` | CTA pressed |
| `--color-action-50` / `--color-action-100` | Orange-tinted surfaces |
| `--color-surface-primary` | Warm cream primary surface |
| `--color-surface-secondary` / `--color-surface-tertiary` | Secondary warm surfaces |
| `--color-surface-wash` | Page canvas wash |
| `--color-inactive-500` | Mastercard red error |
| `--color-inactive-50` | Error-row/background tint |
| `--color-required-asterisk` | Required marker |
| `--duration-route` | Route transition duration |
| `--motion-fade-in` | Validation/banner fade duration |
| `--motion-route-slide` | Route offset |

Radius updates use existing names:

- Consider `--radius-xl: 20px`.
- Consider `--radius-2xl: 24px`.
- Keep `--radius-md` and `--radius-pill` unchanged.

Update `docs/design-spec.md` to remove conflicts with the new behavior:

- Replace the old Settings layout rule with the new responsive 2-column rule.
- Update RouteTransition docs if changing current 200ms / 6px behavior.
- Keep the source order: tokens for values, design-spec for rules, design-system for rationale, ui-components for APIs.

#### 2. Settings rebuild

Files:

- `apps/web/src/pages/SettingsPage.tsx`
- Optional new `apps/web/src/components/ui/FormField.tsx`
- New `apps/web/src/components/ui/UnsavedChangesBar.tsx`

Rules:

- Remove auto-save-on-blur.
- Add sticky UnsavedChangesBar with Save / Discard.
- Use `Input` and `Select` primitives; do not render raw controls in page code if a primitive exists.
- Required asterisks use `var(--color-required-asterisk)`.
- Inline validation covers provider NPI, contact email, trading partner ID, payer ID, and receiver ID.
- Profile defaults update the draft only; user still saves explicitly.
- Import JSON updates the draft; user saves explicitly.

Tests:

- Blur does not persist.
- Save persists.
- Discard reverts.
- Invalid fields block Save and show inline/banner feedback.
- Import JSON updates draft and preserves ICN.

#### 3. Header

File: `apps/web/src/components/layout/AppShell.tsx`

Current header has:

- App title linking to `/`.
- Templates link.
- Settings link.
- A `?` button linking to `/api/v1/templates/template_spec.md`.

Change:

- Replace `?` with an icon-only Home link when `location.pathname !== '/'`.
- Tooltip content is `Home`.
- Hide the Home icon on `/`.
- Template spec remains available from Templates page via **Open Template Spec**.

In design docs, describe the Home icon as navigation only.

#### 4. Templates page and downloadable templates

Files:

- `apps/web/src/pages/TemplatesPage.tsx`
- `apps/api/templates/template_spec.md`
- `apps/api/templates/eligibility_template.csv`
- `apps/api/app/services/templates.py`

Templates page:

- Required Columns card first.
- Excel/CSV download cards second.
- Remove the `DC Medicaid Rules` card.
- Set Required Columns table page size high enough to avoid pagination.

Downloadable templates:

- Keep importable CSV/XLSX templates header-only unless implementing an exact sample-row exclusion rule.
- Do not add a realistic fake patient row to importable templates; it can be accidentally submitted.
- Make `service_type_code = 30` visible in:
  - Required Columns table example.
  - `template_spec.md` Defaults section.
  - Optional non-imported documentation example.

`template_spec.md` should include:

| Column | Default when omitted |
|---|---|
| `service_type_code` | `30` from `SubmitterConfig.default_service_type_code` |
| `service_date` | No implicit default in the template; generation uses settings only when row value is blank |

If a sample row is later required, implement both:

- exact-row exclusion in `normalize_patient_rows`, and
- tests proving the sample is ignored with a warning.

#### 5. Icons

File: `apps/web/src/components/ui/Icons.tsx`

Material Symbols is optional for Phase 3 and must not block ICN.

If migrating:

- Add `material-symbols` dependency.
- Import outlined CSS once at app boot.
- Preserve named exports (`HomeIcon`, `CheckIcon`, etc.).
- Audit every icon call site. Existing `className="h-4 w-4"` is not a reliable size contract for font icons.
- Prefer token-backed size classes, e.g. `size="sm" | "md" | "lg"` mapped to CSS variables, not inline `fontSize: '20px'`.
- Add icon-size tokens if needed.
- Keep icons `aria-hidden` by default; icon-only parents must have `aria-label`.

Tests:

- Existing call sites render without missing exports.
- Icon-only Home link has an accessible name.
- No design-lint violation from inline raw px.

#### 6. Animations

Files:

- Existing `apps/web/src/components/transitions/RouteTransition.tsx`
- `apps/web/src/components/ui/Banner.tsx`
- `apps/web/src/pages/HomePage.tsx`
- `apps/web/src/pages/PreviewPage.tsx`

Current `RouteTransition` already exists and is wired in `App.tsx`. Do not add a second wrapper. If changing it, update the existing component and docs.

Allowed motion:

- Route transition, token-backed, reduced-motion aware.
- Card/Button hover lifts already token-backed; audit only.
- Form validation icon fade-in, token-backed.
- Banner mount/dismiss if implemented inside the primitive and reduced-motion aware.
- Spinners for async states.

No new decorative motion.

## Phase 4 — Version And Release Metadata

Run after the implementation phases are complete:

```bash
python scripts/bump_version.py 1.1.0
make check-version-sync
make docs-regenerate
make docs-check
```

The bump script updates:

- `VERSION`
- package metadata for the library and API
- `apps/web/package.json`
- `apps/web/package-lock.json`
- README version table
- CHANGELOG release block

Do not hand-edit scattered version strings.

## Files To Modify

| Phase | File | Change |
|---|---|---|
| 1 | `apps/web/src/utils/constants.ts` | ICN null/exhausted behavior and helpers |
| 1 | `apps/web/src/hooks/useSettings.tsx` | ICN readiness, strict ICN parsing, settings JSON parsing |
| 1 | `apps/web/src/pages/SettingsPage.tsx` | Explicit save model and ICN section |
| 1 | `apps/web/src/pages/PreviewPage.tsx` | ICN display, blocking gate, spinner in Process button |
| 1 | `apps/web/src/pages/HomePage.tsx` | Generate readiness includes ICN |
| 1 | `apps/web/src/components/features/ConfigStatusBar.tsx` | Separate provider vs ICN readiness copy |
| 1 | `apps/web/src/services/api.ts` | Call `generate270` only with non-null next ICN |
| 1 | `apps/api/app/schemas/common.py` | Tighten control-number bounds as needed |
| 1 | `apps/api/app/schemas/generate.py` | Require explicit starts for generate requests |
| 1 | `apps/api/app/routers/pipeline.py` | Reject pipeline generation without explicit starts |
| 1 | `apps/api/app/services/generator.py` | Defensive guard against missing starts |
| 1 | Web/API tests | ICN utility, settings hook/page, preview gate, API 422 |
| 2 | `apps/api/app/services/exporter.py` | Errors sheet, structured plan columns, row fill |
| 2 | `apps/api/tests/test_export.py` | Export workbook tests |
| 2 | `apps/web/src/utils/plan.ts` | Plan parsing mirror |
| 2 | Dashboard components/tests | Structured plan columns and search |
| 3 | `apps/web/src/styles/tokens.css` | Mastercard token updates |
| 3 | `docs/design-system.md` | Theme rationale and server Excel tint note |
| 3 | `docs/design-spec.md` | Updated rules; remove stale single-column Settings rule |
| 3 | `docs/ui-components.md` | New/changed primitive APIs |
| 3 | `apps/web/src/components/layout/AppShell.tsx` | Home icon link |
| 3 | `apps/web/src/pages/TemplatesPage.tsx` | Required Columns first, no rules card |
| 3 | `apps/api/templates/template_spec.md` | Defaults section |
| 3 | `apps/api/templates/eligibility_template.csv` | Keep header-only unless exact-row exclusion is added |
| 3 | `apps/api/app/services/templates.py` | Keep generated XLSX header-only unless exact-row exclusion is added |
| 3 optional | `apps/web/src/components/ui/Icons.tsx` | Material Symbols migration |
| 4 | Release-bearing files | Via `scripts/bump_version.py` only |

## Verification

### Phase 1

```bash
cd apps/web && npm run test -- --run src/__tests__/icn-utils.test.ts
cd apps/web && npm run test -- --run src/__tests__/use-settings.test.tsx
cd apps/web && npm run test -- --run src/__tests__/preview-page.test.tsx
cd apps/api && pytest tests/test_generate.py tests/test_pipeline_security.py -x
make typecheck
```

Manual checks:

- Fresh browser with valid provider settings but no ICN cannot generate.
- Settings `#icn` shows last/next ICN and stores `19` as `000000019`.
- Preview sends `000000020` after last submitted `000000019`.
- API `/generate` without control-number starts returns 422.
- Split generation increments ISA13 across archive entries and updates local last ICN to the highest returned.

### Phase 2

```bash
cd apps/api && pytest tests/test_export.py -x -v
cd apps/web && npm run test -- --run src/__tests__/eligibility-dashboard.test.tsx src/__tests__/plan-utils.test.ts
make typecheck
```

Manual checks:

- Workbook sheet order is correct with and without errors.
- `Errors` sheet appears for `error`, `not_found`, or AAA rows.
- `Eligibility Results` has `program_name`, `payer_code`, `category`, `billing_note`.
- Error rows are tinted; non-error rows and header are not.

### Phase 3

```bash
make design-lint
make lint
make typecheck
make test-web
```

Manual checks:

- Settings is 2-column on medium+ viewports and single-column on mobile.
- Required asterisks are red and token-backed.
- Header Home icon appears only away from `/`, has tooltip/accessibility name, and navigates home.
- Templates page has Required Columns first and no Rules card.
- Downloaded templates do not include a submit-ready fake patient row.
- Reduced-motion mode disables route/banner/form animations.

### Phase 4

```bash
python scripts/bump_version.py 1.1.0
make check-version-sync
make docs-regenerate
make docs-check
make check-hygiene
```

## Rollback

Rollback should follow phase boundaries:

- If Phase 1 has an issue, revert the ICN/UI/API changes together. Do not keep UI-only gating without the API guard.
- If Phase 2 has an issue, revert Excel/dashboard changes without touching ICN.
- If Phase 3 has an issue, revert theme/icons/animation/template polish without touching ICN.
- Do not reintroduce `null -> 000000001` fallback behavior.
