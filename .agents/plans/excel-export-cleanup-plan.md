# Excel Export Cleanup Implementation Plan

> **Status:** Draft v1.0, ready for implementation
> **Created:** 2026-05-04
> **Scope:** `/api/v1/export/xlsx` eligibility workbook presentation cleanup
> **Primary files:** `apps/api/app/services/exporter.py`, `apps/api/tests/test_export.py`

## 1. Goal

Clean up the exported Excel workbook so it is easy to scan, minimally colored, and understandable without exposing users to raw API field names or crowded pipe-delimited values.

The export should remain data-complete and automation-safe, but the workbook should be optimized for human review in Excel.

## 2. Current Problem

| Problem | Example | Impact |
|---|---|---|
| Raw API headers | `overall_status`, `status_reason`, `all_eb03_service_types` | Users have to translate implementation names while reviewing data. |
| Dense plan cells | `Medicare Buy-In|710Q|BUY-IN` | Important plan details are visually crowded and harder to sort/filter. |
| Clipped columns | Long status reason and plan values are cut off | Users must manually resize columns every export. |
| Minimal visual hierarchy | Header row looks similar to data rows | Scanning large files requires more effort. |
| Color is not intentional | Only error rows are highlighted today | Color does not consistently guide attention. |

## 3. Design Principles

| Principle | Decision |
|---|---|
| Low cognitive load | Use short, human-readable headers and predictable column order. |
| Minimal color | Use only functional color: neutral headers, soft red error rows, restrained summary accents. |
| No decoration | Avoid charts, merged title banners, gradients, or multi-color status tagging. |
| Preserve traceability | Keep member ID, ST control number, trace number, AAA codes, EB codes, and service types. |
| Keep API unchanged | Change Excel presentation only. Do not rename JSON schema fields. |
| Protect sensitive data | Do not log raw X12 payloads, patient identifiers, or generated workbook contents. |

## 4. Target Workbook Sheets

| Sheet | Purpose | Cleanup |
|---|---|---|
| `Summary` | High-level counts | Apply readable labels, compact widths, bold label column, restrained status accents. |
| `Errors` | Actionable error queue when error/not-found rows exist | Human-readable headers, freeze header, filters, wrapped message/action columns, soft red header accent. |
| `Eligibility Results` | Main export table | Human-readable headers, fixed widths, wrapped text, filters, frozen header, error row highlight. |
| `Parser Issues` | Parser recovery warnings/errors when present | Human-readable headers, freeze header, filters, wrapped message column. |
| Validation export sheets | Separate endpoint | Optional follow-up. Reuse the helper if low-risk, but do not expand scope if it delays eligibility export cleanup. |

## 5. Main Sheet Column Layout

Use this exact order for `Eligibility Results`.

| # | Excel Header | Source / Existing Value | Width | Wrap | Notes |
|---:|---|---|---:|---|---|
| 1 | Member Name | `member_name` | 24 | No | Keep first for user lookup. |
| 2 | Member ID | `member_id` | 16 | No | Store as text to preserve leading zeroes. |
| 3 | Status | `overall_status` | 14 | No | Display title case: `Active`, `Inactive`, `Error`, `Not Found`, `Unknown`. |
| 4 | Status Reason | `status_reason` | 34 | Yes | Primary plain-English outcome. |
| 5 | Program | `program_name` from split plan description | 32 | Yes | Example: `Medicare Buy-In`. |
| 6 | Payer Code | `payer_code` from split plan description | 14 | No | Example: `710Q`. |
| 7 | Coverage Category | `category` from split plan description | 18 | No | Example: `BUY-IN`. |
| 8 | Billing Note | `_billing_note(result)` | 30 | Yes | User-facing operational note. |
| 9 | EB01 Codes | `_all_eb01_codes(result)` | 16 | Yes | Preserve raw eligibility indicators. |
| 10 | Service Types | `_all_eb03_service_types(result)` | 20 | Yes | Preserve EB03 values for audit/filtering. |
| 11 | Benefit Entities | `_benefit_entity_names(result)` | 28 | Yes | Plan/payer entity names. |
| 12 | Contacts | `_contact_summaries(result)` | 34 | Yes | Phone/contact details can be long. |
| 13 | AAA Codes | `_aaa_codes(result)` | 14 | No | Error traceability. |
| 14 | ST Control # | `st_control_number` | 16 | No | X12 traceability. |
| 15 | Trace # | `trace_number` | 22 | No | Primary TRN trace. |

## 6. Minimal Color System

Use no more than these functional colors.

| Use | Hex | Why |
|---|---|---|
| Header fill | `E8EEF7` | Light neutral blue-gray gives structure without visual noise. |
| Header text | `111827` | High contrast, readable. |
| Thin grid/border | `D1D5DB` | Helps separate columns without heavy lines. |
| Error row fill | `FEF2F2` | Keep existing soft red behavior for rows needing action. |
| Error text accent | `991B1B` | Optional for `Errors` sheet header or key cells only. |
| Summary neutral fill | `F9FAFB` | Optional for summary label cells. |

Do not add per-status colors for `Active`, `Inactive`, `Unknown`, etc. A status rainbow adds cognitive load and makes error highlighting less meaningful.

## 7. Implementation Steps

### Step 1: Add Presentation Constants

**What:** Add header labels, widths, and style constants in `apps/api/app/services/exporter.py`.

**Why:** Keeps workbook presentation centralized and avoids repeated magic values.

**How:**

- Add an `ELIGIBILITY_RESULT_COLUMNS` structure with:
  - output header
  - width
  - wrap flag
  - source position or builder key
- Add color constants for header fill, border, font, and summary fill.
- Reuse existing `ERROR_ROW_FILL_RGB`.

### Step 2: Add Shared Sheet Formatting Helpers

**What:** Add helpers for tabular sheet styling.

**Why:** The workbook has multiple table-like sheets and should look consistent.

**How:**

- Add `_style_table_header(sheet)` or expand `_style_header(sheet)` to include:
  - bold header font
  - neutral header fill
  - thin bottom border
  - centered vertical alignment
- Add `_apply_table_layout(sheet, column_specs)` to:
  - set column widths
  - set `wrap_text` by column
  - set `freeze_panes = "A2"`
  - set `auto_filter.ref` when there is at least one header row
  - set vertical alignment to top for data rows
- Keep helpers local to `exporter.py` unless a second module needs them.

### Step 3: Rename Excel Headers Only

**What:** Replace raw snake_case headers with human-readable Excel labels.

**Why:** Users should not need to know the API schema to read the export.

**How:**

- Keep the JSON request schema unchanged.
- Update only the appended worksheet headers.
- Update tests that currently expect raw header names.

### Step 4: Format Status Text for Display

**What:** Display statuses in title case in Excel.

**Why:** `not_found` and `active` are API values; `Not Found` and `Active` are easier to read.

**How:**

- Add `_display_status(value: str | None) -> str`.
- Replace underscores with spaces and title-case known statuses.
- Preserve blank/null values as empty strings.

### Step 5: Preserve Text Identifiers

**What:** Ensure IDs and trace/control numbers are treated as text.

**Why:** Excel may strip leading zeroes or display long numeric identifiers poorly.

**How:**

- Apply text number format (`"@"`) to:
  - `Member ID`
  - `Payer Code`
  - `EB01 Codes`
  - `Service Types`
  - `AAA Codes`
  - `ST Control #`
  - `Trace #`
- Keep values as strings where they are already strings.

### Step 6: Improve Summary and Errors Sheets

**What:** Apply the same low-noise formatting to supporting sheets.

**Why:** Users often open `Summary` first and `Errors` when a problem exists.

**How:**

- `Summary`:
  - Label column width: 18
  - Value column width: 16
  - Bold labels
  - Optional neutral fill on labels only
- `Errors`:
  - Headers: `Member Name`, `Member ID`, `Error Type`, `AAA Code`, `Error Summary`, `Recommended Action`, `Follow-up Action`, `ST Control #`, `Trace #`
  - Wrap `Error Summary` and `Recommended Action`
  - Freeze header and enable filters
  - Use normal white data rows; do not fill every row red because the sheet itself is already error-focused.

### Step 7: Parser Issues Sheet

**What:** Make parser issues readable but secondary.

**Why:** Parser issues are diagnostic and should not dominate the workbook.

**How:**

- Headers: `Transaction #`, `Transaction Control #`, `Segment`, `Location`, `Message`, `Severity`
- Wrap `Message`
- Widths tuned for diagnostic review.
- Use the neutral header fill, not red, unless severity-specific formatting is added later.

### Step 8: Tests

**What:** Extend `apps/api/tests/test_export.py`.

**Why:** Formatting can regress silently because workbook bytes still open successfully.

**How:**

Add or update tests for:

| Test | Assertion |
|---|---|
| Header labels | `Eligibility Results` first row equals the human-readable labels. |
| Plan split | Program, payer code, and coverage category still split correctly. |
| Layout | `freeze_panes == "A2"` and `auto_filter.ref` covers the table. |
| Widths | Key columns have expected widths, especially Program and Status Reason. |
| Wrapping | Long-text columns have `alignment.wrap_text is True`. |
| Error fill | Existing error row fill remains `FEF2F2`. |
| Text IDs | Member ID and trace/control columns use text format. |

### Step 9: Verification

**What:** Run targeted API tests.

**Why:** This is a server-side workbook generation change.

**How:**

```bash
cd apps/api
pytest tests/test_export.py -x
```

If the broader test suite is practical before merge:

```bash
make test-api
```

## 8. Acceptance Criteria

| Area | Criteria |
|---|---|
| Readability | Main sheet uses human-readable headers and no raw snake_case field names. |
| Plan clarity | Pipe-delimited plan data is split into `Program`, `Payer Code`, and `Coverage Category`. |
| Low cognitive load | Color is limited to neutral headers, optional summary label shading, and soft red error rows. |
| Usability | Header row is frozen, filters are enabled, and long text wraps. |
| Layout | Key columns open at readable widths without requiring manual resizing. |
| Traceability | Member ID, payer code, EB codes, AAA codes, ST control number, and trace number remain present. |
| Safety | No raw X12 payloads or patient data are logged. |
| Compatibility | API request/response schemas are unchanged. |
| Tests | `apps/api/tests/test_export.py` covers the formatting and existing workbook behavior. |

## 9. Risks and Trade-offs

| Risk / Trade-off | Decision |
|---|---|
| Human-readable headers could affect users who automate from downloaded Excel files. | Accept for Excel presentation. API JSON remains canonical for automation. |
| Fixed widths may not fit every payer value. | Use conservative widths and wrapping rather than oversized columns. |
| Too much color can distract from error rows. | Use only neutral headers and existing soft red error row fill. |
| Auto-sizing based on every value can be slow on large exports. | Prefer fixed widths per known column. |
| Applying styles to validation exports expands scope. | Treat as optional follow-up unless helper reuse is low-risk. |

## 10. Out of Scope

- Changing API schemas.
- Changing eligibility parsing logic.
- Adding charts, pivot tables, merged report banners, or conditional formatting beyond existing error rows.
- Storing generated workbooks server-side.
- Logging workbook contents, raw X12, member identifiers, or filenames beyond existing sanitized logging patterns.
