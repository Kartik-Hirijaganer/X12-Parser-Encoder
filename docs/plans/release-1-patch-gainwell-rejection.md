# Release 1 Patch — Gainwell Rejection Fixes

## Context

Release 1 of the 270 generator shipped, but Gainwell rejected the first real submission (all 153 transactions of `Upload-DCTPID000783-DCMEDICAID-20260417-144236-3849576-005010X279A1-T.edi`) via the 824 BRR report. The same generate call also surfaced two operational defects: the output file is written with the wrong extension, and repeated generations reuse the same ISA13, so the payer sees "duplicate interchange control number" on resubmission.

This patch fixes three bugs:
1. Output file extension.
2. Unique interchange / group control numbers per generation (including split batches).
3. Malformed `DTP*291` placement causing 100% rejection on the 270.

## Assumptions / Non-goals

- No server-side counter, no database, no cross-browser ICN coordination. Uniqueness scope stays browser-local through `localStorage.x12_submitter_config.lastIsaControlNumber`, honoring the stateless-API invariant in `CLAUDE.md`.
- `.txt` applies only to generated ANSI submission filenames. Summary files stay `.txt` (already correct), ZIP containers stay `.zip`, JSON manifests stay `.json`. Inbound file-accept lists (`.edi`, `.x12`, `.txt`) are **unchanged**.
- Fixture artifacts under `docs/test-files/` remain reference-only; their commit status is a separate hygiene discussion — not in this patch.

---

## Bug analysis & recommended fix

### Bug 1 — `.edi` extension should be `.txt`

**Evidence.** The user sees `.edi` in the download name. In this checkout the generator actually emits `.x12` at [apps/api/app/services/generator.py:521-530](../../apps/api/app/services/generator.py#L521-L530) (`_build_document_file_name`) and the frontend fallback at [apps/web/src/pages/GenerateResultPage.tsx:35](../../apps/web/src/pages/GenerateResultPage.tsx#L35) is `'eligibility_270.x12'`. Whichever suffix was shipped, the user wants `.txt` — that's what DC Medicaid / Gainwell SFTP channels accept for the raw ANSI payload.

**Recommended fix.** Change the suffix to `.txt` in the central builder (`_build_document_file_name`) — this single change also fixes the per-file entries inside the ZIP since `_archive_entries` uses the same helper. Update the frontend fallback and the matching assertion in [apps/api/tests/test_generate.py:38](../../apps/api/tests/test_generate.py#L38). Leave input-accept lists alone.

**Why this is the fix.** It's a pure naming change with no structural impact on the X12 payload — one centralized builder, one frontend fallback, one test assertion.

---

### Bug 2 — ISA13 / IEA02 / GS06 / GE02 repeat on every generation

**Evidence.** Two compounding issues:

1. **Backend ignores the config.** The frontend already sends `isaControlNumberStart` + `gsControlNumberStart` ([apps/web/src/pages/PreviewPage.tsx:58-68](../../apps/web/src/pages/PreviewPage.tsx#L58-L68), [apps/web/src/services/api.ts:45-63](../../apps/web/src/services/api.ts#L45-L63)), the DTO accepts them ([apps/api/app/schemas/common.py:95-109](../../apps/api/app/schemas/common.py#L95-L109)), and they reach `SubmitterConfig` — but `_build_interchanges` at [apps/api/app/services/generator.py:285, 296, 302, 306](../../apps/api/app/services/generator.py#L285) hardcodes `"000000001"` on ISA/IEA and uses `str(batch_index)` on GS/GE, dropping the config on the floor.
2. **Frontend forgets split-batch files.** After a successful response, [apps/web/src/pages/PreviewPage.tsx:66-68](../../apps/web/src/pages/PreviewPage.tsx#L66-L68) calls `updateLastIcn(response.control_numbers.isa13)`. That top-level `control_numbers` is just `archive_entries[0].control_numbers` ([apps/api/app/services/generator.py:173, 221](../../apps/api/app/services/generator.py#L173)). If a batch splits into 3 files (ICNs N, N+1, N+2), the browser records only N. The next generation starts at N+1 — colliding with file 2 of the previous run.

**Recommended fix.**
- **Backend:** In `_build_interchanges` read `isa_start = config.isa_control_number_start or 1` and `gs_start = config.gs_control_number_start or 1` once; for batch index `i` (1-based) emit `f"{isa_start + i - 1:09d}"` on both ISA13 and IEA02, and `str(gs_start + i - 1)` on both GS06 and GE02. Reuse the `:09d` pattern from `_format_isa_control` in [convenience.py:975-976](../../packages/x12-edi-tools/src/x12_edi_tools/convenience.py#L975-L976).
- **Frontend:** Add a small util (`highestIsa13(response)`) that walks `response.archive_entries`, parses each `control_numbers.isa13` numerically, and returns the max (falling back to `response.control_numbers.isa13` when there are no entries). `PreviewPage.handleProcess` passes that value to `updateLastIcn` instead of the top-level ICN.

**Why this is the fix.** The payload plumbing is already in place; the API just needs to consume it, and the browser just needs to track the *highest* ICN actually generated (not the first). Together this guarantees every generation — single or split — advances monotonically with no DB.

---

### Bug 3 — Gainwell 824/BRR: "Subscriber Eligibility/Benefit Date should not be used"

**Evidence.** The 999 accepted all 153 transactions syntactically (`IK5*A` on each), but the 824 produced 153 `TED*024` errors keyed on `CTX*Loop 2100C Segment DTP`, and the BRR printed for each rejected transaction:

> Segment DTP (Subscriber Eligibility/Benefit Date) is used. It should not be used when segment DTP (Subscriber Date) is not used in loop 2100C. Segment DTP is defined in the guideline at position 2000.
> Data in error: `DTP*291*D8*20260416`

The X279A1 implementation guide defines the **Subscriber Date** DTP inside **Loop 2100C** (Subscriber Name) with qualifiers 291 (Plan), 435 (Admission), 472 (Service). The DTP inside **Loop 2110C** is "Subscriber Eligibility/Benefit Date" and is only permitted when the 2100C DTP is present. Our encoder emits DTP only at 2110C.

Two generators currently do this wrong — both need updating:
- [apps/api/app/services/generator.py:425-442](../../apps/api/app/services/generator.py#L425-L442) — the production path invoked by `/api/v1/generate`.
- [packages/x12-edi-tools/src/x12_edi_tools/convenience.py:1089-1106](../../packages/x12-edi-tools/src/x12_edi_tools/convenience.py#L1089-L1106) — the library's public `build_270()` path.

And the model is missing the field: `Loop2100C_270` at [packages/x12-edi-tools/src/x12_edi_tools/models/loops/loop_2100c.py:18-23](../../packages/x12-edi-tools/src/x12_edi_tools/models/loops/loop_2100c.py#L18-L23) has no `dtp_segments`.

**Recommended fix.** Move `DTP*291` up one loop:
1. Add `dtp_segments: list[DTPSegment] = Field(default_factory=list)` to `Loop2100C_270`.
2. Extend `_Loop2100C270State` at [parser/loop_builder.py:172-185](../../packages/x12-edi-tools/src/x12_edi_tools/parser/loop_builder.py#L172-L185) with a `dtp_segments` list; route DTPs seen *before* the first EQ inside a 2000C into 2100C, and keep post-EQ DTPs routing to 2110C so the parser still round-trips any pre-patch files on disk.
3. Emit `loop.dtp_segments` after `ref_segments` inside `_iter_loop_2100c_270` ([encoder/x12_encoder.py:341-345](../../packages/x12-edi-tools/src/x12_edi_tools/encoder/x12_encoder.py#L341-L345)).
4. Move the `DTPSegment(date_time_qualifier="291", …)` in **both** `_build_transaction` sites into the `Loop2100C_270(..., dtp_segments=[...])` kwargs. Leave `Loop2110C_270` with only `eq_segments`.
5. Keep `SESegment.number_of_included_segments=13` — segment count is unchanged (we move, not add). Verify with an encoded output length test.

**Why this is the fix.** The BRR explicitly states the DTP is "defined in the guideline at position 2000" in Loop 2100C. The X279A1 TR3 defines the Subscriber DTP at 2100C with qualifier 291 allowed. Moving one loop up satisfies the payer without adding segments and is round-trip-safe. An alternate fix — emitting DTP at *both* 2100C and 2110C — would also satisfy the rule but doubles the payload for no product value; we single-place at 2100C.

---

## Implementation Phases

Each phase is a small, independently demoable chunk. Phases ordered so the user-visible wins land first; the library plumbing for Bug 3 lands behind a dormant field before either generator is switched, so a single phase revert restores prior behavior.

### Phase 1 — `.txt` extension

Change the single output-filename builder from `.x12` to `.txt` in [apps/api/app/services/generator.py:521-530](../../apps/api/app/services/generator.py#L521-L530) (this also corrects the per-entry names inside the ZIP since `_archive_entries` uses the same helper). Update fallback at [apps/web/src/pages/GenerateResultPage.tsx:35](../../apps/web/src/pages/GenerateResultPage.tsx#L35) and assertion at [apps/api/tests/test_generate.py:38](../../apps/api/tests/test_generate.py#L38).

**Demo:** Generate one patient → recommended download name ends in `.txt`. Generate a split batch → every ZIP ANSI entry ends in `.txt`; the `_summary.txt` entry stays `.txt`; the container is still `.zip`.

---

### Phase 2 — Unique ICN per generation (backend wiring)

In `_build_interchanges` ([apps/api/app/services/generator.py:241-316](../../apps/api/app/services/generator.py#L241-L316)) replace hardcoded `"000000001"` on ISA/IEA with `f"{(config.isa_control_number_start or 1) + batch_index - 1:09d}"`, and replace `str(batch_index)` on GS/GE with `str((config.gs_control_number_start or 1) + batch_index - 1)`. Add a unit test that POSTs with `isa_control_number_start=42` and asserts `control_numbers.isa13 == "000000042"`, plus a split-batch test that verifies `archive_entries[0].isa13=="000000042"` and `archive_entries[1].isa13=="000000043"`.

**Demo:** `curl /api/v1/generate` twice with `isaControlNumberStart: 42` then `43`; responses return `"000000042"` and `"000000043"`. Split run with start=42 and two batches returns a ZIP whose files are ICN 42 and 43.

---

### Phase 3 — Unique ICN end-to-end (browser-local, split-aware)

Add `highestIsa13(response)` utility next to `nextIsaControlNumber` in [apps/web/src/utils/constants.ts](../../apps/web/src/utils/constants.ts): iterate `archive_entries`, parse `control_numbers.isa13` as an integer, return the max; fall back to `response.control_numbers.isa13` when `archive_entries` is empty. Update [PreviewPage.tsx:66-68](../../apps/web/src/pages/PreviewPage.tsx#L66-L68) to call `updateLastIcn(highestIsa13(response).toString().padStart(9, '0'))` instead of `response.control_numbers.isa13`. Add Vitest coverage: (a) single-file response advances by 1; (b) split response with ICNs {42, 43, 44} advances `lastIsaControlNumber` to 44; (c) next `nextIsaControlNumber(44)` returns 45.

**Demo:** From the running web app, generate a single 270 once → reload → generate again; second ISA13 is prior+1. Generate a split batch starting at `000000002` (two files: 2 and 3) → the next generation starts at `000000004`, not `000000003`.

---

### Phase 4 — Loop 2100C model + encoder support for DTP (dormant field)

Add `dtp_segments: list[DTPSegment] = Field(default_factory=list)` to `Loop2100C_270` at [models/loops/loop_2100c.py](../../packages/x12-edi-tools/src/x12_edi_tools/models/loops/loop_2100c.py). In `_iter_loop_2100c_270` at [encoder/x12_encoder.py:341-345](../../packages/x12-edi-tools/src/x12_edi_tools/encoder/x12_encoder.py#L341-L345) append `yield from loop.dtp_segments` after `ref_segments`. Add an encoder unit test that hand-builds a `Loop2100C_270` with `dtp_segments=[DTPSegment("291","D8","20260416")]` and asserts the emitted segment sits after `REF` and before the first `EQ`.

**Demo:** Run the new encoder unit test. The generators still produce the old (rejected) layout — this phase only enables the option structurally.

---

### Phase 5 — Parser symmetry for Loop 2100C DTP

Extend `_Loop2100C270State` at [parser/loop_builder.py:172-185](../../packages/x12-edi-tools/src/x12_edi_tools/parser/loop_builder.py#L172-L185) with `dtp_segments: list[DTPSegment]` and wire it through `build()`. In the segment router, DTPs seen inside a 2000C *before the first EQ* land in the 2100C state; DTPs seen *after* an EQ continue landing in the 2110C state. Add a parser unit test that (a) parses a hand-crafted 270 with DTP between DMG and EQ, asserts `loop_2100c.dtp_segments[0].date_time_qualifier == "291"` and `loop_2110c[0].dtp_segments == []`; (b) parses a pre-patch 270 with DTP after EQ and asserts it still lands in `loop_2110c[0].dtp_segments` (backward-compat).

**Demo:** `parse(raw_270_new_shape) → encode(...)` round-trips DTP at 2100C. `parse(raw_270_old_shape)` still produces a usable `Interchange` — existing archived files keep loading.

---

### Phase 6 — Flip both generators to emit DTP at 2100C

Move the `DTPSegment(date_time_qualifier="291", …)` in **both** `_build_transaction` sites — [apps/api/app/services/generator.py:409-443](../../apps/api/app/services/generator.py#L409-L443) and [packages/x12-edi-tools/src/x12_edi_tools/convenience.py:1073-1106](../../packages/x12-edi-tools/src/x12_edi_tools/convenience.py#L1073-L1106) — out of the `Loop2110C_270(...)` kwargs and into `Loop2100C_270(..., dtp_segments=[DTPSegment(...)])`. `Loop2110C_270` is left with only `eq_segments`. Update the two fixtures that lock the old emission order:
- [packages/x12-edi-tools/tests/fixtures/270_batch_multi.x12](../../packages/x12-edi-tools/tests/fixtures/270_batch_multi.x12) — regenerate / hand-edit so each transaction has `DMG…DTP*291*D8*…EQ…`.
- [packages/x12-edi-tools/tests/test_phase9_convenience.py:352](../../packages/x12-edi-tools/tests/test_phase9_convenience.py#L352) and [test_phase8_property_based.py:251](../../packages/x12-edi-tools/tests/test_phase8_property_based.py#L251) — update position assertions.

**Demo:** Upload the 153-row Gainwell spreadsheet → generate → open the `.txt` output; each transaction reads `…DMG…DTP*291*D8*YYYYMMDD~EQ*30~SE~` with no DTP between EQ and SE.

---

### Phase 7 — DC Medicaid profile guard-rail

Extend / add [packages/x12-edi-tools/src/x12_edi_tools/payers/dc_medicaid/profile_270.py](../../packages/x12-edi-tools/src/x12_edi_tools/payers/dc_medicaid/profile_270.py) so the validator flags any 270 with a `DTP*291` at Loop 2110C but no `DTP*291` at Loop 2100C, with a SNIP-5 error message mirroring Gainwell's and a suggestion to move the segment. Register the rule in the profile pack so it fires via the existing `/api/v1/validate` endpoint.

**Demo:** Paste a pre-patch 270 (DTP only at 2110C) into the Validate page → blocking error "Subscriber Eligibility/Benefit Date requires Subscriber Date at Loop 2100C — move DTP*291 before the EQ segment." Validate a Phase-6 output → zero issues.

---

### Phase 8 — Regression anchor against the Gainwell sample

Add a synthetic 2-patient integration test in [apps/api/tests/test_generate.py](../../apps/api/tests/test_generate.py) that POSTs through `/api/v1/generate`, parses the returned X12, and asserts for every transaction: (a) exactly one DTP with qualifier 291 exists, (b) that DTP lives under `loop_2100c.dtp_segments`, (c) `loop_2110c[0].dtp_segments == []`, (d) ICN sequencing from Phase 2 still holds. Add to `make test-api` by virtue of living in the existing test module.

**Demo:** `make test` passes cleanly on a fresh checkout. The test fails deterministically if any future change reintroduces the 2110C-DTP layout.

---

## Critical files to modify (one-page summary)

| File | Bug | Change |
| --- | --- | --- |
| [apps/api/app/services/generator.py](../../apps/api/app/services/generator.py) | 1, 2, 3 | `.txt` in filename builder; read `isa_control_number_start`/`gs_control_number_start`; move DTP to `Loop2100C_270` in `_build_transaction` |
| [apps/api/tests/test_generate.py](../../apps/api/tests/test_generate.py) | 1, 2, 3 | assert `.txt`; assert ICN advance single + split; Phase-8 regression |
| [apps/web/src/pages/GenerateResultPage.tsx](../../apps/web/src/pages/GenerateResultPage.tsx) | 1 | fallback filename `.txt` |
| [apps/web/src/utils/constants.ts](../../apps/web/src/utils/constants.ts) | 2 | add `highestIsa13(response)` |
| [apps/web/src/pages/PreviewPage.tsx](../../apps/web/src/pages/PreviewPage.tsx) | 2 | use `highestIsa13(response)` before `updateLastIcn` |
| [packages/x12-edi-tools/src/x12_edi_tools/models/loops/loop_2100c.py](../../packages/x12-edi-tools/src/x12_edi_tools/models/loops/loop_2100c.py) | 3 | add `dtp_segments` to `Loop2100C_270` |
| [packages/x12-edi-tools/src/x12_edi_tools/encoder/x12_encoder.py](../../packages/x12-edi-tools/src/x12_edi_tools/encoder/x12_encoder.py) | 3 | emit `dtp_segments` inside `_iter_loop_2100c_270` |
| [packages/x12-edi-tools/src/x12_edi_tools/parser/loop_builder.py](../../packages/x12-edi-tools/src/x12_edi_tools/parser/loop_builder.py) | 3 | route pre-EQ DTPs into `_Loop2100C270State`; keep post-EQ DTPs in 2110C for backward compat |
| [packages/x12-edi-tools/src/x12_edi_tools/convenience.py](../../packages/x12-edi-tools/src/x12_edi_tools/convenience.py) | 3 | move `DTPSegment(291, …)` from `Loop2110C_270` to `Loop2100C_270` in library's `_build_transaction` |
| [packages/x12-edi-tools/tests/fixtures/270_batch_multi.x12](../../packages/x12-edi-tools/tests/fixtures/270_batch_multi.x12) | 3 | regenerate with DTP at 2100C |
| [packages/x12-edi-tools/tests/test_phase9_convenience.py](../../packages/x12-edi-tools/tests/test_phase9_convenience.py) / [test_phase8_property_based.py](../../packages/x12-edi-tools/tests/test_phase8_property_based.py) | 3 | update DTP-position assertions |
| [packages/x12-edi-tools/src/x12_edi_tools/payers/dc_medicaid/profile_270.py](../../packages/x12-edi-tools/src/x12_edi_tools/payers/dc_medicaid/profile_270.py) | 3 | new guard-rail rule |

Reused utilities (no new helpers): `_format_isa_control` (library), `nextIsaControlNumber` / `updateLastIcn` (web), `Loop2100C_270` / `Loop2110C_270` models.

---

## Test Scenarios

- Single-patient generation → response `download_file_name` ends in `.txt`; ISA13 equals the sent `isaControlNumberStart`; generated payload contains `DMG…DTP*291…EQ` and no post-EQ DTP.
- Multi-batch split generation (e.g. 5 000 rows @ batch size 2 500) → ZIP contains two `.txt` ANSI entries; entry ICNs are N and N+1; browser records max = N+1; next generation starts at N+2.
- Back-to-back browser generations from a clean `localStorage` → first file `000000001`, second file `000000002`.
- Parser round-trip of pre-patch archive (DTP after EQ) → still parses, `loop_2110c[0].dtp_segments[0]` populated, no warning.
- Parser round-trip of post-patch output (DTP before EQ) → `loop_2100c.dtp_segments[0]` populated, `loop_2110c[0].dtp_segments == []`.
- Validator on post-patch output against `dc_medicaid` profile → zero issues. Validator on pre-patch output → one blocking DTP-placement issue.
- Inbound uploads (`.edi`, `.x12`, `.txt`) still accepted by `/api/v1/parse` and `/api/v1/validate`.

---

## Verification

Before opening the PR:

1. `make lint && make typecheck && make test` — all green.
2. `make coverage` — library ≥ 95%, API ≥ 85% (new tests should raise, not drop, coverage).
3. Library round-trip of a 270 with DTP at 2100C asserts segment order.
4. Two sequential `/api/v1/generate` POSTs with `isaControlNumberStart=42` → `"000000042"` then `"000000043"`; a split response with `isaControlNumberStart=42` → ICNs 42 and 43, and a *subsequent* generation starts at 44.
5. PreviewPage Vitest: `localStorage.x12_submitter_config.lastIsaControlNumber` advances by the number of files returned, not by 1.
6. Manual E2E (`cd apps/api && uvicorn app.main:app --reload` + `cd apps/web && npm run dev`):
   - Upload the 153-row Gainwell spreadsheet → generate → download → confirm filename ends in `.txt`, DTP is before EQ in every transaction, no DTP between EQ and SE.
   - Generate again without reloading; ISA13 ticks up by 1.
   - Split a large batch; confirm ZIP entries advance monotonically and the next generation starts strictly after the highest split ICN.
7. Optional: submit the regenerated file to Gainwell's test endpoint; expect a clean 824 (zero DTP-placement rejections).
