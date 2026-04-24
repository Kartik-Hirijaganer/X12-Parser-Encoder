# Gainwell 271 Parser Recovery + Per-Patient Validation

---

## EXECUTIVE SUMMARY

### What the user did
Uploaded the **April 22, 2026 Gainwell 271 response** (paired with a 999 that confirms **153 accepted `ST*271` subscriber transactions**) and saw **only 13 rows** in the dashboard. The user also validated the originating **270** and saw a flat issue list with no per-patient breakdown and no Excel export.

### What is actually happening — two distinct defects
1. **271 parser silently drops 140 of 153 Gainwell transactions (primary defect).** The real failures are concentrated in shared parse-time segment models — not in per-transaction parser files that do not exist in this repo. An empirical run of the current path against [metadata/Upload-271-Response-…](metadata/) produces **13 surviving transactions and 140 collected errors, split 99 `EB` + 41 `NM1`**. The enums live at:
   - [packages/x12-edi-tools/src/x12_edi_tools/models/segments/eb.py:31](packages/x12-edi-tools/src/x12_edi_tools/models/segments/eb.py) — `eligibility_or_benefit_information: EligibilityInfoCode` rejects `R`, `L`, `MC`; `service_type_code: ServiceTypeCode` rejects composite `30^1^35…`.
   - [packages/x12-edi-tools/src/x12_edi_tools/models/segments/nm1.py:28](packages/x12-edi-tools/src/x12_edi_tools/models/segments/nm1.py) — `entity_identifier_code: EntityIdentifierCode` rejects `P5`, `P3`, `1I`.
   - [packages/x12-edi-tools/src/x12_edi_tools/parser/segment_parser.py:107](packages/x12-edi-tools/src/x12_edi_tools/parser/segment_parser.py) — surfaces those model failures as transaction-fatal `ParserComponentError`s; the loop builder at [parser/loop_builder.py](packages/x12-edi-tools/src/x12_edi_tools/parser/loop_builder.py) never sees an `LS / NM1*P5 / PER / LE` sequence because the NM1 fails first.
   Transactions containing any of these get swallowed silently into `ParseResult.errors` rather than surfaced as parser issues on the dashboard.

2. **Validation UI is issue-centric, not patient-centric (secondary defect).** [apps/web/src/pages/ValidationResultPage.tsx](apps/web/src/pages/ValidationResultPage.tsx) renders a flat `IssueTable`. Patients with no local issue are invisible, and no Excel export exists on that page.

### Inbound parsing policy — tolerant-first, classify later
The project adopts this as a standing rule for **all** companion-guide-sensitive fields (e.g. `EB01`, `EB03`, `NM101`, segment-level entity codes, enum-valued code lists): **accept the raw string on inbound parse; re-validate or classify at a later, explicitly-named layer.** Strict enum validation stays for the **encoder / generator / validator** surfaces, so outbound X12 is still conformant. This prevents the recurring pattern of payer-specific one-offs every time a partner emits a valid-per-CG code that does not happen to live in our internal enum. See "Tolerant-first policy" below for the concrete shape.

### Recommended fix — two parallel workstreams, no more
- **Workstream G (Gainwell parser recovery)** — one owned library slice that relaxes inbound segment models, splits repetition-separated composites, and routes `LS / NM1*P5 / PER / LE` into a new `Loop2120C_271`. Then truthful accounting, a 5-way status classifier, and `2120C` projection at the API layer; 5 summary cards, expand block, filters, and a parser-issue banner at the UI layer. This is the **headline fix** and directly answers "13 rows, should be 153."
- **Workstream V (per-patient validation)** — thread `transaction_index` through every `ValidationError`, reshape `/validate/result` from issue-centric to patient-centric, add Excel export. Filter vocabulary stays **`valid / invalid` only** (no cross-stage lifecycle statuses on this page).

**Descoped per reviewer answer:** `999/824` ingestion, `/ack/result` page, lifecycle correlator, and DC Medicaid profile rule hardening (old V1.D). They do not help the "13 vs 153" fix land faster and materially widen scope. Captured under "Descoped / future" at the end of this document for resumption, not as critical-path work.

### Expected outcome for the April 22, 2026 Gainwell file
The three real files are available locally under [metadata/DCTPID000783_270_20260422_000000001.txt](metadata/DCTPID000783_270_20260422_000000001.txt), [metadata/Upload-DCTPID000783-DCMEDICAID-20260422-…-999.edi](metadata/), and [metadata/Upload-271-Response-DCTPID000783-20260422-…-005010X279A1.edi](metadata/). They are PHI-bearing smoke inputs, not committed fixtures. An empirical raw-segment scan (`awk` over the `~` record separator) gives the real-file smoke oracle:

| Metric | Real-file raw scan (smoke-only ground truth) | Before fix (what user sees) | Real-file smoke after fix |
|---|---|---|---|
| `ST*270` transactions submitted | **153** | — | — |
| `AK9` acknowledged transactions | **153 / 153 (`AK9*A`)** | — | — |
| `ST*271` transactions returned | **153** | — | — |
| `source_transaction_count` | 153 | not reported | **153** |
| `parsed_result_count` | 153 | not reported | **153** |
| `parser_issue_count` | 0 | silent (currently 140) | **0** |
| `EB` segments total | 1 151 | — | — |
| `EB03` with `^` repetition | **541 (47 % of EB)** | parser rejects these | parsed |
| `LS`/`LE` pairs (2120C loops) | **932 / 932** | parser rejects these | parsed |
| `NM1*P5` (plan sponsor) | 932 | — | 932 projected |
| `NM1*P3` / `NM1*1I` | 0 in this file | — | 0 projected (parser must still tolerate) |
| `PER` segments | 1 097 | — | 1 097 projected |
| `EB01` = `1` (active) | 500 occurrences | partial | all projected |
| `EB01` = `R` / `B` / `MC` / `L` (supplemental) | 335 / 219 / 72 / 25 | parser rejects | all preserved |
| `AAA*71` (invalid information) | 4 | — | 4 → `error` |
| `AAA*73` (invalid DOB) | 9 | — | 9 → `error` |
| `AAA*75` (subscriber not found) | **0** | — | 0 → `not_found` empty |
| **Expected dashboard summary** | — | 13 rows only | **active ≈ 140, inactive 0, error 13, not_found 0, unknown 0 – 4** |
| Excel export rows | — | 13 (parser row-loss symptom, not an export bug) | **153 once parser is fixed** |

The active/unknown split (`140 / 0` vs `136 / 4`) depends on whether a handful of transactions carry only supplemental `EB01` codes with no `1` anywhere; the classifier handles that deterministically. What is non-negotiable is `source_transaction_count == parsed_result_count == 153` and zero silent drops.

R10 recheck: the local PHI-bearing 271 was re-scanned before closing P7. The raw `AAA` distribution is `AAA*71 = 4`, `AAA*73 = 9`, `AAA*75 = 0`, so the real-file oracle above is correct and the fixture should not be regenerated to remove its synthetic `AAA*75` branch coverage.

The committed redacted fixture is a separate automated regression oracle. It intentionally includes one synthetic `AAA*75` transaction so the `not_found` classifier branch stays covered even though the real April 22 271 has no `AAA*75`.

| Metric | Redacted fixture expectation (automated gate) |
|---|---|
| `ST*271` transactions returned | **153** |
| `source_transaction_count` / `parsed_result_count` | **153 / 153** |
| `parser_issue_count` | **0** |
| `AAA*71` (invalid information) | **4** |
| `AAA*73` (invalid DOB) | **8** |
| `AAA*75` (subscriber not found) | **1** |
| **Expected dashboard summary** | **active 136, inactive 0, error 12, not_found 1, unknown 4** |
| Excel export rows | **153** |

### Scope corrections captured from review
- **Parser recovery is one slice, not three.** Collapsing the previous `G1.A / G1.B / G1.C` into a single owned `P1` task removes fake parallelism across shared files (`eb.py`, `nm1.py`, `segment_parser.py`, `loop_builder.py`). Full-file acceptance against the real 271 is a post-merge gate on `P1`, not a mid-slice assertion.
- **Eligibility export parity is not a separate defect.** [apps/web/src/pages/EligibilityDashboardPage.tsx:36](apps/web/src/pages/EligibilityDashboardPage.tsx) already posts the full `response.results`, and [apps/api/app/services/exporter.py:58](apps/api/app/services/exporter.py) already iterates the full payload. The "13-row export" is a parser row-loss symptom. Export work is therefore limited to **new columns / optional Parser Issues sheet**, not plumbing parity.
- **Accounting mismatch is a 200 with surfaced partial success, not a 500.** The parser already supports `on_error="collect"` at [apps/api/app/services/parser.py:43](apps/api/app/services/parser.py) and has transaction-scoped error envelopes in [packages/x12-edi-tools/src/x12_edi_tools/exceptions.py:36](packages/x12-edi-tools/src/x12_edi_tools/exceptions.py). Return the partial payload plus `parser_issues[]`, emit `parser_accounting_mismatch_total` counter, structured-log the mismatch with the correlation id. Reserve 5xx for server faults.
- **Old V1.D demo target dropped.** The April 22 run through the validator currently yields `153` transactions, `0` parse errors, `0` validation issues. The stale "13 → ~153 issues" target contradicts the scope correction and is removed. Any DC-Medicaid profile hardening becomes future-proofing in the Descoped section.
- **Validation filter stays `valid / invalid`.** The validation page does not adopt the dashboard's cross-stage vocabulary (`Active / Inactive / Errors / Not Found / Unknown`) because those states do not exist on `PatientValidationRow`. If a future lifecycle object is defined, that is a separate plan.

### Status vocabularies (kept deliberately distinct)

**Eligibility dashboard** renders from this set (applied by `_overall_status` in [apps/api/app/services/parser.py](apps/api/app/services/parser.py)):

| Status | When applied |
|---|---|
| `active` | 271 has `EB01` in `{1,2,3,4,5}`. |
| `inactive` | 271 has `EB01` in `{6,7,8}` and no active/error/not_found. |
| `error` | 271 has an `AAA` rejection other than code `75`. |
| `not_found` | 271 has `AAA*75` (carved out from the old `unknown` bucket). |
| `unknown` | 271 has only supplemental `EB01` (`B,F,J,L,N,R,MC,…`) — no coverage signal. |

**Validation page** renders only:

| Status | When applied |
|---|---|
| `valid` | Pre-271: 270 transaction has **zero** error-severity validation issues. Green, reuses the `active` variant in [formatters.ts](apps/web/src/utils/formatters.ts). |
| `invalid` | Pre-271: 270 transaction has ≥1 error-severity issue. Red, reuses the `inactive` variant. |

Both pages share the same `formatStatusLabel` + `statusVariantFromValue` helpers, but each page's filter set only exposes its own vocabulary.

---

## TOLERANT-FIRST INBOUND POLICY

This is the architectural rule the plan commits to — written here once so every downstream task can reference it rather than re-deciding.

1. **Inbound segment models accept `str` for CG-sensitive code fields.** Replace strict `Literal[…]` / `Enum` typing with `str` for `EB01`, `EB03`, `NM101` and any element whose value space the companion guide keeps open. Keep the enum as a **module-level constant** used elsewhere.
2. **Composite elements are split on the interchange repetition separator at parse time.** `EB03` of `30^1^35^47^…` yields `service_type_codes: list[str]` and a back-compat `service_type_code: str | None` equal to the first element. Split happens in segment construction using the `repetition_separator` carried on the tokenizer.
3. **Classification runs later, in a dedicated service layer.** The API parser service [apps/api/app/services/parser.py](apps/api/app/services/parser.py) owns the `active/inactive/error/not_found/unknown` decision. The library never raises on an unknown inbound code; it records it verbatim.
4. **Outbound (encoder / generator) stays strict.** We continue to reject non-enum values when building X12 we emit. That is where strictness protects the user.
5. **Validator remains free to complain.** A `validator/` rule is allowed to flag `EB01=Z9` as non-conformant; that complaint is a `ValidationIssue`, not a parse failure. The parse still succeeds; the patient row still appears; the user decides.

This rule is why the plan has a single `P1` parser-recovery slice instead of three — the change is one coherent policy shift across `eb.py`, `nm1.py`, `segment_parser.py`, and `loop_builder.py`.

---

## ARCHITECTURE DIAGRAM

```
                                           REFERENCE ONLY
                                 metadata/ (user-provided Gainwell 270/271)
                                 docs/full_text.txt (DC Medicaid CG v1.4)
                                 docs/test-files/ (historical 999/824/BRR oracles)
                                                |
                                                v
+=====================================================================================================+
|                                       BROWSER (React + Vite)                                        |
+=====================================================================================================+
|                                                                                                     |
|   /                           /preview                  /validate/result                            |
|   ────────                    ────────                  ─────────────────                           |
|   HomePage                    PreviewPage               ValidationResultPage  (REWORKED)            |
|   Upload 270 or 271 ──▶      Review file      ──▶      ┌───────────────────────────────────┐      |
|                                                         │ Header: Total 153 · Valid / Inval │      |
|                                                         │ Filter: All | Valid | Invalid     │      |
|                                                         ├───────────────────────────────────┤      |
|                                                         │ PatientValidationTable (P6)       │      |
|                                                         ├───────────────────────────────────┤      |
|                                                         │ [Export Excel]  [Download JSON]   │      |
|                                                         └───────────────────────────────────┘      |
|                                                                                                     |
|   /dashboard                                                                                        |
|   ────────                                                                                          |
|   EligibilityDashboardPage (REWORKED)                                                               |
|   ┌───────────────────────────────────────┐                                                         |
|   │ ⚠ Parser Issues: n (banner P5.B)      │                                                         |
|   ├───────────────────────────────────────┤                                                         |
|   │ 5 cards (P5.A):                       │                                                         |
|   │  Active │ Inactive │ Errors │ NotFnd  │                                                         |
|   │  Unknown                              │                                                         |
|   ├───────────────────────────────────────┤                                                         |
|   │ Filter: All/Active/.../Unknown (P5.D) │                                                         |
|   │ Search: name/id/plan/reason/trace     │                                                         |
|   ├───────────────────────────────────────┤                                                         |
|   │ Row table (P5.C): expand → status_    │                                                         |
|   │  reason + 2120C entities + contacts   │                                                         |
|   ├───────────────────────────────────────┤                                                         |
|   │ [Export Excel] — full response always │                                                         |
|   └───────────────────────────────────────┘                                                         |
+=====================================================================================================+
                                               │
                                               │ HTTPS · correlation-id
                                               ▼
+=====================================================================================================+
|                                       FastAPI BACKEND                                               |
+=====================================================================================================+
|                                                                                                     |
|   routers/validate.py        routers/parse.py         routers/export.py                             |
|        │                          │                        │                                        |
|        ▼                          ▼                        ▼                                        |
|   services/validator.py      services/parser.py      services/exporter.py                           |
|   (P4 wiring)                (P3)                    (P3.C: columns + optional Parser Issues sheet) |
|        │                          │                        │                                        |
|        ├─parse()─▶ Interchange    ├─parse() collect ─▶     ├─build_validation_workbook_bytes (P4.C) |
|        │                          │  interchange + errors  ├─build_eligibility_workbook_bytes       |
|        ├─validate() ─▶ issues     ├─classify + project ─▶  │   (+ Parser Issues sheet when          |
|        │                          │  5 statuses,           │    parser_issue_count > 0)             |
|        ├─ NEW validation_         │  status_reason,                                                  |
|        │  projector.project_      │  2120C entities                                                  |
|        │  patient_rows() (P4.B)   │  accounting reconciliation                                      |
|        │                          │  → partial response + parser_issues[] + counter  (NOT 500)      |
|        ▼                          ▼                                                                 |
|   ValidateResponse {        ParseResponse {                                                         |
|      summary,                  source_transaction_count,    # NEW P3.A                              |
|      patients[],               parsed_result_count,         # NEW P3.A                              |
|      issues[],                 parser_issue_count,          # NEW P3.A                              |
|      is_valid, …               parser_issues[],             # NEW P3.A                              |
|   }                            transaction_count  (alias, deprecated),                              |
|   (P4.A)                       summary{active,inactive,error,not_found,unknown},                    |
|                                results[ { …, status_reason, st_control_number, trace_number,       |
|                                           eligibility_segments[{eligibility_code,                   |
|                                             service_type_code, service_type_codes[]}],             |
|                                           benefit_entities[{entity_identifier_code, name,          |
|                                             contacts[]}],  aaa_errors[] } ]                        |
|                                }                                                                    |
+=====================================================================================================+
                                               │
                                               ▼
+=====================================================================================================+
|                        Python library — x12_edi_tools (pure, framework-agnostic)                    |
+=====================================================================================================+
|                                                                                                     |
|   parser/segment_parser.py, parser/loop_builder.py   models/segments/eb.py, nm1.py                  |
|    P1 — tolerant-first inbound policy:                ─ EB01 / NM101 / entity codes: str            |
|     ─ relax enums to str on inbound path              ─ service_type_codes: list[str] (split on     |
|     ─ split EB03 on repetition separator                interchange repetition separator)          |
|     ─ route LS / NM1*P3|P5|1I / PER* / LE into new                                                  |
|       Loop2120C_271                                  validator/                                     |
|                                                       P2 — thread transaction_index +              |
|   models/loops/loop_2120c_271.py (NEW P1)              transaction_control_number through every    |
|    ─ LSSegment, NM1Segment, list[PERSegment], LE       ValidationError                             |
|    ─ carried inside loop_2110c.loop_2120c[]                                                         |
|                                                                                                    |
+=====================================================================================================+
```

---

## EXECUTION STRATEGY

Work is organised as one linear table in the same shape as the reference: a single Phase column, a human sentence of what the agent actually does, the **main write scope** (files/directories touched — this is what gates collisions), an explicit `Depends on` column, a recommended owner, and a demoable artefact. Phases inside the same "Depends on" row are parallel-safe.

### 3.4 Execution strategy table

| Phase | What the agent does | Main write scope | Depends on | Recommended agent | Demo |
|---|---|---|---|---|---|
| **P0** | Lock parser-recovery fixture harness + contract freeze: redacted Gainwell fixture under `tests/fixtures/`, response-contract docstring, metric name registry for `parser_accounting_mismatch_total`. No production code edits. | `packages/x12-edi-tools/tests/fixtures/gainwell_271_redacted.edi` (new), `docs/plans/gainwell-271-parser-recovery-and-validation.md` (this file), `apps/api/app/core/metrics.py` (registration only) | — | **Integrator / principal backend** | Redacted fixture committed; `pytest tests/fixtures` import-green; metric name visible in `/metrics`. |
| **P1** | Parser-recovery slice (single owned library change). Relax inbound enum typing on `EB01`, `EB03`, `NM101`; split `EB03` on repetition separator; add `Loop2120C_271` and route `LS / NM1*P3\|P5\|1I / PER* / LE`. Keep outbound encoder enums strict. Tests: fixture parses with `len(transactions) == 153` and zero collected errors on the redacted corpus. | `packages/x12-edi-tools/src/x12_edi_tools/models/segments/eb.py`, `.../models/segments/nm1.py`, `.../models/loops/loop_2120c_271.py` (new), `.../models/loops/loop_2110c.py`, `.../parser/segment_parser.py`, `.../parser/loop_builder.py`, `.../encoder/transaction_271.py` (round-trip), tests under `packages/x12-edi-tools/tests/parser/` and `tests/encoder/` | P0 | **Library engineer (A)** | `make test-lib` green; redacted fixture parses 153/153 with 0 errors; EB01 ∈ {R,L,MC,B}, composite EB03, `NM1*P5` in 2120C all covered. |
| **P2** | Validator thread-through: add `transaction_index` + `transaction_control_number` to `ValidationError`; populate in every SNIP rule that iterates transactions. Envelope-level rules leave them `None`. | `packages/x12-edi-tools/src/x12_edi_tools/validator/base.py`, `.../validator/snip1.py` `.../snip2.py` `.../snip3.py` `.../snip4.py` `.../snip5.py`, `.../validator/x12_validator.py`, tests under `packages/x12-edi-tools/tests/validator/` | P0 | **Library engineer (B)** | Existing validator tests stay green; new `test_transaction_index.py` proves issue → `st02` mapping on a 3-transaction fixture. |
| **P3** | API parse layer: `ParseResponse.source_transaction_count / parsed_result_count / parser_issue_count / parser_issues[]`; 5-way status classifier with `status_reason`, `st_control_number`, `trace_number`; project `2120C` into `BenefitEntity{entity_identifier_code,name,contacts[]}`; reconciliation guard emits `parser_accounting_mismatch_total` and attaches `parser_issues[]` to the **200** response — **never 500** on mismatch. Optional `Parser Issues` sheet in `build_eligibility_workbook_bytes` when `parser_issue_count > 0`. Keep `transaction_count` as a deprecated alias. | `apps/api/app/schemas/parse.py`, `apps/api/app/schemas/common.py`, `apps/api/app/services/parser.py`, `apps/api/app/services/exporter.py`, `apps/api/tests/test_parse*.py` | P1 | **API engineer** | `curl POST /api/v1/parse` on the real 271 returns `source_transaction_count: 153`, `parsed_result_count: 153`, `parser_issue_count: 0`; summary `active ≈ 140, error = 13, inactive/not_found/unknown ≈ 0`; expanded row carries 2120C entity + PER contacts; mismatch harness returns 200 with counter increment. |
| **P4** | API validate layer: `ValidateResponse.patients[]` + `summary{total_patients, valid_patients, invalid_patients}` retaining `issues[]` for back-compat; new `validation_projector.project_patient_rows()`; `/export/validation/xlsx` endpoint emitting 3 sheets (Summary, Per-Patient, Issues). | `apps/api/app/schemas/validate.py`, `apps/api/app/schemas/common.py`, `apps/api/app/services/validation_projector.py` (new), `apps/api/app/services/validator.py`, `apps/api/app/services/exporter.py` (validation workbook function), `apps/api/app/routers/export.py`, `apps/api/tests/test_validate*.py`, `apps/api/tests/test_export*.py` | P2 | **API engineer** | `POST /api/v1/validate` on the real 270 returns `summary.total_patients == 153`; workbook export has Summary / Per-Patient / Issues sheets with matching row counts. |
| **P5** | Frontend eligibility dashboard: 5 summary cards (Active / Inactive / Errors / Not Found / Unknown), parser-issue banner when `parser_issue_count > 0`, expandable row with `status_reason` + 2120C entity/contact block, filter includes 5 statuses + search over `status_reason` and `trace_number`. Export button already passes the full payload; include `parser_issues` in request body. | `apps/web/src/components/features/EligibilityDashboard.tsx` (split into `DashboardSummary`, `DashboardFilterBar`, `DashboardTable`, `DashboardRow` at the start of this phase), `apps/web/src/pages/EligibilityDashboardPage.tsx`, `apps/web/src/services/api.ts`, `apps/web/src/types/api.ts`, `apps/web/src/utils/formatters.ts`, `apps/web/src/__tests__/eligibility-dashboard*.test.tsx` | P3 | **Web UI agent (A)** | Manual smoke on [metadata/Upload-271-Response-…](metadata/): 5 cards; 153 rows; filter narrowing works; banner absent (parser_issue_count == 0); expand shows `Coverage on file` + plan-sponsor name/phone. |
| **P6** | Frontend validation page: header cards (Total / Valid / Invalid), `PatientValidationTable` + `PatientIssueDrawer`, `Tabs`-style `Patients \| Issues \| Summary`, status filter **`All / Valid / Invalid` only** (no cross-stage states), search by member, Export-Excel wired to `/export/validation/xlsx`. | `apps/web/src/components/features/PatientValidationTable.tsx` (new), `.../PatientIssueDrawer.tsx` (new), `apps/web/src/pages/ValidationResultPage.tsx`, `apps/web/src/utils/formatters.ts` (`valid`/`invalid` arms only), `apps/web/src/services/api.ts`, `apps/web/src/__tests__/patient-validation-table.test.tsx`, `validation-result-page.test.tsx` | P4 | **Web UI agent (B)** | Manual smoke on [metadata/DCTPID000783_270_…](metadata/): header shows 153 / 153 / 0; per-patient table paginates; row drawer opens with issue detail; Excel export yields 3-sheet workbook. |
| **P7** | Cross-layer regression + release gates: expand the redacted fixture to cover composite EB03, 2120C NM1/PER, supplemental EB01, AAA 71/73/75, export row parity; API test asserts `source_transaction_count == parsed_result_count`; UI test asserts filter + export invariant. Gate `make lint`, `make typecheck`, `make test`, `make coverage` (lib ≥ 95 %, api ≥ 85 %), `make docs` regenerated OpenAPI. | `packages/x12-edi-tools/tests/fixtures/gainwell_271_redacted.edi` (expand), `packages/x12-edi-tools/tests/parser/test_gainwell_271_regression.py` (new), `apps/api/tests/test_parse_gainwell_regression.py` (new), `apps/web/src/__tests__/gainwell-regression.test.tsx` (new), `docs/api/openapi.yaml` (regenerated) | P5, P6 | **Integrator / principal backend** | All four make targets green from repo root; OpenAPI diff reviewed; fixture-based regression suite fails if `parsed_result_count < source_transaction_count`. |

### Collision rules (read before claiming a phase)
- **P1 is single-owner by design.** `eb.py`, `nm1.py`, `segment_parser.py`, and `loop_builder.py` are all co-edited. Do not split P1 across agents — the previous attempt (`G1.A/B/C`) produced collisions across the same files and was rolled back into this phase per review.
- **`apps/api/app/schemas/common.py` is single-writer.** P3 and P4 both touch it; sequence P3 → P4, or have one agent own `common.py` and send patches.
- **`apps/web/src/utils/formatters.ts` is shared** between P5 and P6. P6 adds only the `valid`/`invalid` switch arms; P5 reads existing arms plus `not_found`. No actual overlap — noted for awareness.
- **`EligibilityDashboard.tsx` is the hottest file on Wave 3.** P5 begins by splitting it into `DashboardSummary / DashboardFilterBar / DashboardTable / DashboardRow`; every subsequent edit lands in exactly one child component.

### Recommended headcount
Two library engineers drive P1 and P2 in parallel; one API engineer runs P3 then P4; two UI engineers take P5 and P6 in parallel; the integrator handles P0 and P7. With that headcount the sequence collapses to **P0 → (P1 ‖ P2) → (P3 → P4) → (P5 ‖ P6) → P7**, four serial wall-clock stages instead of seven.

---

## PHASED IMPLEMENTATION PLAN

Each phase below is the detailed contract backing the table above. Use the phase IDs exactly — they are how agents claim work.

---

### P0 — Contract freeze and redacted fixture harness

**Goal:** Before any production code changes, establish the oracle and contract so every subsequent phase can assert against the same numbers.

**Files:**
- `packages/x12-edi-tools/tests/fixtures/gainwell_271_redacted.edi` (**new**) — hand-crafted synthetic fixture reproducing the real file's structural patterns: composite `EB03` with `^` repetition, `LS … NM1*P5 … PER … LE` 2120C loops, `EB01` ∈ {R,L,MC,B}, AAA 71/73/75 mix, transactions with only supplemental EB. No real PHI — `make check-hygiene` must stay green.
- `apps/api/app/core/metrics.py` — register `parser_accounting_mismatch_total` counter (name only, no increment sites yet).
- This plan — keep the scope corrections captured here as the single source of truth.

**Blocker:** `metadata/` must contain the three real files and `make check-hygiene` must still pass (those files are `.gitignore`d by `make check-hygiene`).

**Tests:** `pytest --collect-only tests/fixtures` imports clean; `/metrics` exposes the new counter at zero.

**Demo:** `ls -la packages/x12-edi-tools/tests/fixtures/gainwell_271_redacted.edi` and a `curl -s http://localhost:8000/metrics | grep parser_accounting_mismatch_total` returning the registered name.

---

### P1 — Parser recovery slice (single owner)

**Goal:** The shared 271 parse path accepts every structural construct in the real Gainwell file. One owner; one merge; the tolerant-first policy is applied consistently across models and parser in the same commit chain.

**Work contents (in one slice):**

1. **Relax inbound enums to `str`** on the parse path:
   - [models/segments/eb.py:31](packages/x12-edi-tools/src/x12_edi_tools/models/segments/eb.py) — `eligibility_or_benefit_information: str`. Keep `EligibilityInfoCode` enum as a module constant for the encoder/validator.
   - [models/segments/nm1.py:28](packages/x12-edi-tools/src/x12_edi_tools/models/segments/nm1.py) — `entity_identifier_code: str`. Likewise keep `EntityIdentifierCode` as a constant. Adjust downstream comparisons in `loop_builder.py` that do `== EntityIdentifierCode.PAYER` to compare `.value` or normalise.
2. **Split composite `EB03` on the interchange repetition separator** at segment construction:
   - Extend the tokenizer so the repetition separator (read from `ISA11`) is reachable during segment_parser construction.
   - `EBSegment` gains `service_type_codes: list[str] = Field(default_factory=list)`; `service_type_code` (existing singular) becomes the first element for back-compat.
3. **Add `Loop2120C_271` and route its segments** in [parser/loop_builder.py](packages/x12-edi-tools/src/x12_edi_tools/parser/loop_builder.py):
   - `models/loops/loop_2120c_271.py` (**new**):
     ```python
     class Loop2120C_271(X12BaseModel):
         ls: LSSegment
         nm1: NM1Segment                 # entity_identifier_code in {P3, P5, 1I, …} (now str)
         per_segments: list[PERSegment] = Field(default_factory=list)   # cap at 3 per CG §A.1
         le: LESegment
     ```
   - `models/loops/loop_2110c.py` gains `loop_2120c: list[Loop2120C_271] = Field(default_factory=list)`.
   - In `loop_builder.py` 271 branch (current state machine around line 585), on `LS` open a 2120C; append subsequent `NM1` / `PER` into it; close on `LE`. Cap PER silently at 3 — do not raise.
4. **Encoder round-trip** in `encoder/transaction_271.py`: when encoding a 2110C with `loop_2120c`, emit `LS … NM1 … PER* … LE` in order so parse → encode → parse preserves the shape.

**Tests:**
- `packages/x12-edi-tools/tests/parser/test_gainwell_271_parser_recovery.py` — aggregate parser-recovery coverage: `EB*R*IND`, `EB*L*IND`, `EB*MC*IND`, `EB*B*IND` parse successfully with raw values preserved; single, 3-element, and 10-element `EB03` composites populate `service_type_codes`; `P5`, `P3`, and `1I` 2120C entity codes route correctly; 4-PER input is capped at 3; the P0 redacted fixture parses to **153 transactions with 0 collected errors**.
- `packages/x12-edi-tools/tests/encoder/test_gainwell_271_roundtrip.py` — parse → encode → parse preserves the Gainwell fixture shape, while outbound encoding remains strict for unknown `EB01`, `NM101`, and `EB03` service type codes.

**Demo:** `python -c "from x12_edi_tools.parser import parse; r = parse(open('metadata/Upload-271-Response-DCTPID000783-20260422-4251655-005010X279A1.edi').read(), strict=False, on_error='collect'); print(len(r.interchange.functional_groups[0].transactions), len(r.errors))"` prints `153 0`. (Do not commit `metadata/`.)

---

### P2 — Validator transaction-index thread-through

**Goal:** Every `ValidationError` whose rule iterates transactions carries `transaction_index` + `transaction_control_number`, so the API can bucket issues per patient.

**Files:**
- [packages/x12-edi-tools/src/x12_edi_tools/validator/base.py](packages/x12-edi-tools/src/x12_edi_tools/validator/base.py) — add optional fields to `ValidationError`:
  ```python
  transaction_index: int | None = None
  transaction_control_number: str | None = None
  ```
- `validator/x12_validator.py` — pass the index into rule closures when iterating transactions.
- `validator/snip1.py` … `validator/snip5.py` — set both fields on every yielded error from transaction-scope rules. Envelope-scope rules leave them `None`.

**Tests:** `packages/x12-edi-tools/tests/validator/test_transaction_index.py` — 3-transaction 270 with a seeded error in transaction 2; assert `issues[0].transaction_index == 1` and `transaction_control_number` matches `ST02`.

**Demo:** Existing validator tests stay green; new test passes.

---

### P3 — API parse layer: accounting, classifier, 2120C projection, surfaced mismatch

**Goal:** The parse endpoint returns truthful accounting, a 5-way status per patient, projected 2120C entities, and — critically — surfaces mismatches as partial success instead of 500.

**Files:**
- [apps/api/app/schemas/parse.py](apps/api/app/schemas/parse.py):
  ```python
  class ParserIssue(ApiModel):
      transaction_index: int | None
      transaction_control_number: str | None
      segment_id: str | None
      location: str | None
      message: str
      severity: Literal["error", "warning"] = "error"

  class ParseResponse(ApiModel):
      filename: str
      payer_name: str | None = None
      source_transaction_count: int       # NEW
      parsed_result_count: int            # NEW
      parser_issue_count: int             # NEW
      parser_issues: list[ParserIssue] = Field(default_factory=list)
      transaction_count: int              # deprecated alias of source_transaction_count
      summary: EligibilitySummary         # now with not_found in addition to unknown
      results: list[EligibilityResult]
  ```
- [apps/api/app/schemas/common.py](apps/api/app/schemas/common.py) — add `not_found: int` to `EligibilitySummary`; extend `BenefitEntity` with `entity_identifier_code`, `name`, `contacts: list[str]`; extend `EligibilityResult` with `status_reason`, `st_control_number`, `trace_number`, and `eligibility_segments[*].service_type_codes`.
- [apps/api/app/services/parser.py](apps/api/app/services/parser.py):
  - Replace `_overall_status` with a 5-way classifier returning `(status, status_reason)`:
    ```python
    def _overall_status(eb_segments, aaa_errors) -> tuple[str, str]:
        if any(a.code == "75" for a in aaa_errors):
            return "not_found", "Subscriber not found"
        if aaa_errors:
            return "error", _aaa_reason(aaa_errors[0].code)
        codes = {s.eligibility_code for s in eb_segments}
        if codes & _ACTIVE_CODES:       return "active", "Coverage on file"
        if codes & _INACTIVE_CODES:     return "inactive", "Coverage terminated"
        if codes & _SUPPLEMENTAL_CODES: return "unknown", "Additional payer information only"
        return "unknown", "No coverage signal"
    ```
  - Populate `status_reason`, `st_control_number` (from `transaction.st.st02`), `trace_number` (first `TRN`).
  - Project `2110C.loop_2120c[*]` into `BenefitEntity` with name + `PER` contacts.
  - **Surfaced mismatch handling** — replace the current "raise on empty results" branch:
    ```python
    parser_issues = _collect_parser_issues(parse_result.errors)
    if len(results) + len(parser_issues) != source_transaction_count:
        parser_accounting_mismatch_total.labels(path=metrics_path).inc()
        logger.warning(
            "parser_accounting_mismatch",
            extra={"correlation_id": correlation_id,
                   "source": source_transaction_count,
                   "parsed": len(results),
                   "issues": len(parser_issues)},
        )
        # Do NOT raise. Return the partial response with parser_issues[] so the
        # user still sees what parsed and can diagnose the rest.
    return ParseResponse(...)
    ```
    The only 4xx/5xx cases remain: malformed envelope → 400 (existing `X12ParseError`); true server fault → 500. An accounting-count mismatch is a surfaceable partial, not a fault.
- [apps/api/app/services/exporter.py](apps/api/app/services/exporter.py) — add new columns to `build_eligibility_workbook_bytes`: `status_reason`, `primary_plan_summary`, `all_eb01_codes`, `all_eb03_service_types`, `benefit_entity_names`, `contact_summaries`, `aaa_codes`, `st_control_number`, `primary_trn`. Add a conditional `Parser Issues` sheet when `parser_issue_count > 0`. Keep the existing full-payload iteration untouched — it is already correct.

**Tests:**
- `apps/api/tests/test_parse_status_classifier.py` — table-driven: AAA 75 → `not_found`, AAA 72 → `error`, EB 1 → `active`, EB 6 → `inactive`, only-supplemental EB → `unknown` with reason.
- `apps/api/tests/test_parse_reconciliation.py` — synthesise a mismatch harness; assert **200** response, `parser_issues[]` populated, counter incremented, no 500.
- `apps/api/tests/test_parse_2120c.py` — P5 entity + 2 PER → one `BenefitEntity` with 2 contacts.
- `apps/api/tests/test_export.py` — parser-issues fixture emits the sheet; clean payload omits it.

**Demo:** `POST /api/v1/parse` on [metadata/Upload-271-Response-…](metadata/) returns `source_transaction_count = parsed_result_count = 153`, `parser_issue_count = 0`, summary `{active ≈ 140, inactive 0, error 13, not_found 0, unknown 0–4}`.

---

### P4 — API validate layer: per-patient projection + Excel export

**Goal:** The validate endpoint returns a per-patient row list and the UI can export a 3-sheet workbook.

**Files:**
- [apps/api/app/schemas/validate.py](apps/api/app/schemas/validate.py):
  ```python
  class ValidationSummary(ApiModel):
      total_patients: int
      valid_patients: int
      invalid_patients: int

  class PatientValidationRow(ApiModel):
      index: int
      transaction_control_number: str | None
      member_name: str
      member_id: str | None
      service_date: str | None
      status: Literal["valid", "invalid"]
      error_count: int
      warning_count: int
      issues: list[ValidationIssue] = Field(default_factory=list)

  class ValidateResponse(ApiModel):
      filename: str
      is_valid: bool
      error_count: int
      warning_count: int
      issues: list[ValidationIssue]                                           # kept (back-compat)
      patients: list[PatientValidationRow] = Field(default_factory=list)      # NEW
      summary: ValidationSummary | None = None                                # NEW
  ```
- `apps/api/app/services/validation_projector.py` (**new**) — `project_patient_rows(interchange, issues)` buckets issues by `transaction_index` and iterates `transaction.loop_2000a.loop_2000b[*].loop_2000c[*]` to emit one `PatientValidationRow` per subscriber.
- `apps/api/app/services/validator.py` — after building issues, call the projector, compute `ValidationSummary`, attach both.
- `apps/api/app/services/exporter.py` — `build_validation_workbook_bytes(payload)` with three sheets: Summary, Per-Patient, Issues.
- `apps/api/app/routers/export.py` — `POST /export/validation/xlsx`.

**Tests:**
- `apps/api/tests/test_validate_schema.py` — Pydantic round-trip with a 3-patient fixture.
- `apps/api/tests/test_validate.py` — 3-transaction 270 with one error in transaction 2; assert `patients[1].status == "invalid"`.
- `apps/api/tests/test_export.py` — POST the 3-row fixture; `openpyxl` loads bytes with matching sheet names and row counts.

**Demo:** `POST /api/v1/validate` on [metadata/DCTPID000783_270_…](metadata/) returns `summary.total_patients == 153`, `valid_patients == 153`, `invalid_patients == 0` (given the April 22 generator passes current profile rules).

---

### P5 — Frontend eligibility dashboard

**Goal:** The dashboard reflects the new five-status vocabulary, surfaces parser issues, and expands rows to show 2120C entities.

**Files (start this phase by splitting the current monolith):**
- `apps/web/src/components/features/EligibilityDashboard.tsx` → split into:
  - `DashboardSummary.tsx` (5 cards from `summary.{active, inactive, error, not_found, unknown}`),
  - `DashboardFilterBar.tsx` (`FILTER_OPTIONS = [All, Active, Inactive, Errors, Not Found, Unknown]`; search matches `member_name`, `member_id`, plan summary, `status_reason`, `trace_number`),
  - `DashboardTable.tsx` + `DashboardRow.tsx` (expand shows `status_reason` prominently plus `BenefitEntity[]` grouped by `entity_identifier_code` — P3 Primary Payer, P5 Plan Sponsor, 1I Preferred Provider — with `contacts[]` sub-list).
- [apps/web/src/pages/EligibilityDashboardPage.tsx](apps/web/src/pages/EligibilityDashboardPage.tsx):
  - Top of page: `<Banner variant="warning">` when `response.parser_issue_count > 0` (zero otherwise — no banner).
  - `handleExport` already passes the full `response.results`; extend the payload to include `parser_issues`.
- `apps/web/src/services/api.ts` — update `ExportWorkbookRequest` TS to include `parser_issues`.
- `apps/web/src/types/api.ts` — add `not_found: number` to `EligibilitySummary`; add new fields to `EligibilityResult`.
- `apps/web/src/utils/formatters.ts` — no new switch arms needed for the dashboard; validate existing arms render `not_found` label.

**Tests:**
- `apps/web/src/__tests__/eligibility-dashboard.test.tsx` — 5 cards render for a fixture with all non-zero; filter narrowing on each of the 5 statuses returns the expected subset; expand renders P5 + 2 contacts.
- `apps/web/src/__tests__/eligibility-dashboard-page.test.tsx` — zero issues → no banner; non-zero → banner with count; apply filter → export payload still carries the full row set.

**Demo:** `npm run dev`, upload the April 22 271, 5 cards + 153 rows + no banner + expandable row shows plan-sponsor name/phone.

---

### P6 — Frontend validation page

**Goal:** The validation page becomes patient-centric, filter vocabulary stays `All / Valid / Invalid`, Excel export works end-to-end.

**Files:**
- `apps/web/src/components/features/PatientValidationTable.tsx` (**new**) — columns `#, Member, Member ID, Service Date, Status, Errors, Warnings`. Status cell uses `<Badge variant={statusVariantFromValue(status)}>{formatStatusLabel(status)}</Badge>`. Page size 25. `onSelect(row)` on row click.
- `apps/web/src/components/features/PatientIssueDrawer.tsx` (**new**) — `Card` below the table; reuses existing `IssueTable` internally with the selected row's `issues[]`.
- [apps/web/src/pages/ValidationResultPage.tsx](apps/web/src/pages/ValidationResultPage.tsx):
  - Header: `Total / Valid / Invalid` metrics.
  - Tabs: `Patients` (default) | `Issues` | `Summary`.
  - Status filter **options restricted to `All / Valid / Invalid`** — no cross-stage statuses. If a future lifecycle page wants `Active / Inactive / Not Found`, it is a separate page, not a new filter here.
  - Search input on member name / ID.
  - Drawer rendered below the table when a row is selected.
  - Buttons: `Export Excel` (wired to `/export/validation/xlsx`), `Download Report (JSON)`.
- `apps/web/src/utils/formatters.ts` — add only `valid` / `invalid` switch arms; reuse `active` / `inactive` variants (green / red).
- `apps/web/src/services/api.ts` — `exportValidationWorkbook(payload): Promise<Blob>` via `requestBlob('/export/validation/xlsx', …)`.

**Tests:**
- `apps/web/src/__tests__/formatters.test.ts` — `formatStatusLabel('valid') === 'Valid'`, `statusVariantFromValue('invalid') === 'inactive'`.
- `apps/web/src/__tests__/patient-validation-table.test.tsx` — 5-row fixture; status variants correct; click row → `onSelect` called.
- `apps/web/src/__tests__/validation-result-page.test.tsx` — 5-patient fixture; filter to `Invalid` narrows rows; clicking a row opens the drawer; stubbed `requestBlob` sees the correct payload on Export click.

**Demo:** `npm run dev`, validate the April 22 270, header shows `153 / 153 / 0`, filter to `Invalid` yields an empty state, Export Excel downloads a 3-sheet workbook.

---

### P7 — Cross-layer regression + release gates

**Goal:** Lock the fix so silent row loss cannot recur, and gate release on the standard make targets.

**Files:**
- `packages/x12-edi-tools/tests/fixtures/gainwell_271_redacted.edi` — expanded to cover every construct from the real file.
- `packages/x12-edi-tools/tests/parser/test_gainwell_271_regression.py` (**new**) — parse fixture → 1 result per `ST*271`, zero collected errors.
- `apps/api/tests/test_parse_gainwell_regression.py` (**new**) — POST fixture → `source_transaction_count == parsed_result_count`, summary matches expected counts, `parser_issue_count == 0`.
- `apps/api/tests/test_parse_gainwell_metadata_smoke.py` (**new**) — opt-in `metadata_smoke` test. When `X12_METADATA_DIR` points at the local PHI-bearing `metadata/` directory, POST the real April 22 271 and assert the real-file smoke oracle. Skipped in CI when the file is absent.
- `apps/web/src/components/features/FilterBar.tsx` (**new**) — shared filter/search/action layout used by the eligibility dashboard and validation patients tab.
- `apps/web/src/__tests__/gainwell-regression.test.tsx` (**new**) — mount with fixture API response; 5 cards; expected row counts per filter; export payload contains all rows.
- `docs/api/openapi.yaml` — regenerated.

**Under no circumstance commit real PHI to `packages/x12-edi-tools/tests/fixtures/`.** Redact all names, member IDs, DOBs, and addresses (`STEWART, PATRICIA` → `LASTNAME01, FIRSTNAME01`, etc.).

---

## VERIFICATION

After each phase, from the repo root:

```bash
make lint            # ruff + eslint clean
make typecheck       # mypy strict + tsc --noEmit
make test            # all three test suites
make coverage        # lib ≥ 95 %, api ≥ 85 %
```

After P3 / P4 (API contract change):

```bash
make docs            # revalidates docs/api/openapi.yaml + ERD
```

**Manual end-to-end smoke** (after P6):

```bash
cd apps/api && uvicorn app.main:app --reload      # Terminal A
cd apps/web && npm run dev                        # Terminal B
# Browser: http://localhost:5173

# 1. Upload metadata/DCTPID000783_270_20260422_000000001.txt
#    → /validate/result: Total 153 · Valid 153 · Invalid 0
#      (April 22 generator is clean against the current profile)
#    → Export Excel returns a 3-sheet workbook with 153 Per-Patient rows.
# 2. Upload metadata/Upload-271-Response-...-005010X279A1.edi
#    → /dashboard: 5 cards; Active ≈ 140, Inactive 0, Errors 13, Not Found 0, Unknown 0–4
#    → parser_issue_count == 0; no warning banner
#    → Expand an active row: status_reason "Coverage on file" + 2120C plan-sponsor block with PER contacts
#    → Expand an AAA*71 or AAA*73 row: status_reason derived from the AAA code
#    → Export Excel: 153 rows; Parser Issues sheet absent
#    → Optional smoke: cd apps/api && X12_METADATA_DIR=../../metadata pytest tests/test_parse_gainwell_metadata_smoke.py -m metadata_smoke
# 3. Simulate mismatch (unit-test harness only — do not mangle metadata/):
#    → Response is 200 with partial results + parser_issues[]; counter increments
```

**MCP code-review-graph checks** before each gate:

- Before P3: `get_impact_radius` on changed `x12_edi_tools` symbols — downstream should be only `apps/api/app/services/parser.py` + tests.
- Before P5: `get_affected_flows` on `parse`, `validate`, `export` — confirm the flows match the table.
- Before P7: `query_graph tests_for` on every changed UI component — confirm new tests are linked.

---

## OUT OF SCOPE / DELIBERATE NON-GOALS

- **270 generator changes.** The April 22, 2026 999 accepted all 153 transactions — the generator is healthy.
- **Persistent storage / DB / queue.** CLAUDE.md statelessness invariant holds.
- **Auto-submission to Gainwell.** The app stays a workbench.
- **New design tokens.** Unless P5 exposes a state not covered by existing variants.
- **Committing raw `metadata/` files or real-PHI 999 / 824.** `make check-hygiene` will fail on any such file. Redact before committing any derivative fixture in P7.
- **Promoting `TYPE_CHECKING`-only symbols** (Phase 7 of the broader 837/835 plan) — separate work item.

---

## DESCOPED / FUTURE

Captured per reviewer answer that these are not required for the user-visible fix. Re-enter as a separate plan when prioritised.

- **Workstream A — 999 / 824 ingestion + `/ack/result` page.** Design already sketched (library readers `readers/ack_999.py` + `readers/ack_824.py`, upload sniffer extension, routers under `/api/v1/ack/*`, React `AckResultPage.tsx`). Useful, does not accelerate the row-loss fix.
- **Lifecycle correlator + dashboard toggle.** `lifecycle.correlate_lifecycle(raw_270, raw_999, raw_824, raw_271)` + per-patient pill bar (Sent · Ack · Business · Eligibility). Depends on Workstream A.
- **DC Medicaid profile rule hardening** (formerly V1.D — DCMD-DTP-001, DCMD-MEMID-001, DCMD-EQ01-001, DCMD-NM1-001). The April 22 pipeline now passes the current profile (`153 / 0 / 0` when re-run), so the old "13 → ~153 issues" target no longer reproduces. Any further hardening is future-proofing and should be scoped against a fresh 824, not the April 17 one.

---

## ASSUMPTIONS AND DEFAULTS

- **Tolerant-first inbound, strict outbound.** Applied consistently to every companion-guide-sensitive field; re-validated at the classifier / validator layer.
- **`not_found` means AAA 75 only.** Every other AAA → `error`. `unknown` is a distinct bucket.
- **Supplemental EB01 codes** (`B, F, J, L, N, R, MC, …`) are preserved and exported but do not determine active/inactive alone.
- **One row = one subscriber transaction** (`ST*271` or `ST*270`), not one `EB` segment.
- **Silent row loss is unacceptable.** Any parser failure surfaces as `parser_issues[]`; accounting mismatches emit the counter and are returned as **200 with partial payload**, never 500.
- **`transaction_count` on `ParseResponse`** is a deprecated alias for one release; remove in the next minor version.
- **Validation page filter vocabulary is `valid / invalid`.** If a future page requires `Active / Inactive / Not Found / Unknown` on pre-271 validation, it needs a new cross-stage lifecycle object — not a filter extension on this page.
