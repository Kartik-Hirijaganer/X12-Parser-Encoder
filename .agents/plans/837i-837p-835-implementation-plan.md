# 837I / 837P / 835 Implementation Plan

> **Status:** Draft v1.3 — ready for agent execution
> **Owners:** Platform / RCM Core
> **Target release train:** library `0.2.x` → `0.3.0` cut
> **Companion docs:**
> - [`docs/erd.md`](../../docs/erd.md) — logical data model (generated with `eralchemy`)
> - [`docs/api/openapi.yaml`](../../docs/api/openapi.yaml) — HTTP contract
> - [`docs/api/index.html`](../../docs/api/index.html) — rendered Swagger UI
> - [`docs/architecture.md`](../../docs/architecture.md) — current-state architecture
> - **Companion Guide (local-only reference):** DC Medicaid 270/271 Companion Guide v1.4 (2026-01-28), copyright Gainwell Technologies ("Proprietary and Confidential"). **Do not commit the source text to this repository.** Per §3.9 (new in v1.3), the raw guide lives outside source control (e.g., `metadata/` per `CLAUDE.md` safety rules, which is local-only and gitignored). This plan extracts only the normative rules — payer IDs, batch caps, SNIP levels, filename template, ack set — as implementation constants/tests; citations reference §/table numbers from the guide rather than prose. Phase 0 enforces this: `docs/full_text.txt` (currently untracked) must not be `git add`-ed; a repo-hygiene check (§3.9) blocks it.
>
> **v1.1 revisions (incorporated from a peer review round, with my final sign-off):**
> 1. Parser dispatch key is now `(ST01, ST03)` with `GS08` fallback (§2.4, R-2) — `ST01` alone cannot distinguish 837I vs 837P.
> 2. Delivery sequencing changed: 837I lands first (revenue-blocker), then 835 + 837P in parallel (§1.5). Phase 3 split into 3a (837I + dispatch) and 3b (835 + 837P).
> 3. New `ClaimBuildOptions` contract (§2.10) keeps claim-packaging knobs out of envelope-oriented `SubmitterConfig`.
> 4. API surface canonicalized to `/api/v1/{eligibility,claims,remittance,payers,acks,status}/*` with deprecated flat eligibility aliases (§2.7, Phase 6). `/remittance/835/*` infix removed.
> 5. `/claims/generate` (preview) and `/claims/submission-package` (export) are now distinct — reversing my prior §1.7 collapse. Teammate pushback was correct: packaging metadata is genuinely different from preview.
> 6. Shared-file lock matrix added (§3.2.1) to formalize which phase owns which collision-heavy file.
> 7. `/acks/ingest` and `/status/resolve` documented as planned-501 endpoints with real OpenAPI schemas so clients can integrate the shape pre-implementation.
>
> **v1.2 revisions (aligned to DC Medicaid 270/271 Companion Guide v1.4 dated 2026-01-28 — referenced by section number only, not bundled in this repo; see §3.9):**
> 8. **SNIP Level 7 added.** CG §3.2 + §7.1 applies SNIP Levels 1-5 **and 7** (Provider ID / Member ID business edits against the DC MMIS repository). My prior SNIP 1-5 scope is incomplete for this payer. See §2.6 and Phase 4.
> 9. **Mixed-claim-type batches now split to separate ISA/IEA interchanges, not separate GS/GE.** CG §7.1 states: *"There should be only one interchange per transmission and one transaction type per interchange."* This supersedes my v1.1 claim that separate GS/GE groups are sufficient. `ClaimBuildOptions.split_mixed_claim_types` now emits a list of `Interchange` objects. See §2.10 and Phase 6 submission-package.
> 10. **DC Medicaid payer identifier migration.** CG §2.1.1: ISA08/GS03/NM109(2100A/B) now use `DCMEDICAID` in place of the legacy `100000` / `77033` values. `payers/dc_medicaid/constants_common.py` must carry this and reject legacy values in validation. See Phase 5.
> 11. **Acknowledgement set corrected.** CG Table 1: DC Medicaid produces **TA1, 999, 824 (005010X186), and BRR** — not 999/277CA. The ack scaffold (§2.7, Phase 6 `schemas/acks.py`) is revised accordingly. 277CA remains a future capability for other payers but is not on the DC Medicaid critical path.
> 12. **Payer batch-size limit documented.** CG §7.1: max 5,000 transactions per transmission in batch mode; real-time is 1. `ClaimBuildOptions.max_transactions_per_group` becomes `max_transactions_per_interchange` and the DC Medicaid profile defaults it to `5000`.
> 13. **File naming convention (CG A.4)** captured as optional metadata on `ArchiveEntry`: `<Input Class>-<Sender ID>-<Receiver ID>-<Date>-<Time>-<File ID>-<Transaction Type>-<Usage>.edi`. Produced by the submission-package endpoint when `build_options.include_archive_manifest=True` and a DC Medicaid profile is active.
>
> **v1.3 revisions (cleanup pass before hand-off to parallel agents; incorporates peer redline, with my final sign-off):**
> 14. **Envelope language normalized across the document.** Phase 6, §1.7, §2.7, and §2.10 now consistently describe DC Medicaid mixed-claim batches as splitting at the **ISA/IEA** boundary (one transaction type per interchange, per CG §7.1). The earlier "separate GS/GE" phrasing survives only where it accurately describes the `SEPARATE_GROUPS` partitioning option for payers other than DC Medicaid. The DC Medicaid profile forces `SEPARATE_INTERCHANGES`. See §2.10.
> 15. **270/271 union refactor scoped explicitly.** The current code hard-codes `Transaction270 | Transaction271` in [`models/transactions/functional_group.py`](../../packages/x12-edi-tools/src/x12_edi_tools/models/transactions/functional_group.py), [`parser/x12_parser.py`](../../packages/x12-edi-tools/src/x12_edi_tools/parser/x12_parser.py), [`parser/loop_builder.py`](../../packages/x12-edi-tools/src/x12_edi_tools/parser/loop_builder.py), [`validator/base.py`](../../packages/x12-edi-tools/src/x12_edi_tools/validator/base.py), and the `models/__init__.py` / `models/transactions/__init__.py` surfaces. All six files are now named owners in §3.2 and §3.2.1, owned by the Phase 3a integration agent. A new `TransactionModel` alias (§2.11) becomes the single dispatch type once Phase 3 lands.
> 16. **SNIP 7 validation context is now a first-class contract.** `ValidationContext` is defined in §2.11 (new section) and the `PayerProfile` Protocol gains `snip7_enabled: bool` and `build_validation_context(...)` methods. Phase 0 extends the Protocol; Phase 4 implements the `validate(interchange, *, context=ValidationContext(...))` signature; Phase 5 requires DC Medicaid profiles to populate the context or raise `PayerConfigurationError`. This resolves the v1.2 contradiction between Phase 4 (silent skip) and Phase 5 (hard-fail).
> 17. **Library-first refactor of existing eligibility flows is explicit.** The API 270 generator and 271 parser currently construct envelopes and project transactions inline in `apps/api/app/services/` (see [`apps/api/app/services/generator.py`](../../apps/api/app/services/generator.py), [`apps/api/app/services/parser.py`](../../apps/api/app/services/parser.py)). Phase 3a lands `build_270` via `builders/_common.build_envelope` behind a golden-bytes parity test; **Phase 6 additionally migrates `apps/api/app/services/generator.py` to call `builders.eligibility_270.build_270` and `apps/api/app/services/parser.py` to call a new `readers/eligibility_271.read_271` projection.** Without this, the repo carries two architectural patterns — I'm refusing that outcome. See §2.7 and Phase 6.
> 18. **Stale Section 2.1 artifacts corrected.** Architecture diagram now reads `/api/v1/remittance/*` (not `/remittance/835/*`), the ack scaffold description cites DC Medicaid CG Table 1 (TA1/999/824/BRR, not 999/277CA), the parser block describes `(ST01, ST03)` dispatch, and the §2.3 module list marks `SubmitterConfig` as unchanged (claim-scoped defaults live in the new `ClaimBuildOptions`, per §2.10).
> 19. **Companion-guide repository-hygiene step added.** Plan no longer treats `docs/full_text.txt` as an in-repo companion doc; see revised header and new §3.9. Phase 0 adds a `scripts/check_repo_hygiene.py` gate that fails CI if a "Proprietary and Confidential" marker lands in `docs/` or `packages/`.

---

## 1. Executive Summary

### 1.1 What is being built

Three production-grade EDI transaction sets will be added to the existing `x12-edi-tools` Python library and the FastAPI workbench:

| Transaction | Purpose | Direction | Version |
|------------|---------|-----------|---------|
| **837I** | Institutional claim submission (home-health, hospital, SNF) | Outbound (provider → payer) | `005010X223A2` |
| **837P** | Professional claim submission (clinician-billed services) | Outbound | `005010X222A1` |
| **835** | Electronic Remittance Advice (payment + adjudication detail) | Inbound (payer → provider) | `005010X221A1` |

Each is implemented end-to-end: **typed Pydantic v2 models → parser → encoder → validator (SNIP 1-5) → payer profile overrides → convenience builder/reader → FastAPI routes**. The work is deliberately structured so multiple AI agents can work on non-overlapping files in parallel without merge conflicts.

### 1.2 Why it matters

The library today is eligibility-only (270/271). For a home-health RCM operator, eligibility is a *gate*, not a revenue event. Claim submission (837I/P) and remittance posting (835) are the backbone of AR, denial management, and cash flow — without them, the product sits adjacent to revenue rather than driving it.

- **837I** is the blocking transaction for home-health revenue. Every admission, recertification, and final claim flows through it.
- **835** is how claims turn into cash and how denials are operationally visible. Posting automation requires this.
- **837P** unlocks companion lines (physician oversight, therapy evaluations) billed alongside 837I episodes.

### 1.3 Business value

- **Revenue unlock:** Enables a first-party submission pipeline rather than depending on a commercial clearinghouse SDK for envelope construction.
- **Denial intelligence:** Parsing 835 CAS groups + CARC/RARC codes locally lets us build denial dashboards and payer scorecards without leaking PHI to a third-party BI tool.
- **Posting throughput:** Structured 835 ingestion compresses an accountant-hour job to an API call.
- **Compliance surface:** All SNIP level 1-5 validation runs pre-flight, reducing payer rejections and TA1/999 rework.
- **Extensibility:** The same scaffolding accommodates 999, 277CA, 276/277, and 278 without re-plumbing envelope, validator, or payer-profile systems.

### 1.4 Technical scope

In scope:

- Pydantic v2 domain models for Claim / ClaimLine / Provider / Patient / Payer / Remittance / Adjustment / Acknowledgement / SubmissionBatch
- New X12 segments: CLM, CLP, CAS, SVC, HI, SV1, SV2, SV3, HCP, AMT, QTY, BPR, PLB, PER variants, N3/N4 contextual uses, K3, NTE, PWK, CRC, CR1–CR3, CN1, MIA, MOA, DMG/PAT, SBR, OI, MEA, LX
- New loops (per implementation guide): 2000A/B/C, 2010AA/AB/BA/BB/CA, 2300, 2310A-F, 2320, 2330A-G, 2400, 2410, 2420A-I, 2430, 2440 (837); 1000A/B, 2000, 2100, 2110 (835)
- Transaction classes `Transaction837I`, `Transaction837P`, `Transaction835` following the `Transaction270/271` pattern
- Convenience functions `build_837i`, `build_837p`, `read_835`, plus mirror imports (`from_csv` claim template, etc.)
- Parser dispatcher extension to recognize `ST01 ∈ {837, 835}` and route to new loop builders
- Encoder extension with re-use of `encode_isa` / `encode_segment` primitives
- SNIP 1-5 validators per transaction set, **plus SNIP Level 7** (Provider ID + Member ID business edits) for payers that require it — DC Medicaid CG §3.2 applies Levels 1-5 and 7. Payer-profile hook points layer on top.
- DC Medicaid companion-guide override pack (initial payer) with a documented pattern for adding future payers
- FastAPI routers under canonical namespaces: `/api/v1/eligibility/*` (existing capability migrated), `/api/v1/claims/*`, `/api/v1/remittance/*`, with deprecated flat aliases (`/generate`, `/parse`, `/validate`) preserved for one minor-version cycle
- Planned-but-501 endpoints: `/api/v1/acks/ingest` and `/api/v1/status/resolve` — documented in OpenAPI so clients can integrate the shape now; return `501 Not Implemented` until TA1/999/824/BRR parsing lands. 824 (`005010X186`) is the DC Medicaid priority format per CG Table 1; 277CA is out of scope for this release
- `ClaimBuildOptions` as a new top-level contract (see §2.10): separates claim-packaging knobs from envelope-scoped `SubmitterConfig`; prevents `SubmitterConfig` bloat and keeps 270/271 callers unaffected
- Parser dispatch keyed on **`(ST01, ST03)`** with **`GS08` as fallback** — not `ST01` alone, since 837I and 837P both emit `ST01=837`
- OpenAPI contract + Swagger UI delivered under `docs/api/`
- Logical ERD generated via `eralchemy` from a `.er` DSL source
- Hypothesis property-based tests for roundtrip (encode → parse → equals), parser fuzzing, and control-number invariants

Out of scope (explicitly):

- Persistent storage / database adapters (the library stays stateless — ERD is *logical*, not physical)
- SFTP / AS2 / trading-partner connectivity (caller's responsibility)
- Real patient or payer-specific real-world test data (synthetic only, per `CLAUDE.md`)
- 999, 277CA, 276/277, 278 implementations (scaffolded for but not implemented in this plan)
- UI work in `apps/web/` (tracked separately; this plan delivers API + library only)
- Background job queues or async claim pipelines

### 1.5 Recommended implementation order

```
Phase 0 ── Scaffolding & placeholder modules      (1 agent,   1-2 days)
Phase 1 ── Domain model layer                     (3 agents,  3 days, parallel)
Phase 2 ── X12 segment & loop expansion           (3 agents,  4 days, parallel after Phase 1)
Phase 3a ── 837I transaction + builder + parser   (1+1 agents, 4 days) ◄── lands FIRST
Phase 3b ── 835 + 837P transactions/builders      (2 agents,   5 days, parallel with each other,
                                                                after Phase 3a parser dispatch lands)
Phase 4 ── Validator & SNIP rules                 (3 agents,  3 days, parallel)
Phase 5 ── Payer profile extension (DC Medicaid)  (1 agent,   2 days)
Phase 6 ── FastAPI routers + services + schemas   (2 agents,  3 days, parallel)
Phase 7 ── Convenience layer                      (1 agent,   2 days)
Phase 8 ── Fixtures, property-based tests, E2E    (3 agents,  3 days, parallel)
Phase 9 ── Docs: ERD regen, OpenAPI, Swagger UI   (1 agent,   1 day)
```

**Delivery-order rationale (revised from prior draft):** 837I is the blocking revenue transaction for home-health, so it is sequenced first. 835 ships second because it unlocks posting/denial visibility and closes the AR loop. 837P ships third because its operational need is real but narrower. Phase 3a delivers 837I end-to-end (transaction model, builder, parser, encoder). Phase 3b begins as soon as 3a's `parser/transaction_dispatch.py` merges — 835 and 837P tracks then run **fully in parallel** on disjoint folders (`transaction_835.py` / `readers/` vs `transaction_837p.py` / `builders/claim_837p.py`).

Phases can overlap: Phase 1 (domain) unblocks Phases 2, 3, 4 in parallel. Phase 0 must complete before any parallel work begins — it is the scaffold that prevents file collisions.

### 1.6 Key risks and assumptions

| ID | Risk / Assumption | Severity | Mitigation |
|----|-------------------|----------|------------|
| R-1 | Implementation guide ambiguities (e.g., 2300 CLM05 "Facility Code Value" allowed list drifts between 837I and 837P) | High | Keep guides versioned in `metadata/` (local-only), lock the version pin in `IMPLEMENTATION_REFERENCE` constants per transaction, regression-test against recorded fixtures |
| R-2 | Parser dispatch based on `ST01` **alone cannot distinguish 837I from 837P** (both emit `ST01=837`); non-standard envelopes also mis-route | High | Dispatch key is the composite `(ST01, ST03)` where `ST03` is the implementation-reference identifier (`005010X223A2` for 837I, `005010X222A1` for 837P, `005010X221A1` for 835). When `ST03` is absent or non-canonical, fall back to `GS08`. When both are missing or conflicting, raise `TransactionDispatchError` with `st_control_number` + the observed `(ST01, ST03, GS08)` tuple (non-PHI). Unknown bodies still fall back to `GenericSegment` |
| R-3 | 835 matching to original 837 claims requires TRN/CLP cross-reference logic that some payers fill imperfectly | Medium | Expose raw unmatched remittance claims alongside matched ones; never silently drop |
| R-4 | Decimal precision in CLM02, SV102, SVC02, etc. — floats would corrupt monetary values | High | Use `Decimal` everywhere in domain + segment models; serializer renders with `format(value, "f")` (already the library convention) |
| R-5 | Property-based tests may flake on random Unicode in free-form text fields (NTE, REF descriptions) | Low | Constrain Hypothesis strategies to the X12 basic character set; document the restriction |
| R-6 | Payer variability (companion guides) will outgrow a single-file override model | Medium | Phase 5 delivers a `payers/<payer>/{transaction}.py` per-transaction override pattern, not a single monolith |
| R-7 | PHI logging regression when new segments are added | High | Every new segment emitter routes through `_logging.build_log_extra`, which must not include raw payloads. A CI grep gate (`scripts/check_no_proprietary_content.py`) will be extended to flag `logger.*raw_segment` usage |
| R-8 | Version drift between library and API while both evolve in parallel | Medium | The existing `scripts/check_version_sync.py` and `VERSION` contract remain authoritative. Minor-version bump at the end of Phase 3 (0.2.0) and 0.3.0 at end of Phase 6 |
| R-9 | Parallel agents touching the same `__init__.py` public surface | High | Public-surface additions happen only in Phase 0 scaffolding and Phase 7 convenience — not during Phase 3 parallel work. See Section 3.7 for the collision-avoidance rules |
| A-1 | Assumption: we remain stateless. No DB, no queues, no retention on disk | Core | ERD is *logical*; `docs/erd.md` is a reference artifact only |
| A-2 | Assumption: caller handles SFTP / MFT / AS2 transport and is responsible for recording control-number ledger persistence | Core | Library exposes `ControlNumbers` return on every `build_*` so callers can persist in their own store |
| A-3 | Assumption: synthetic fixtures are built from publicly available WPC examples and the company's own de-identified scaffolds | Core | `tests/fixtures/` expands under the existing synthetic-only policy |

### 1.7 Author's opinionated disagreements with the brief

The task framing implied four things I'm pushing back on — stated up front so reviewers can overrule before work begins:

1. **Unified `/claims/generate` endpoint (preview/build); separate `/claims/submission-package` (export).** After reviewing the teammate plan, I am partially revising my prior stance. The original brief implied two endpoints, which I argued should collapse to one. On reflection: **generation and submission-package are genuinely different concerns** even in a stateless library, because a submission package carries packaging metadata (interchange-level partitioning for mixed 837I/837P batches under a DC Medicaid profile, per-ST `ControlNumbers`, archive entries, a manifest suitable for a caller's outbound ledger) that a preview response doesn't need. I'm keeping:
   - `POST /api/v1/claims/generate` — lightweight preview/build, accepts a discriminated union of `InstitutionalClaim` / `ProfessionalClaim` on `claim_type`, returns X12 + validation result. Suitable for UI "preview before submit" flows.
   - `POST /api/v1/claims/submission-package` — export/submission-prep. Same input shape. Returns the X12 *plus* a `SubmissionPackage` projection (per-ST control numbers, a partitioned interchange/group manifest honoring the active payer's `PartitioningStrategy`, archive entries, payer routing hints). Suitable for the caller's outbound submission pipeline.
   Both dispatch 837I vs 837P internally via `claim_type`. Partitioning is payer-driven (§2.10): the DC Medicaid profile forces `SEPARATE_INTERCHANGES` (one transaction type per ISA/IEA, per CG §7.1); other payers may accept `SEPARATE_GROUPS` (separate GS/GE within one ISA). **Cost accepted:** two endpoints instead of one; mitigated by keeping the request schema identical so clients can switch with a URL change only.

2. **Reconciliation / posting belongs in the caller's domain, not the library.** What the library *can* do is project an 835 into matched/unmatched buckets relative to a caller-supplied list of prior `SubmissionBatch` control numbers. I've kept the endpoint in the OpenAPI but it returns a projection, not a posted result.

3. **ERDs for a stateless library should be logical, not physical.** Using SQLAlchemy here would plant a persistence assumption we don't want. The ERD uses the `.er` DSL (plain text, rendered by `eralchemy`) — it's documentation, not schema migration substrate.

4. **Payer-specific logic should never live in the transaction builders.** Everything payer-specific flows through the `payers/<payer>/` profile, which returns defaults, validation deltas, and per-segment overrides. This is already the 270 pattern; the plan just extends it. If reviewers push to inline payer logic in `builders/837i.py` "for speed," that's a hard no — it re-creates spaghetti by Q4.

---

## 2. Target Architecture

### 2.1 End-state system view

```
┌─────────────────────────────────────────────────────────────────────┐
│                           apps/web (React)                          │
│            Imports spreadsheets, previews X12, posts 835            │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS JSON
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    apps/api (FastAPI, stateless)                    │
│                                                                     │
│  /api/v1/eligibility/*     (existing 270/271/validate, canonical)   │
│  /api/v1/claims/*          (NEW — unified 837I/P via claim_type)    │
│  /api/v1/remittance/*      (NEW — ingest/parse/reconcile)           │
│  /api/v1/acks/*            (NEW — TA1/999/824/BRR; 501 until parsers │
│                              land per DC Medicaid CG Table 1)       │
│  /api/v1/status/*          (NEW — stateless status projection)      │
│  /api/v1/payers/*          (NEW — profile discovery)                │
│                                                                     │
│  routers/  →  services/  →  x12_edi_tools (library)                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │ in-process Python
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              packages/x12-edi-tools (pure-Python library)           │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐  │
│  │   domain/    │  │   models/     │  │   payers/<payer>/        │  │
│  │ business obj │  │ segments/     │  │   profile.py             │  │
│  │ (DB-free)    │  │ loops/        │  │   constants.py           │  │
│  │              │  │ transactions/ │  │   837i.py / 837p.py /    │  │
│  │              │  │               │  │   835.py overrides       │  │
│  └──────┬───────┘  └───────┬───────┘  └────────┬─────────────────┘  │
│         │                  │                   │                    │
│         └──────────────────┼───────────────────┘                    │
│                            ▼                                        │
│  ┌────────────────┐  ┌──────────────────────┐  ┌──────────────────┐ │
│  │  builders/     │  │   parser/            │  │   encoder/       │ │
│  │  claim_837i.py │  │  dispatches by       │  │  serializes typed│ │
│  │  claim_837p.py │  │  (ST01, ST03) with   │  │  interchange →   │ │
│  │  remit_835.py  │  │  GS08 fallback       │  │  text            │ │
│  │  (270 via      │  │  (TransactionDispatch│  │                  │ │
│  │  _common env)  │  │  Error on ambiguity) │  │                  │ │
│  └────────┬───────┘  └──────────┬───────────┘  └────────┬─────────┘ │
│           │                 │                     │                 │
│           └─────────────────┼─────────────────────┘                 │
│                             ▼                                       │
│            ┌───────────────────────────────────────────┐            │
│            │              validator/                   │            │
│            │   SNIP 1-5 (generic) + payer deltas       │            │
│            └───────────────────────────────────────────┘            │
│                             │                                       │
│                             ▼                                       │
│            ┌───────────────────────────────────────────┐            │
│            │              convenience.py               │            │
│            │  build_837i / build_837p / read_835 /     │            │
│            │  existing: build_270 / read_271           │            │
│            └───────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 System boundaries

| Boundary | Contract | Notes |
|----------|----------|-------|
| Web ↔ API | HTTPS + JSON, Pydantic-validated; request-size limits enforced in middleware | Existing pattern |
| API ↔ Library | Pure Python function calls; the library accepts domain objects or dicts and returns typed `Interchange`, `ParseResult`, or projection objects | No serialization crossing this boundary |
| Library ↔ External | None. The library never opens sockets, never writes to disk (tests and apps do) | Preserves the "framework-agnostic" requirement in `CLAUDE.md` |
| Library internal (domain ↔ X12) | `domain/` models are X12-agnostic; `builders/` translate domain → wire; `parser/` translates wire → typed segments + `readers/` project typed segments back to domain | This is the key separation that enables reuse for future non-X12 sources (e.g., NUCC JSON, FHIR Claim) |

### 2.3 Core modules (post-implementation)

```
x12_edi_tools/
├── __init__.py                   # Public surface (curated re-exports)
├── __about__.py
├── _logging.py                   # Correlation-id-aware logger (unchanged)
├── common/                       # Delimiters, enums, shared types (unchanged, extended)
│   ├── delimiters.py
│   ├── enums.py                  # + new enums: ClaimFrequencyCode, ServiceLineRevenueCode, CAS*
│   └── types.py
├── config.py                     # SubmitterConfig (unchanged — envelope-only) + new ClaimBuildOptions (§2.10)
├── exceptions.py                 # + RemittanceParseError, ClaimValidationError
├── domain/                       # NEW — business objects, X12-agnostic
│   ├── __init__.py
│   ├── claim.py                  # Claim, ClaimLine
│   ├── patient.py                # Patient (subscriber + patient, both)
│   ├── provider.py               # BillingProvider, RenderingProvider, AttendingProvider, etc.
│   ├── payer.py                  # Payer
│   ├── remittance.py             # Remittance, RemittancePayment, RemittanceClaim, RemittanceServiceLine
│   ├── adjustment.py             # Adjustment (CAS groups), CARCRARCMessage
│   ├── acknowledgement.py        # Acknowledgement (999, 277CA scaffold)
│   ├── submission_batch.py       # SubmissionBatch (envelope manifest)
│   └── audit.py                  # TransactionAudit (non-PHI audit record)
├── models/                       # X12 wire-format typed models
│   ├── base.py                   # X12BaseModel, X12Segment, GenericSegment (unchanged)
│   ├── segments/                 # Pydantic segment classes
│   │   ├── (existing: aaa, bht, dmg, dtp, eb, eq, ge, gs, hl, iea, isa, ls_le,
│   │   │    n3, n4, nm1, per, prv, ref, se, st, trn)
│   │   ├── clm.py                # NEW (837)
│   │   ├── sbr.py                # NEW (837)
│   │   ├── pat.py                # NEW (837)
│   │   ├── oi.py                 # NEW (837)
│   │   ├── cn1.py                # NEW (837)
│   │   ├── crc.py                # NEW (837)
│   │   ├── cr1.py                # NEW (837 — ambulance/emergency)
│   │   ├── cr2.py                # NEW (837 — spinal manipulation)
│   │   ├── cr3.py                # NEW (837 — DME)
│   │   ├── hi.py                 # NEW (837 — diagnosis + value + occurrence + condition codes)
│   │   ├── sv1.py                # NEW (837P)
│   │   ├── sv2.py                # NEW (837I)
│   │   ├── sv3.py                # NEW (837 — dental)
│   │   ├── svd.py                # NEW (837 — line adjudication)
│   │   ├── svc.py                # NEW (835)
│   │   ├── cas.py                # NEW (835/837 claim + line adjustments)
│   │   ├── clp.py                # NEW (835)
│   │   ├── plb.py                # NEW (835 — provider-level adjustments)
│   │   ├── bpr.py                # NEW (835 — financial information)
│   │   ├── amt.py                # NEW (shared)
│   │   ├── qty.py                # NEW (shared)
│   │   ├── k3.py                 # NEW (shared — fixed-format add-ons)
│   │   ├── nte.py                # NEW (shared)
│   │   ├── pwk.py                # NEW (837)
│   │   ├── mia.py                # NEW (835 — institutional outpatient adjudication)
│   │   ├── moa.py                # NEW (835 — medicare outpatient adjudication)
│   │   ├── mea.py                # NEW (837 — measurements)
│   │   ├── lx.py                 # NEW (shared — service line counter)
│   │   └── hcp.py                # NEW (shared — health-care pricing)
│   ├── loops/                    # Typed loop containers
│   │   ├── (existing: loop_2000a, loop_2000b, loop_2000c, loop_2100a/b/c, loop_2110c)
│   │   └── claims/               # NEW subpackage — shared across 837I and 837P
│   │       ├── __init__.py
│   │       ├── loop_1000a.py     # Submitter name
│   │       ├── loop_1000b.py     # Receiver name
│   │       ├── loop_2000a_claim.py       # Billing provider
│   │       ├── loop_2000b_claim.py       # Subscriber
│   │       ├── loop_2000c_claim.py       # Patient (non-subscriber)
│   │       ├── loop_2010aa.py    # Billing provider name
│   │       ├── loop_2010ab.py    # Pay-to address
│   │       ├── loop_2010ac.py    # Pay-to plan
│   │       ├── loop_2010ba.py    # Subscriber name
│   │       ├── loop_2010bb.py    # Payer name
│   │       ├── loop_2010ca.py    # Patient name
│   │       ├── loop_2300.py      # Claim information (CLM + DTP + CL1 + PWK + CN1 + DN1-2 + REF + NTE + CR1-3 + HI + HCP)
│   │       ├── loop_2310a.py     # Referring provider
│   │       ├── loop_2310b.py     # Rendering provider
│   │       ├── loop_2310c.py     # Service facility location
│   │       ├── loop_2310d.py     # Supervising provider
│   │       ├── loop_2310e.py     # Ambulance pick-up location
│   │       ├── loop_2310f.py     # Ambulance drop-off location
│   │       ├── loop_2320.py      # Other subscriber information
│   │       ├── loop_2330a.py     # Other subscriber name
│   │       ├── loop_2330b.py     # Other payer name
│   │       ├── loop_2400.py      # Service line (LX)
│   │       ├── loop_2410.py      # Drug identification
│   │       ├── loop_2420a.py     # Rendering provider (line-level)
│   │       ├── loop_2430.py      # Line adjudication information
│   │       └── loop_2440.py      # Form identification code
│   │   └── remittance/           # NEW subpackage — 835-specific
│   │       ├── __init__.py
│   │       ├── loop_1000a_remit.py  # Payer identification
│   │       ├── loop_1000b_remit.py  # Payee identification
│   │       ├── loop_2000_remit.py   # Header number (LX)
│   │       ├── loop_2100_remit.py   # Claim payment information (CLP + CAS + NM1 + MIA/MOA + REF + DTM + PER + AMT + QTY)
│   │       ├── loop_2110_remit.py   # Service payment information (SVC + DTM + CAS + REF + AMT + QTY + LQ)
│   ├── transactions/
│   │   ├── (existing: interchange, functional_group, transaction_270, transaction_271)
│   │   ├── transaction_837i.py   # NEW
│   │   ├── transaction_837p.py   # NEW
│   │   └── transaction_835.py    # NEW
├── parser/
│   ├── (existing: tokenizer, segment_parser, isa_parser, loop_builder, x12_parser, _exceptions, __init__)
│   └── transaction_dispatch.py   # NEW — maps ST01 → transaction-specific loop_builder
├── encoder/
│   ├── (existing: isa_encoder, segment_encoder, x12_encoder, __init__)
│   └── claim_encoder.py          # NEW — hand-off for 837/835 structural specifics
├── builders/                     # NEW — domain → typed Interchange
│   ├── __init__.py
│   ├── claim_837i.py             # build_837i(claims, config, profile) → Interchange
│   ├── claim_837p.py             # build_837p(claims, config, profile) → Interchange
│   └── _common.py                # Envelope construction helpers (shared with existing 270 builder)
├── readers/                      # NEW — typed parse result → domain projection
│   ├── __init__.py
│   ├── remittance_835.py         # read_835(payload) → RemittanceResultSet
│   └── _common.py                # Projection helpers (mirrors convenience 271 projection)
├── validator/
│   ├── (existing: base, snip1-5, x12_validator, __init__)
│   └── rules/                    # NEW subpackage — transaction-scoped rules
│       ├── __init__.py
│       ├── rules_837.py
│       ├── rules_837i.py
│       ├── rules_837p.py
│       └── rules_835.py
├── payers/
│   ├── __init__.py
│   ├── base.py                   # + extended Protocol: get_claim_defaults(), get_remit_overrides()
│   └── dc_medicaid/
│       ├── (existing: profile.py, constants.py, search_criteria.py, __init__.py)
│       ├── constants_837.py      # NEW — payer-specific CARC/RARC, accepted POS codes, TOB prefixes
│       ├── constants_835.py      # NEW
│       ├── profile_837i.py       # NEW
│       ├── profile_837p.py       # NEW
│       └── profile_835.py        # NEW
├── convenience.py                # Extended with build_837i, build_837p, read_835
```

### 2.4 Shared infrastructure

**Envelope construction** stays DRY. `builders/_common.py` extracts the ISA/GS/GE/IEA scaffolding currently inlined in `convenience.build_270`. Every builder (`build_270`, `build_837i`, `build_837p`) calls `_common.build_envelope(config, transactions, functional_identifier_code, implementation_reference)` which returns a fully-formed `Interchange`.

**Parser dispatch** is a pure function keyed on the composite `(ST01, ST03)` with `GS08` as a fallback. `parser/transaction_dispatch.py` exposes:

```python
def dispatch(
    st01: str,                          # e.g. "837", "835", "270"
    st03: str | None,                   # implementation reference, e.g. "005010X223A2"
    gs08: str | None = None,            # functional-group version qualifier, fallback for ST03
) -> TransactionLoopBuilder: ...
```

Dispatch table (canonical):

| `ST01` | `ST03`           | Transaction | Loop builder                 |
|--------|------------------|-------------|------------------------------|
| `270`  | `005010X279A1`   | 270         | `loop_builder.build_270`     |
| `271`  | `005010X279A1`   | 271         | `loop_builder.build_271`     |
| `837`  | `005010X223A2`   | 837I        | `loop_builder.build_837i`    |
| `837`  | `005010X222A1`   | 837P        | `loop_builder.build_837p`    |
| `835`  | `005010X221A1`   | 835         | `loop_builder.build_835`     |

When `ST03` is absent or non-canonical, the dispatcher consults `GS08`. When both are absent or conflict, `TransactionDispatchError` is raised with `st_control_number` + the observed `(ST01, ST03, GS08)` tuple (non-PHI; safe to log). Unknown bodies still fall back to `GenericSegment` preserving current behavior. The existing `x12_parser.parse()` calls `dispatch` before building the transaction body.

**Validator layering** is four tiers:

1. **SNIP 1** (existing) — ISA/IEA structural integrity; transaction-agnostic
2. **SNIP 2-3** (existing + extended) — Segment/element syntax and code-set validation; per-transaction enum dispatch
3. **SNIP 4-5** (new, per transaction) — Situational and payer-specific rules, pluggable via `validator/rules/rules_<txn>.py` and `payers/<payer>/profile_<txn>.py`
4. **SNIP 7** (new, payer-opt-in) — Provider ID and Member ID business-edit validation against a payer-supplied repository. Executed via the `ValidationContext` API defined in §2.11: the caller or payer profile injects `ProviderRegistryLookup` / `MemberRegistryLookup` callables. The library ships **no built-in repository**; this keeps the library stateless while honoring DC Medicaid CG §3.2 which mandates SNIP 7. Precedence, skip-vs-fail semantics, and the `PayerProfile.build_validation_context()` hook are defined canonically in §2.11. The validator reports SNIP 7 failures as `X12-<TXN>-SNIP7-PROVIDER-NOT-FOUND` / `X12-<TXN>-SNIP7-MEMBER-NOT-FOUND` with stable codes so downstream 824/BRR mapping is deterministic; missing lookups surface as `X12-SNIP7-SKIPPED-NO-LOOKUP` warnings unless a profile promotes them to errors.

**Logging and correlation IDs** are unchanged. All new code uses `x12_edi_tools._logging.build_log_extra` with the documented non-PHI fields only. Reviewer checklist for new code: zero raw payloads, zero member identifiers, zero names, zero filenames in log statements.

### 2.5 Payer override strategy

Payer profiles are hierarchical, not hard-coded. The existing `PayerProfile` Protocol in `payers/base.py` is extended:

```python
class PayerProfile(Protocol):
    name: str
    snip7_enabled: bool                      # NEW — see §2.11

    # Existing
    def get_defaults(self) -> dict[str, object]: ...

    # CHANGED in v1.3: validate now takes a required ValidationContext (§2.11)
    def validate(
        self,
        interchange: Interchange,
        *,
        context: ValidationContext,
    ) -> Sequence[ValidationError]: ...

    # NEW
    def build_validation_context(
        self,
        *,
        provider_lookup: ProviderRegistryLookup | None = None,
        member_lookup: MemberRegistryLookup | None = None,
        correlation_id: str | None = None,
    ) -> ValidationContext: ...  # see §2.11 for precedence rules

    def get_claim_defaults(self, transaction: str) -> dict[str, object]:
        """Return per-transaction defaults (e.g., claim frequency, TOB, POS, signature indicator)."""

    def get_remit_overrides(self) -> dict[str, object]:
        """Return payer-specific CARC/RARC mappings, PLB handling hints, etc."""

    def validate_claim(self, transaction: Transaction837I | Transaction837P) -> Sequence[ValidationError]: ...

    def validate_remittance(self, transaction: Transaction835) -> Sequence[ValidationError]: ...
```

Each payer lives under `payers/<payer>/` with per-transaction override modules. New payers follow the DC Medicaid pattern: constants files for data, profile files for behavior. The `get_profile(name)` registry stays the single entry point.

Payer override precedence (highest wins):

1. Caller-supplied `custom_rules` / `overrides` argument to `validate()` / `build_*()`
2. `payers/<payer>/profile_<txn>.py` deltas
3. `payers/base.py` defaults
4. Library SNIP defaults

### 2.6 Validation strategy

Every transaction is validated at three checkpoints:

1. **Pre-build (domain)** — Pydantic validators on `Claim`, `ClaimLine`, `Remittance` et al. reject malformed business objects before any X12 is emitted. Fast, clear errors; no SNIP context yet.
2. **Post-build, pre-encode (SNIP 1-3)** — `validate(interchange, levels=[1,2,3])` runs against the typed `Interchange`. Catches structural issues introduced by the builder.
3. **Post-encode or on-parse (SNIP 4-5, +7 when profile opts in)** — Full validator sweep including payer deltas. For outbound, this is the pre-flight gate before submission. For inbound (835), it is the receipt gate before projection. SNIP 7 runs against a `ValidationContext` (§2.11): DC Medicaid's profile sets `snip7_enabled=True` and overrides `build_validation_context` to raise if lookups are missing (CG §3.2 makes SNIP 7 mandatory). Other payers may opt in with soft-skip semantics.

The existing `ValidationResult` shape is preserved (severity, level, code, message, location). New transaction-scoped error codes are namespaced: `X12-837I-*`, `X12-837P-*`, `X12-835-*`.

### 2.7 Data flow between domain models, transaction builders/parsers, and APIs

**Canonical API surface (post-migration):**

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /api/v1/eligibility/generate` | implemented (canonical) | Replaces flat `/generate` which remains as deprecated alias for one minor-version cycle |
| `POST /api/v1/eligibility/parse` | implemented (canonical) | Replaces flat `/parse`; alias preserved |
| `POST /api/v1/eligibility/validate` | implemented (canonical) | Replaces flat `/validate`; alias preserved |
| `POST /api/v1/claims/generate` | **new** | Preview/build — unified 837I/P via `claim_type` discriminator |
| `POST /api/v1/claims/validate` | **new** | Validate structured claim or raw 837 payload; dispatches on `claim_type` or parsed `ST03` |
| `POST /api/v1/claims/submission-package` | **new** | Export/submission-prep — returns X12 + `SubmissionPackage` projection (per-ST control numbers, interchange/group partitioning per active payer profile — DC Medicaid = `SEPARATE_INTERCHANGES`, CG §7.1 — archive manifest) |
| `POST /api/v1/remittance/ingest` | **new** | Lightweight: envelope-level validation + receipt summary only |
| `POST /api/v1/remittance/parse` | **new** | Full typed remittance projection (payments, claims, service lines) |
| `POST /api/v1/remittance/reconcile` | **new** | Read-only projection of remittance matched against caller-supplied claim corpus; stateless |
| `GET /api/v1/payers`, `GET /api/v1/payers/{name}` | **new** | Profile discovery + documented defaults |
| `POST /api/v1/acks/ingest` | **documented, 501 until TA1/999/824/BRR parsers land** | Present in OpenAPI with discriminated-union schema across all four DC Medicaid ack formats (CG Table 1) so clients can integrate now. 824 prioritized. |
| `POST /api/v1/status/resolve` | **documented, 501 until ack parsing lands** | Stateless: takes caller-supplied claim + ack + remittance inputs and returns a computed status projection |

I dropped the `/remittance/835/` infix from my prior draft: future remittance-family transactions (277U) should not force a URL break. Transaction version is an implementation detail behind the service boundary, not a URL dimension.

**Library-first refactor of the existing 270/271 API services (v1.3).** Today [`apps/api/app/services/generator.py`](../../apps/api/app/services/generator.py) constructs `Interchange` / `FunctionalGroup` / `Transaction270` directly from library model classes, and [`apps/api/app/services/parser.py`](../../apps/api/app/services/parser.py) reaches into typed transactions and projects them to the API response inline. This is an architectural drift — it means there is no canonical `build_270` / `read_271` in the library, only an ad-hoc reimplementation in the API. Shipping 837/835 as library-first callables while leaving 270/271 as a different pattern would double the maintenance burden and defeat the reason for the refactor.

Accordingly, v1.3 adds an explicit migration:

1. **Phase 3a** lands `builders/_common.build_envelope(...)` and introduces a dedicated `builders/eligibility_270.build_270(...)` that *wraps* the existing inline logic. A golden-bytes parity test captures current 270 API output and asserts byte-for-byte equality after the refactor (same gate used for the downstream library consumers). The library's existing `convenience.build_270` is routed through `builders.eligibility_270.build_270` in the same PR.
2. **Phase 3b** lands `readers/eligibility_271.read_271(parse_result)` — a library-level projection from `Transaction271` → the domain shape the API currently assembles inline. Initially this matches the API's current projection 1:1.
3. **Phase 6** migrates the API services:
   - `apps/api/app/services/generator.py` is rewritten as a thin wrapper over `builders.eligibility_270.build_270` + `encoder.encode_all`. Inline `Interchange`/`FunctionalGroup` construction is deleted.
   - `apps/api/app/services/parser.py` is rewritten as a thin wrapper over `parser.parse` + `readers.eligibility_271.read_271`.
   Both refactors are guarded by golden-JSON snapshot tests captured before the change, and by `docs/api/openapi.yaml` diff checks.

After Phase 6, every API service is a thin translator that calls exactly one library builder or reader — no exceptions. Reviewers are instructed to reject API services that import from `x12_edi_tools.models.*` directly.

**Outbound flow (claim submission):**

```
POST /api/v1/claims/generate            { claims: [ { claim_type: "INSTITUTIONAL" | "PROFESSIONAL", ... } ] }
POST /api/v1/claims/submission-package  (same input; returns X12 + SubmissionPackage)
  │
  ▼
apps/api/app/schemas/claims.py::GenerateClaimRequest (Pydantic, camelCase-compat; discriminated union on claim_type)
  │
  ▼
apps/api/app/services/claims.py::generate_claims_response() | prepare_submission_package()
  │  — partitions by claim_type → domain.InstitutionalClaim[] / ProfessionalClaim[] + SubmitterConfig + ClaimBuildOptions
  ▼
x12_edi_tools.builders.claim_837.build_837(claims, submitter_config, build_options, profile)
  │  — dispatches to build_837i / build_837p per partition; returns list[Interchange]
  │    (separate ISA/IEA per claim_type under DC Medicaid SEPARATE_INTERCHANGES strategy; CG §7.1)
  ▼
x12_edi_tools.validator.validate(interchange, levels=[1..5, 7 if profile.snip7_enabled], profile=...)
  │  — SNIP 7 runs only when the payer profile declares it and supplies registry lookups
  ▼
x12_edi_tools.encoder.encode_all(interchanges, config=submitter_config, correlation_id=...)
  │  — returns one x12 payload per interchange
  ▼
apps/api/app/services/claims.py wraps payloads + per-ST ControlNumbers + ArchiveEntry[] (submission-package only)
  │
  ▼
apps/api/app/schemas/claims.py::GenerateClaimResponse | SubmissionPackageResponse
```

**Inbound flow (remittance parsing):**

```
POST /api/v1/remittance/parse  (multipart .835 or inline payload)
  │
  ▼
apps/api/app/services/remittance.py
  │
  ▼
x12_edi_tools.parser.parse(raw, strict=False, on_error="collect")
  │
  ▼
x12_edi_tools.readers.remittance_835.read_835(parse_result)
  │  — projects Transaction835 → RemittanceBatch (domain objects)
  ▼
apps/api/app/services/remittance.py wraps projection + parse_errors + summary
  │
  ▼
apps/api/app/schemas/remittance.py::RemittanceParseResponse
```

**Reconciliation flow** is explicit and stateless: `POST /api/v1/remittance/reconcile` takes a `RemittanceBatch` (or raw 835 for convenience) **plus** a caller-supplied list of prior `SubmissionBatch` control numbers / CLM01 identifiers, and returns `{ matched: [...], unmatched_remittance_claims: [...], unmatched_submission_claims: [...], summary: {...} }`. Unmatched remittance claims are never silently dropped — this is the teammate plan's call-out and it's the right one. Matching heuristics (TRN→ISA control, CLP01 fuzzy match) live in `reconciliation/matcher.py`.

**Acknowledgement / status flow** is scaffolded but deferred. DC Medicaid CG Table 1 specifies the inbound ack set as **TA1, 999, 824 (005010X186), and BRR** (Business Reject Report — a human-readable rendering of 824). `POST /api/v1/acks/ingest` is present in `docs/api/openapi.yaml` with discriminated-union request schemas covering all four ack formats. The 824 parser will be the priority implementation because DC Medicaid SNIP 3-7 errors report through 824. Handler returns `501 Not Implemented` until parsing lands; `POST /api/v1/status/resolve` similarly 501s until it can consume TA1+999+824 projections. Router lives at `apps/api/app/routers/acks.py`; feature flag `X12_API_ENABLE_ACKS=false` gates the 501→200 transition when implementations ship. 277CA remains a future capability for payers that use it, but is **not** on DC Medicaid's critical path — the prior v1.0/v1.1 plan incorrectly named 277CA as the primary ack format for this payer.

### 2.8 Fit alongside existing 270/271 support

The new transactions are purely additive. No existing public API changes. The current `build_270` / `read_271` / `parse` / `encode` / `validate` signatures are preserved. New public functions are added to `x12_edi_tools.__init__` via Phase 7.

Contract tests in `tests/test_smoke.py` continue to exercise 270/271. New contract tests mirror that structure (`test_smoke_837i.py`, `test_smoke_837p.py`, `test_smoke_835.py`) — each ensures the public surface of the respective transaction round-trips through `build → encode → parse → compare`.

### 2.9 Architecture documentation source

The architecture diagram in Section 2.1 is the authoritative high-level view. A detailed module-relationship diagram is rendered by `eralchemy` from the same source file that drives the ERD ([`docs/erd.md`](../../docs/erd.md)). See Section 3.5 below for where the source lives and how it's regenerated.

Swagger/OpenAPI is the authoritative HTTP contract ([`docs/api/openapi.yaml`](../../docs/api/openapi.yaml)). Keep both regenerations gated in CI (see Phase 9).

### 2.10 `ClaimBuildOptions` — separate contract from `SubmitterConfig`

Incorporated from the teammate plan: **do not overload `SubmitterConfig` with claim-scoped fields.** `SubmitterConfig` is envelope-oriented (ISA sender/receiver IDs, delimiters, usage indicator, control-number allocator). Claim packaging knobs belong in a new `ClaimBuildOptions` model under `config.py`:

```python
class PartitioningStrategy(str, Enum):
    SINGLE_GROUP = "single_group"            # All claims in one GS/GE within one ISA/IEA — valid only when every
                                             # claim has the same claim_type (no mixing).
    SEPARATE_GROUPS = "separate_groups"      # One ISA/IEA, one GS/GE per claim_type — permitted by payers that
                                             # accept multiple transaction types per interchange. NOT valid for
                                             # DC Medicaid.
    SEPARATE_INTERCHANGES = "separate_interchanges"  # One ISA/IEA per claim_type — DC Medicaid required default
                                             # per CG §7.1: "There should be only one interchange per
                                             # transmission and one transaction type per interchange."

class ClaimBuildOptions(BaseModel):
    """Claim-scoped packaging options. Separate from SubmitterConfig to keep
    envelope config stable for 270/271 callers and avoid field bloat."""

    # Envelope partitioning (reflects payer constraints; DC Medicaid requires SEPARATE_INTERCHANGES)
    partitioning_strategy: PartitioningStrategy = PartitioningStrategy.SEPARATE_INTERCHANGES
    max_transactions_per_interchange: int | None = 5000  # DC Medicaid CG §7.1 batch cap; None = uncapped

    # Claim-level defaults (can be overridden per-claim)
    default_claim_frequency_code: str = "1"  # Original
    default_assignment_of_benefits: bool = True
    default_signature_indicator: str = "Y"
    default_release_of_information: str = "Y"

    # Provider/identifier defaults
    default_billing_provider_taxonomy: str | None = None

    # Submission metadata
    submission_mode: Literal["production", "test"] = "test"  # → ISA15 independently
    include_archive_manifest: bool = False  # True for /submission-package only
    archive_filename_template: str | None = None  # e.g. DC Medicaid CG A.4 template; payer profile supplies
```

`build_837i` / `build_837p` / `prepare_claim_submission` therefore return `list[Interchange]` (not a single `Interchange`) when partitioning produces multiple envelopes. The 270 builder is unaffected — its return type stays `Interchange`. This is an intentional API asymmetry: claim submission fundamentally requires list-return semantics because payers impose interchange-level constraints.

### 2.11 Core contracts for parallel execution — `TransactionModel` alias and `ValidationContext`

Two small contracts must land in Phase 0 (Protocol extension) and Phase 3a (alias) so every downstream phase can code against them without racing on refactors. These are the explicit fix for peer-redline High-2 and High-3.

**`TransactionModel` type alias.** Currently `Transaction270 | Transaction271` is hard-coded in [`models/transactions/functional_group.py`](../../packages/x12-edi-tools/src/x12_edi_tools/models/transactions/functional_group.py), [`parser/x12_parser.py`](../../packages/x12-edi-tools/src/x12_edi_tools/parser/x12_parser.py), [`parser/loop_builder.py`](../../packages/x12-edi-tools/src/x12_edi_tools/parser/loop_builder.py), and [`validator/base.py`](../../packages/x12-edi-tools/src/x12_edi_tools/validator/base.py). Phase 3a introduces a single alias:

```python
# x12_edi_tools/models/transactions/__init__.py
TransactionModel = (
    Transaction270
    | Transaction271
    | Transaction837I
    | Transaction837P
    | Transaction835
)
```

All five call sites are rewritten to import `TransactionModel` (Agent G, Phase 3a). `Transaction837I` / `Transaction837P` / `Transaction835` are added as literal union members in the same commit that lands their transaction classes (Agents H/I/K). This is why §3.2.1 locks `models/transactions/__init__.py` to Phase 3a with controlled extension by Phase 3b agents.

**`ValidationContext` and the SNIP 7 contract.** SNIP 7 (Provider ID / Member ID business edits against an external repository) cannot be executed by the library alone — it requires caller-supplied lookups. Previously the plan left this underspecified: Phase 4 said "silently skip if no lookups", Phase 5 said "hard-fail if no lookups for DC Medicaid." Both can be true, but only if they are different layers of the same contract. Defined here:

```python
# x12_edi_tools/validator/context.py  (Phase 0 scaffolds; Phase 4 uses)
from typing import Callable, Protocol

class ProviderRegistryLookup(Protocol):
    def __call__(self, npi: str, taxonomy: str | None = None) -> bool: ...

class MemberRegistryLookup(Protocol):
    def __call__(self, member_id: str, birth_date: str | None = None) -> bool: ...

@dataclass(frozen=True)
class ValidationContext:
    """Injected dependencies for optional validation levels (currently SNIP 7).

    Every field is Optional. A level that needs a dependency is skipped (with a
    `warning` ValidationError, code X12-SNIP7-SKIPPED-NO-LOOKUP) if the dependency
    is absent. Payer profiles may promote that warning to an error via their
    `build_validation_context(raise_on_missing=True)` override.
    """
    provider_lookup: ProviderRegistryLookup | None = None
    member_lookup: MemberRegistryLookup | None = None
    correlation_id: str | None = None
```

Protocol extension on `PayerProfile` (Phase 0 locks this in `payers/base.py`):

```python
class PayerProfile(Protocol):
    name: str
    snip7_enabled: bool                     # NEW — default False on the base stub

    def build_validation_context(
        self,
        *,
        provider_lookup: ProviderRegistryLookup | None = None,
        member_lookup: MemberRegistryLookup | None = None,
        correlation_id: str | None = None,
    ) -> ValidationContext:
        """Compose a ValidationContext for this payer.

        DC Medicaid (CG §3.2) overrides this: if either lookup is None it raises
        PayerConfigurationError instead of returning a partial context. Other payers
        may return a partial context and let the default SNIP 7 executor skip with
        warnings."""

    def validate(
        self,
        interchange: Interchange,
        *,
        context: ValidationContext,          # CHANGED — required keyword arg
    ) -> Sequence[ValidationError]: ...
```

The library-level validator picks up the context:

```python
# x12_edi_tools/validator/x12_validator.py
def validate(
    interchange: Interchange,
    *,
    levels: Sequence[SnipLevel] = (...),
    profile: PayerProfile | None = None,
    context: ValidationContext | None = None,
) -> Sequence[ValidationError]:
    ctx = context or (profile.build_validation_context() if profile else ValidationContext())
    ...
```

**Precedence for SNIP 7 outcomes:**

1. Caller supplies `context` explicitly → used verbatim.
2. Caller supplies `profile` but no `context` → `profile.build_validation_context()` is called with no lookups. DC Medicaid raises; other payers return a partial context.
3. Neither → base `ValidationContext()` with all-None lookups. SNIP 7 is silently skipped with a `warning` (non-fatal).

This is the single source of truth. Phase 4 implements `validator/snip7.py` against this contract; Phase 5 implements DC Medicaid's `build_validation_context` override and its `snip7_enabled=True`. No other phase defines or reshapes this API.

Rules of engagement:
- `build_270` / `read_271` signatures are untouched. They continue to take `SubmitterConfig` only.
- `build_837i` / `build_837p` / `prepare_claim_submission` take both `SubmitterConfig` and `ClaimBuildOptions` (the latter defaulted).
- `read_835` does not use `ClaimBuildOptions`; it uses `SubmitterConfig` only for delimiter reuse on acknowledgement emissions (future).
- Payer profiles may *override* `ClaimBuildOptions` defaults via `PayerProfile.get_claim_defaults(transaction)` — precedence identical to §2.5.

---

## 3. Scaffolding

### 3.1 Repository file tree (target end-state, files marked)

Legend: `[E]` = exists today, `[N]` = new in this plan, `[M]` = modified.

```
X12-Parser-Encoder/
├── .agents/
│   └── plans/
│       ├── 837i-837p-835-implementation-plan.md           [N]  ← this file
│       └── 837i-837p-835-implementation-plan.html         [N]
│
├── docs/
│   ├── architecture.md                                    [E]
│   ├── erd.md                                             [N]
│   ├── erd.html                                           [N]
│   ├── erd.er                                             [N]  ← eralchemy DSL source
│   ├── erd.svg                                            [N]  ← generated from erd.er (CI)
│   └── api/
│       ├── openapi.yaml                                   [N]
│       └── index.html                                     [N]  ← Swagger UI
│
├── packages/x12-edi-tools/
│   ├── pyproject.toml                                     [M]  ← add eralchemy[dev] extra; bump version
│   ├── src/x12_edi_tools/
│   │   ├── __init__.py                                    [M]  ← additive public exports only
│   │   ├── exceptions.py                                  [M]  ← + RemittanceParseError, ClaimValidationError
│   │   ├── config.py                                      [M]  ← add `ClaimBuildOptions` + `PartitioningStrategy` enum only; `SubmitterConfig` unchanged
│   │   ├── common/enums.py                                [M]  ← + claim/remit enums (new file per enum optional)
│   │   ├── domain/                                        [N]
│   │   │   ├── __init__.py                                [N]
│   │   │   ├── claim.py                                   [N]
│   │   │   ├── patient.py                                 [N]
│   │   │   ├── provider.py                                [N]
│   │   │   ├── payer.py                                   [N]
│   │   │   ├── remittance.py                              [N]
│   │   │   ├── adjustment.py                              [N]
│   │   │   ├── acknowledgement.py                         [N]
│   │   │   ├── submission_batch.py                        [N]
│   │   │   └── audit.py                                   [N]
│   │   ├── models/
│   │   │   ├── segments/                                  [M/N]  ← many new files (Section 2.3)
│   │   │   ├── loops/                                     [M/N]
│   │   │   │   ├── claims/                                [N]
│   │   │   │   └── remittance/                            [N]
│   │   │   └── transactions/
│   │   │       ├── transaction_837i.py                    [N]
│   │   │       ├── transaction_837p.py                    [N]
│   │   │       └── transaction_835.py                     [N]
│   │   ├── parser/transaction_dispatch.py                 [N]
│   │   ├── encoder/claim_encoder.py                       [N]
│   │   ├── builders/                                      [N]
│   │   │   ├── __init__.py
│   │   │   ├── _common.py
│   │   │   ├── claim_837i.py
│   │   │   └── claim_837p.py
│   │   ├── readers/                                       [N]
│   │   │   ├── __init__.py
│   │   │   ├── _common.py
│   │   │   └── remittance_835.py
│   │   ├── validator/rules/                               [N]
│   │   │   ├── __init__.py
│   │   │   ├── rules_837.py
│   │   │   ├── rules_837i.py
│   │   │   ├── rules_837p.py
│   │   │   └── rules_835.py
│   │   ├── payers/base.py                                 [M]  ← extend Protocol
│   │   └── payers/dc_medicaid/                            [M/N]
│   │       ├── profile_837i.py                            [N]
│   │       ├── profile_837p.py                            [N]
│   │       ├── profile_835.py                             [N]
│   │       ├── constants_837.py                           [N]
│   │       └── constants_835.py                           [N]
│   └── tests/
│       ├── fixtures/
│       │   ├── claims/                                    [N]
│       │   │   ├── 837i/synthetic_episode_admission.x12
│       │   │   ├── 837i/synthetic_episode_final.x12
│       │   │   ├── 837i/synthetic_replacement_claim.x12
│       │   │   ├── 837p/synthetic_single_line.x12
│       │   │   └── 837p/synthetic_multi_line.x12
│       │   └── remittance/                                [N]
│       │       ├── 835/synthetic_paid_in_full.x12
│       │       ├── 835/synthetic_denial_group.x12
│       │       ├── 835/synthetic_mixed_adjudication.x12
│       │       └── 835/synthetic_plb_interest_payment.x12
│       ├── test_domain/                                   [N]
│       │   ├── test_claim.py
│       │   ├── test_remittance.py
│       │   └── test_adjustment.py
│       ├── test_builders/                                 [N]
│       │   ├── test_build_837i.py
│       │   └── test_build_837p.py
│       ├── test_readers/                                  [N]
│       │   └── test_read_835.py
│       ├── test_transactions/                             [N]
│       │   ├── test_transaction_837i.py
│       │   ├── test_transaction_837p.py
│       │   └── test_transaction_835.py
│       ├── test_validator/                                [M/N]
│       │   ├── test_rules_837i.py
│       │   ├── test_rules_837p.py
│       │   └── test_rules_835.py
│       ├── test_payers/                                   [M/N]
│       │   ├── test_dc_medicaid_837i.py
│       │   ├── test_dc_medicaid_837p.py
│       │   └── test_dc_medicaid_835.py
│       ├── test_property/                                 [N]
│       │   ├── test_roundtrip_837i.py
│       │   ├── test_roundtrip_837p.py
│       │   └── test_roundtrip_835.py
│       ├── test_smoke_837i.py                             [N]
│       ├── test_smoke_837p.py                             [N]
│       └── test_smoke_835.py                              [N]
│
└── apps/api/
    ├── app/
    │   ├── routers/
    │   │   ├── claims.py                                  [N]
    │   │   ├── remittance.py                              [N]
    │   │   ├── acks.py                                    [N]  ← feature-flagged
    │   │   └── __init__.py                                [M]
    │   ├── schemas/
    │   │   ├── claims.py                                  [N]
    │   │   ├── remittance.py                              [N]
    │   │   └── acks.py                                    [N]
    │   ├── services/
    │   │   ├── claims.py                                  [N]
    │   │   ├── remittance.py                              [N]
    │   │   └── acks.py                                    [N]
    │   └── core/config.py                                 [M]  ← + enable_acks flag
    └── tests/
        ├── routers/
        │   ├── test_claims.py                             [N]
        │   └── test_remittance.py                         [N]
        └── services/
            ├── test_claims_service.py                     [N]
            └── test_remittance_service.py                 [N]
```

### 3.2 Module boundaries and folder ownership

Each row below has exactly one Phase that owns it. Phase boundaries are chosen so concurrent agents never edit the same file.

| Folder / File | Owned by Phase | Modification type |
|---------------|----------------|-------------------|
| `.agents/plans/*` | (outside any phase) | Source-controlled plan; read-only once merged |
| `docs/erd.er`, `docs/api/openapi.yaml` | Phase 9 | Regenerate on docs CI job |
| `src/x12_edi_tools/domain/*` | Phase 1 | New files only |
| `src/x12_edi_tools/models/segments/<new>.py` | Phase 2 | New files; one segment per file |
| `src/x12_edi_tools/models/loops/claims/*.py` | Phase 2 | New files; one loop per file |
| `src/x12_edi_tools/models/loops/remittance/*.py` | Phase 2 | New files; one loop per file |
| `src/x12_edi_tools/models/transactions/transaction_<txn>.py` | Phase 3 | New files |
| `src/x12_edi_tools/models/transactions/functional_group.py` | **Phase 3a** | Refactor: replace hard-coded `Transaction270 \| Transaction271` with the `TransactionModel` alias defined in §2.11 |
| `src/x12_edi_tools/models/transactions/__init__.py` | **Phase 3a** (refactor) + **Phase 3b** (adds 835/837P exports) | Agent G owns the refactor; Agents I/K each add exactly one new export behind review |
| `src/x12_edi_tools/models/__init__.py` | **Phase 3a** (adds `TransactionModel` alias export) + **Phase 7** (adds public surface for 837/835) | Locked during Phases 4–6 |
| `src/x12_edi_tools/parser/x12_parser.py` | **Phase 3a** | Refactor `_parse_transaction_tokens` return type + call `transaction_dispatch`; no behavior change for 270/271 (golden-bytes parity gate) |
| `src/x12_edi_tools/parser/loop_builder.py` | **Phase 3a** | Replace hard-coded `Transaction270 \| Transaction271` return type with `TransactionModel`; introduce per-transaction build dispatch |
| `src/x12_edi_tools/validator/base.py` | **Phase 3a** (type alias swap) + **Phase 4** (ValidationContext wiring per §2.11) | No simultaneous edits |
| `src/x12_edi_tools/parser/transaction_dispatch.py` | Phase 3a | New file |
| `src/x12_edi_tools/encoder/claim_encoder.py` | Phase 3 | New file |
| `src/x12_edi_tools/builders/*` | Phase 3 | New files |
| `src/x12_edi_tools/readers/*` | Phase 3 | New files |
| `src/x12_edi_tools/validator/rules/*` | Phase 4 | New files |
| `src/x12_edi_tools/payers/base.py` | Phase 0 + Phase 5 | Phase 0 extends Protocol (incl. `snip7_enabled`, `build_validation_context`); Phase 5 fills implementations |
| `src/x12_edi_tools/payers/dc_medicaid/*` | Phase 5 | New files |
| `src/x12_edi_tools/convenience.py` | Phase 7 | Single agent appends new public functions |
| `src/x12_edi_tools/__init__.py` | Phase 0 + Phase 7 | Phase 0 reserves import slots; Phase 7 fills them |
| `src/x12_edi_tools/common/enums.py` | Phase 2 | Appended to (single agent per transaction batch) |
| `apps/api/app/services/generator.py` | **Phase 6** (library-first refactor) | Migrate from inline `Interchange` construction to `builders.eligibility_270.build_270`; golden-bytes parity gate (see §2.7, Phase 6) |
| `apps/api/app/services/parser.py` | **Phase 6** (library-first refactor) | Migrate from inline `Transaction271` projection to `readers.eligibility_271.read_271` |
| `apps/api/app/routers/claims.py` | Phase 6 | New file |
| `apps/api/app/routers/remittance.py` | Phase 6 | New file |
| `apps/api/app/routers/__init__.py` | Phase 6 | Single agent merges the two new routers |
| `apps/api/app/schemas/{claims,remittance,acks}.py` | Phase 6 | New files |
| `apps/api/app/services/{claims,remittance,acks}.py` | Phase 6 | New files |
| `tests/fixtures/{claims,remittance}` | Phase 8 | New directories |
| `tests/test_*` (new paths only) | Phase 8 | New files |

### 3.2.1 Shared-file lock matrix (collision-heavy files)

Incorporated from the teammate plan. These files are touched by multiple phases; to prevent merge collisions, each has a single integration owner per phase. No agent other than the named owner may edit these files during the phase window. PRs that touch them are held for the integration PR.

| File | Integration owner |
|------|-------------------|
| `packages/x12-edi-tools/src/x12_edi_tools/__init__.py` | Phase 0 owner (reserves slots), then Phase 7 owner (fills) |
| `packages/x12-edi-tools/src/x12_edi_tools/models/__init__.py` | Phase 3a owner (adds `TransactionModel` alias), then Phase 7 owner (fills 837/835 public surface). **No edits during Phases 1–2 or Phases 4–6.** |
| `packages/x12-edi-tools/src/x12_edi_tools/models/transactions/__init__.py` | Phase 3a owner (refactor for alias); Agents I (835) and K (837P) each append exactly one export via a mini-integration PR reviewed by the Phase 3a owner |
| `packages/x12-edi-tools/src/x12_edi_tools/models/transactions/functional_group.py` | Phase 3a owner only (swap `Transaction270 \| Transaction271` → `TransactionModel`) |
| `packages/x12-edi-tools/src/x12_edi_tools/parser/x12_parser.py` | **Phase 3a owner only** (refactors inline dispatch into `transaction_dispatch`) |
| `packages/x12-edi-tools/src/x12_edi_tools/parser/loop_builder.py` | **Phase 3a owner only** (return-type swap; per-transaction build dispatch) |
| `packages/x12-edi-tools/src/x12_edi_tools/parser/segment_parser.py` | Phase 2 owner only (extensions for new segment-level parsing hooks) |
| `packages/x12-edi-tools/src/x12_edi_tools/validator/base.py` | Phase 3a owner (type alias), then Phase 4 owner (ValidationContext wiring per §2.11). No other edits. |
| `packages/x12-edi-tools/src/x12_edi_tools/validator/x12_validator.py` | Phase 4 owner only (ValidationContext plumbing) |
| `packages/x12-edi-tools/src/x12_edi_tools/payers/base.py` | Phase 0 owner (Protocol extension incl. `snip7_enabled`, `build_validation_context`), then no edits during Phases 1-4 |
| `packages/x12-edi-tools/src/x12_edi_tools/common/enums.py` | Phase 2 claim-owner (Agent D in this plan) only |
| `packages/x12-edi-tools/src/x12_edi_tools/convenience.py` | Phase 7 owner only |
| `apps/api/app/services/generator.py` | Phase 6 owner only (library-first migration + 270 golden-bytes parity gate) |
| `apps/api/app/services/parser.py` | Phase 6 owner only (library-first migration) |
| `apps/api/app/routers/__init__.py` | Phase 6 integration owner only |
| `apps/api/app/core/config.py` | Phase 0 owner (adds flags), then no edits during Phases 1-5 |
| `docs/api/openapi.yaml` | Phase 9 owner only (authoritative spec source) |
| `docs/_assets/doc-theme.css` | Phase 0 owner only (one shared theme) |
| `docs/erd.er` | Phase 9 owner only (regenerates SVG) |

Agents with changes targeting a locked file during another phase's window must file an issue instead of editing. The integration owner batches the change into their next PR. This is strictly enforced in review.

### 3.3 Naming conventions

- **Segments:** `models/segments/<lowercase_segment_id>.py`, class name `<UpperCaseSegmentId>Segment` (e.g., `clm.py` defines `CLMSegment`). One segment per file. Follow the existing 270/271 convention.
- **Loops:** `models/loops/{claims,remittance}/loop_<numeric_id>[_<scope>].py`. Class name `Loop<NumericId>_<TransactionSuffix>` (e.g., `Loop2300_837I`). This mirrors the existing `Loop2000A_270` pattern; the suffix disambiguates when the same loop number appears in 837I vs 837P with different segment ordering.
- **Transactions:** `models/transactions/transaction_<txn_lower>.py`, class name `Transaction<TxnUpper>` (e.g., `Transaction837I`).
- **Builders:** `builders/claim_<txn_lower>.py`, public function `build_<txn_lower>`.
- **Readers:** `readers/<scope>_<txn>.py`, public function `read_<txn>`.
- **Domain objects:** Singular, business-language. `Claim`, not `Claim837I`. `Remittance`, not `RemittanceAdvice`. The wire format is an implementation detail.
- **Validator rules:** `validator/rules/rules_<txn>.py`. Error codes `X12-<TXN>-<NNN>` where NNN is zero-padded.
- **Payer overrides:** `payers/<payer_slug>/profile_<txn>.py` and `payers/<payer_slug>/constants_<family>.py`.
- **Fixtures:** `tests/fixtures/<domain>/<txn>/synthetic_<scenario>.x12`. Every fixture must be synthetic and the filename must include a scenario descriptor.

### 3.4 Code organization strategy

- **One concept per file.** Do not bundle `SV1` and `SV2` into a single module because they "both start with SV." Splitting keeps diffs focused and Grep/Glob cleaner.
- **No cross-file enum leakage.** If an enum is used only inside one segment, declare it in that segment file. Shared enums move to `common/enums.py` only when at least two segments consume them.
- **No inline loop definitions in transaction files.** `Transaction837I` imports from `models/loops/claims/`. This keeps the transaction file under ~80 lines and readable at a glance (matches the 270 pattern).
- **No helper dumping grounds.** `_common.py` exists in `builders/` and `readers/` for genuinely shared envelope construction. Do not use it as a miscellaneous kitchen-sink — if a helper is transaction-specific, it lives in the transaction builder.
- **Strict typing throughout.** `mypy --strict` is enforced in CI. Any new file that fails must be fixed before merge, not suppressed.

### 3.5 Documentation organization strategy

- `docs/architecture.md` — high-level diagram + paragraph summary. Update once, at end of Phase 3, to reference new modules. Do not let it become a changelog; point at CHANGELOG.md for history.
- `docs/erd.md` — human-readable ERD discussion + embedded `erd.svg`. Regenerated when `erd.er` changes.
- `docs/erd.er` — eralchemy DSL source of truth for the logical ERD. Single file, human-edited.
- `docs/erd.svg` — generated. CI regenerates and a pre-commit hook catches drift.
- `docs/erd.html` — standalone HTML wrapper around the SVG with system theme CSS.
- `docs/api/openapi.yaml` — HTTP contract source of truth. Hand-written, reviewed line-by-line. CI validates with `openapi-spec-validator`.
- `docs/api/index.html` — self-contained Swagger UI (via CDN or vendored static assets). Renders `openapi.yaml` in browser.

Regeneration commands:

```bash
# ERD
eralchemy -i docs/erd.er -o docs/erd.svg

# OpenAPI validation
python -m openapi_spec_validator docs/api/openapi.yaml
```

Both are wired into `Makefile` as `make docs` and gated in CI by a single job that fails if `git diff --exit-code docs/erd.svg` is non-empty after regeneration.

### 3.6 Test fixture organization

- `tests/fixtures/claims/<txn>/*.x12` — synthetic outbound claims (encoded, then verified by a decode+compare step in Phase 8)
- `tests/fixtures/remittance/835/*.x12` — synthetic inbound 835s covering: paid-in-full, single-line denial, multi-line mixed adjudication, PLB provider-level adjustment (interest payment), forwarding balance, refund request
- `tests/fixtures/common/envelopes/` — fragments for envelope-only test scenarios (bad ISA, missing IEA, truncated GS, etc.)
- Every fixture has a matching `.expected.json` sibling (generated on first run, committed after human review) documenting what the parser should produce.
- Fixtures are validated on ingest by a conftest fixture that asserts (a) synthetic markers present (`SENDER = SYNTHETIC_TEST`, member IDs in a known test range), (b) no PHI-like names.

### 3.7 Payer override folder strategy

- Every payer is a sibling directory under `payers/`, owned by a single team member or agent.
- Within a payer directory, one file per transaction override (`profile_837i.py`, `profile_837p.py`, `profile_835.py`, `profile_270.py` retroactively split from current `profile.py`).
- Constants files (`constants_837.py`, `constants_835.py`) hold payer-scoped code sets, CARC/RARC filtering lists, accepted POS codes, and signature indicator requirements.
- Payer registration is via `payers/__init__.py::PROFILE_REGISTRY`. New payers add one entry; no dispatch-table sprawl.

### 3.8 How scaffolding prevents agent collision and code duplication

Rules enforced by review:

1. **One file per agent per task.** Phase 3 assigns `claim_837i.py` to Agent D and `claim_837p.py` to Agent E. They do not touch each other's files. Shared helpers go to Phase 2 (already merged) or to `_common.py` via coordinated PR.
2. **`__init__.py` public surface edits happen only in two phases.** Phase 0 reserves placeholder slots as `from __future__ import annotations`-safe `TYPE_CHECKING` imports. Phase 7 flips them to real imports. This prevents Phase 3 agents from fighting over `__all__` ordering.
3. **Segment and loop files are write-once.** If Agent D discovers an omission mid-Phase-3 (e.g., missing `CRC` segment), they file an issue and route the fix through a Phase-2 patch rather than reaching into segments themselves. This keeps Phase 3 diffs small.
4. **Per-agent worktrees.** Each Phase-3 agent runs in an isolated git worktree (`git worktree add ../X12-837I-worktree dev`). Merges happen via PR against a dedicated integration branch per transaction (`feature/837i`, `feature/837p`, `feature/835`) which is rebased into `dev` after Phase 3 closeout.
5. **Fixture isolation.** Phase-8 agents create fixtures under their transaction's subfolder only. Shared envelope fixtures are a single-agent ticket at the start of Phase 8.
6. **No cross-layer reach-through.** Routers import services; services import library public surface. Routers do not import `x12_edi_tools.models.segments.clm`. This rule is lint-enforced via ruff's `tidy-imports` plugin (to be added in Phase 0).
7. **Deterministic ordering in `__all__`.** Alphabetical. Mechanical. No judgment calls — diffs stay clean.

### 3.9 Proprietary companion-guide handling (repo hygiene)

**Issue.** Prior drafts of this plan treated `docs/full_text.txt` — the DC Medicaid 270/271 Companion Guide — as an in-repo authoritative reference. The file itself is marked "Proprietary and Confidential © 2026 Gainwell Technologies. All rights reserved." Committing proprietary third-party content to a publishable repository is a licensing/compliance problem even if the file is useful during implementation. v1.3 closes this.

**Rules.**

1. **Do not commit `docs/full_text.txt` or any other proprietary companion-guide source to the repository.** The file belongs in a local-only directory such as `metadata/` (already gitignored per `CLAUDE.md`).
2. **Plan and code cite the guide by §/table number, not by path.** All `[docs/full_text.txt]` links were removed in v1.3. Normative rules are captured as constants in `payers/dc_medicaid/constants_common.py` with a CG §-reference comment, not as prose quotes.
3. **Verbatim quotes stay out of the repo.** If a rule cannot be captured without quoting, capture it as a test fixture expectation (assert numeric cap, assert enum rejection) rather than a docstring quote.
4. **CI enforcement.** `scripts/check_repo_hygiene.py` (new in Phase 0) greps `docs/`, `packages/`, and `apps/` for the string `Proprietary and Confidential` and fails the build on match. The existing `scripts/check_no_proprietary_content.py` is extended with this pattern if not already present.
5. **Removal step if already staged.** If a branch contains a staged or committed copy of the guide, the branch author rewrites history to drop it before merging to `dev`. Reviewers reject PRs that ship the file.
6. **Downstream references.** `README.md`, `docs/architecture.md`, and `docs/payer-authoring-guide.md` describe the CG as an external reference callers supply; they do not link to a bundled copy.
7. **Release gate.** Phase 9 DoD includes: `scripts/check_repo_hygiene.py` is green against the release tag, and `git log --diff-filter=A --name-only -- docs/full_text.txt` returns no commits after the v1.3 plan merge.

**Scope of this section.** This is a repo-hygiene decision, not a legal review. Releasing `0.3.0` publicly without this clean-up would ship Gainwell content — Phase 9 release gate asserts the hygiene check is green.

---

## 4. Phased Implementation Plan

### Phase 0 — Scaffolding & Placeholder Modules

**Objective:** Create the skeleton so every subsequent phase has an uncontested target.

**Scope:**

- Create all new directories (Section 3.1) as empty packages with `__init__.py` containing `"""TODO: Phase N."""` docstrings.
- Add a single placeholder in each `segments/`, `loops/`, `transactions/`, `builders/`, `readers/`, `validator/rules/`, `domain/` file with a `NotImplementedError`-raising sentinel or a commented contract stub so imports resolve.
- **Land the `ValidationContext` scaffold per §2.11.** Create `validator/context.py` with the `ValidationContext` dataclass and the two Protocol types (`ProviderRegistryLookup`, `MemberRegistryLookup`). No executor logic yet — that lands in Phase 4.
- **Extend `payers/base.py::PayerProfile` Protocol** with `snip7_enabled: bool = False`, `build_validation_context(...) -> ValidationContext`, and the revised `validate(interchange, *, context)` signature plus the four claim/remit methods. Existing `dc_medicaid.profile` gets default `raise NotImplementedError` stubs for the new methods and `snip7_enabled = False` so the 270/271 test suite continues to pass.
- Reserve public-surface slots in `x12_edi_tools/__init__.py` under a `TYPE_CHECKING`-gated import block. Do not yet add to `__all__`.
- Add `eralchemy`, `openapi-spec-validator`, and `hypothesis` to the dev extras in `pyproject.toml`.
- Add `.agents/plans/`, `docs/api/`, and `docs/erd.er` to the repository with the content from this plan set. **Do not add `docs/full_text.txt`** — see §3.9.
- Add `scripts/check_repo_hygiene.py` (per §3.9) and wire it into CI. The check greps `docs/` and `packages/` for `Proprietary and Confidential` and fails on match.
- Extend `Makefile` with `make docs` target wiring eralchemy + OpenAPI validation.

**Deliverables:**

- The repo compiles (`mypy --strict` passes against empty stubs) and tests still pass.
- `make docs` runs end-to-end against the placeholder ERD/OpenAPI content.
- A CI job runs `pytest -x` + `mypy` + `ruff` against `dev` and fails on regressions.

**Ownership boundaries:** 1 agent, 1-2 days. No parallel agents yet — this is the gate.

**Dependencies:** None.

**Risks:**

- Temptation to "just start writing 837I while I'm here." Don't. The scaffold is the contract.

**Definition of Done:**

- [ ] All directories from Section 3.1 exist with valid `__init__.py` files.
- [ ] `mypy --strict` passes.
- [ ] `pytest` passes unchanged.
- [ ] `make docs` produces `docs/erd.svg` and validates `docs/api/openapi.yaml`.
- [ ] PR merged to `dev` with the "scaffold-only" label.

**Parallelism:** Single-threaded. No other agents run until this merges.

---

### Phase 1 — Domain Model Layer

**Objective:** Deliver DB-free business objects for claims, remittances, and their satellites.

**Scope:**

- Implement Pydantic v2 models listed under `domain/` in Section 2.3.
- Every model fully validated: decimal precision, ISO date normalization, required vs. situational fields, NPI Luhn checks where applicable.
- Write `test_domain/` unit tests covering: happy-path construction, edge cases (missing subscriber → patient fallback, multi-line claim with mixed revenue codes), and Decimal rounding.

**Deliverables:**

- `domain/claim.py` exports `Claim`, `ClaimLine`, `ClaimAdjustment`, `ClaimSupportingInfo`, `ClaimType` enum.
- `domain/patient.py` exports `Patient`, `Subscriber`, `PatientRelationship` enum.
- `domain/provider.py` exports `BillingProvider`, `AttendingProvider`, `RenderingProvider`, `ReferringProvider`, `ServiceFacility`, `ProviderRole` enum.
- `domain/payer.py` exports `Payer`, `PayerResponsibility` enum.
- `domain/remittance.py` exports `Remittance`, `RemittancePayment`, `RemittanceClaim`, `RemittanceServiceLine`.
- `domain/adjustment.py` exports `Adjustment`, `AdjustmentGroupCode` enum, `ClaimAdjustmentReasonCode` (CARC) + `RemittanceAdviceRemarkCode` (RARC) as string types with validation.
- `domain/acknowledgement.py` scaffolding (empty classes acceptable; filled in a later scope).
- `domain/submission_batch.py` exports `SubmissionBatch`, `ControlNumbers` (mirrors existing API schema), `ArchiveEntry`.
- `domain/audit.py` exports `TransactionAudit` with correlation_id + non-PHI metrics only.
- Tests: 95%+ line coverage on `domain/`.

**Ownership boundaries:** 3 agents, ~3 days.

- **Agent A:** `domain/claim.py`, `domain/patient.py`, `domain/provider.py`, `domain/payer.py` + tests.
- **Agent B:** `domain/remittance.py`, `domain/adjustment.py` + tests.
- **Agent C:** `domain/acknowledgement.py`, `domain/submission_batch.py`, `domain/audit.py` + tests.

**Dependencies:** Phase 0.

**Risks:**

- Decimal handling drift: all monetary fields must be `Decimal`. Reviewer will grep for `: float` in domain files and reject.
- Enum explosion: keep CARC/RARC as validated strings with a registry lookup, not mega-enums.

**Definition of Done:**

- [ ] All domain modules pass mypy --strict.
- [ ] Coverage ≥ 95% on `src/x12_edi_tools/domain/`.
- [ ] `test_domain/` suite passes.
- [ ] No domain file imports from `models/`, `parser/`, or `encoder/` (verified by a structural test).

**Parallelism:** Agents A, B, C can run fully in parallel in isolated worktrees. No file overlap.

---

### Phase 2 — X12 Segment and Loop Expansion

**Objective:** Land every segment and loop class needed by 837I, 837P, and 835. No transaction or builder logic yet.

**Scope:**

- Author each segment file listed in Section 2.3. Each extends `X12Segment` with `segment_id`, `_element_map`, and field-level Pydantic validation.
- Author each loop file listed in Section 2.3 and 3.1. Loops compose segment classes; no logic beyond structural containment.
- Extend `common/enums.py` with new enum classes (one per appendable PR to avoid merge conflicts).
- Add unit tests at `tests/test_models/` — per-segment round-trip (`from_elements` → `to_elements` → equal), per-loop construction happy-path.

**Deliverables:**

- ~35 new segment files.
- ~40 new loop files across `loops/claims/` and `loops/remittance/`.
- Enum additions in `common/enums.py`.
- Segment/loop unit tests.

**Ownership boundaries:** 3 agents, ~4 days, split by segment family:

- **Agent D:** Claim-scoped segments (CLM, SBR, PAT, OI, CN1, CRC, CR1-3, HI, SV1, SV2, SV3, SVD, PWK, MEA, LX) + claim loops under `loops/claims/`.
- **Agent E:** Shared/cross-cutting segments (AMT, QTY, K3, NTE, HCP, N3/N4 contextual tests) + shared loop helpers.
- **Agent F:** Remittance-scoped segments (SVC, CAS, CLP, PLB, BPR, MIA, MOA) + all loops under `loops/remittance/`.

**Dependencies:** Phase 0. Can start concurrently with Phase 1 if Phase 0 fully merged.

**Risks:**

- Composite element parsing (e.g., SV101-1:2:3) must use the component separator from `Delimiters`. Tests must include custom-delimiter fixtures.
- HI segment carries up to 24 composites — structure must scale without hard-coded array lengths.

**Definition of Done:**

- [ ] Every new segment passes round-trip `from_elements` → `to_elements` equality for at least one sample.
- [ ] Every new loop passes a construction happy-path test.
- [ ] mypy --strict passes.
- [ ] Coverage ≥ 90% across `models/segments/` and `models/loops/claims/`, `models/loops/remittance/`.

**Parallelism:** Agents D, E, F work on disjoint file sets. Single coordination point: `common/enums.py` additions go through a shared PR owned by Agent D (convention).

---

### Phase 3a — 837I Transaction + Parser Dispatch (blocking sequence)

**Objective:** Deliver 837I end-to-end *first* (highest business-value transaction) and land the shared parser dispatch infrastructure that 835 and 837P will depend on.

**Rationale for splitting:** 837I is the home-health revenue-unlock transaction and must ship first. The parser dispatch refactor (`x12_parser.py` → `transaction_dispatch.py`) is a locked-file change with wide blast radius — landing it in a single PR prevents three agents from racing to modify the same file in Phase 3b. This matches the teammate plan's 837I-first sequencing and adds the dispatch consolidation that my prior draft scattered across three agents.

**Scope:**

- Author `builders/_common.py` — envelope helper shared by all builders. Refactor `convenience.build_270` to call it **with a golden-bytes parity test**: capture current 270 output before the refactor, assert byte-for-byte equality after. No behavior change permitted.
- Author `builders/eligibility_270.py::build_270(...)` as the canonical library-level 270 builder. `convenience.build_270` re-exports it. This is the library-side half of the eligibility-services refactor (§2.7); the API migration lands in Phase 6.
- Author `parser/transaction_dispatch.py` with the `(ST01, ST03)` + `GS08` fallback dispatch table from §2.4. Emit `TransactionDispatchError` for ambiguous envelopes.
- Modify `parser/x12_parser.py` minimally to call `transaction_dispatch`. Preserve 270/271 behavior; regression test it via the existing `tests/test_smoke.py`.
- Author `transaction_837i.py` (transaction model class mirroring `Transaction270`).
- Author `parser/loop_builders/claim_837i.py` (if not yet present from Phase 2).
- Author `builders/claim_837i.py::build_837i(claims, *, submitter_config, build_options, profile)` returning `Interchange`.
- Author `encoder/claim_encoder.py` if 837I needs structural hooks beyond the generic `segment_encoder` (e.g., HI composite ordering). Keep scope surgical.
- Unit tests: `test_transactions/test_transaction_837i.py`, `test_builders/test_build_837i.py` — happy paths (admission, final, replacement, void) and two failure modes (missing attending, bad TOB).

**Deliverables:**

- 837I end-to-end library slice.
- `_common.py` envelope helper live and 270 parity verified.
- `transaction_dispatch` live; 270/271 behavior unchanged.
- 75%+ coverage on new code.

**Ownership boundaries:** 2 agents, ~4 days:

- **Agent G (integration):** `parser/transaction_dispatch.py`, `parser/x12_parser.py` refactor, `builders/_common.py`, `encoder/claim_encoder.py`, 270 parity tests. Sole owner of locked files per §3.2.1.
- **Agent H:** `transaction_837i.py`, `builders/claim_837i.py`, 837I tests.

**Dependencies:** Phases 1 and 2.

**Risks:**

- Parser refactor breaks 270/271. Mitigation: golden-bytes parity test is the gate; Agent G's PR does not merge until parity passes.
- 837I home-health situational rules (type-of-bill, statement dates, attending provider for inpatient, HI composite ordering). Mitigation: Phase 4 validator rules catch these; Phase 3a only needs structural correctness.

**Definition of Done:**

- [ ] 837I transaction class builds a complete `Interchange` from admission/final/replacement fixtures.
- [ ] 270/271 tests unchanged and green; byte-for-byte parity on 270 fixture.
- [ ] `(ST01, ST03)` dispatch live with ambiguity handling.
- [ ] Roundtrip invariant holds for ≥1 837I fixture: `parse(encode(build_837i(domain))) == build_837i(domain)`.
- [ ] Coverage ≥ 75% on `builders/claim_837i.py`, `transactions/transaction_837i.py`, `parser/transaction_dispatch.py`.

**Parallelism:** G and H sequenced (G's dispatch refactor must merge before H's 837I builder wires into it). G and H can both work in isolated worktrees; merge order is G→H.

---

### Phase 3b — 835 and 837P Slices (parallel)

**Objective:** Deliver 835 and 837P in parallel tracks after 3a's dispatch infrastructure lands.

**Scope:**

- **835 track:**
  - `transaction_835.py` transaction model.
  - `parser/loop_builders/remittance_835.py`.
  - `readers/remittance_835.py::read_835(payload_or_path)` returning a `RemittanceBatch` projection.
  - `reconciliation/matcher.py` + `reconciliation/result.py` implementing the stateless TRN / CLP01 match heuristics.
  - `test_transactions/test_transaction_835.py`, `test_readers/test_read_835.py`, `test_reconciliation/test_matcher.py`.
- **837P track:**
  - `transaction_837p.py` transaction model.
  - `parser/loop_builders/claim_837p.py`.
  - `builders/claim_837p.py::build_837p(claims, *, submitter_config, build_options, profile)`.
  - `test_transactions/test_transaction_837p.py`, `test_builders/test_build_837p.py`.
- **271 reader track (library-first prep for Phase 6 API migration):**
  - `readers/eligibility_271.py::read_271(parse_result)` — projection from `Transaction271` → the domain shape currently assembled inline in `apps/api/app/services/parser.py`. Matches the existing API projection 1:1.
  - `test_readers/test_read_271.py` — golden-JSON snapshot captured from the current API before migration, asserted after.

**Deliverables:**

- 835 end-to-end (parse → read → reconcile projection).
- 837P end-to-end (build → encode → parse → compare).
- Public functions internal to `builders/` and `readers/` for now; surfaced in Phase 7.
- 70%+ coverage on new code.

**Ownership boundaries:** 3 agents, ~5 days, on disjoint folders:

- **Agent I (835 wire + parser):** `transaction_835.py`, `parser/loop_builders/remittance_835.py`.
- **Agent J (835 reader + reconciliation):** `readers/remittance_835.py`, `reconciliation/*`, 835 tests.
- **Agent K (837P full slice):** `transaction_837p.py`, `parser/loop_builders/claim_837p.py`, `builders/claim_837p.py`, 837P tests.

**Dependencies:** Phase 3a (specifically: `transaction_dispatch.py` merged; `_common.py` envelope helper available).

**Risks:**

- 835 matching heuristics when payers send incomplete TRN references or fuzzy CLP01 values. Mitigation: `reconciliation/matcher.py` returns both matched *and* unmatched buckets; never silently drops remittance claims (teammate-plan callout — kept).
- 837P line-level rendering-provider + modifier rules. Mitigation: Phase 4 validator rules catch situational issues.

**Definition of Done:**

- [ ] 835 fixtures (paid-in-full, partial payment, denial, PLB, unmatched) parse to complete `RemittanceBatch`.
- [ ] `reconcile_835(batch, claims)` returns matched + both unmatched buckets on all fixtures.
- [ ] 837P builds complete `Interchange` for single-line, multi-line, modifier-heavy, and secondary-payer fixtures.
- [ ] Roundtrip invariant holds for ≥1 fixture per transaction.
- [ ] 835 and 837P tracks merge without editing each other's folders.
- [ ] Coverage ≥ 70% on new code.

**Parallelism:** I, J, K fully parallel on disjoint folders. No locked-file edits in this phase.

---

### Phase 4 — Validator and SNIP Rules

**Objective:** SNIP level 1-5 validation for the three new transactions, **plus a SNIP 7 hook** for payers that require business-edit validation against Provider/Member registries (DC Medicaid per CG §3.2).

**Scope:**

- Implement `validator/rules/rules_837.py` (shared 837-family checks: billing provider NPI, subscriber/patient HL hierarchy, CLM control number uniqueness, service line totals vs. claim total).
- Implement `rules_837i.py` (institutional-only: TOB prefix rules, statement-covers-period dates, DRG if applicable, attending provider required for inpatient).
- Implement `rules_837p.py` (professional-only: rendering provider rules, POS validation, CPT/HCPCS code format, NDC rules on 2410, anesthesia units).
- Implement `rules_835.py` (CLP status code ∈ valid set, CAS group codes ∈ {CO,CR,OA,PI,PR}, BPR monetary reconciliation, PLB provider-level totals).
- Implement `validator/snip7.py` — SNIP 7 executor. **Consumes the `ValidationContext` defined in §2.11 (Phase 0 scaffold).** Stateless: reads `context.provider_lookup` / `context.member_lookup` and produces `ValidationError[]` with codes `X12-<TXN>-SNIP7-PROVIDER-NOT-FOUND` / `X12-<TXN>-SNIP7-MEMBER-NOT-FOUND`. When a lookup is `None`, emit a single `X12-SNIP7-SKIPPED-NO-LOOKUP` warning rather than silently no-op'ing — this gives auditors a trail. The library ships no registry; payer profiles and callers inject via `ValidationContext`.
- Extend `validator/x12_validator.py::validate(...)` with the final signature from §2.11: `validate(interchange, *, levels, profile, context=None)`. When `context` is omitted and `profile` is supplied, the validator calls `profile.build_validation_context()` (which DC Medicaid's override may turn into a `PayerConfigurationError`). Level 7 is gated on `profile.snip7_enabled`.
- Unit tests in `test_validator/test_rules_<txn>.py` — each rule has a "pass" test and a "fail" test with the expected error code. Add `test_snip7.py` covering three cases: (a) both lookups supplied, pass + fail fixtures; (b) lookups `None` with soft-skip warning; (c) DC Medicaid profile short-circuits to `PayerConfigurationError` when lookups missing.

**Deliverables:**

- Four new rule files with `~40` rules total (tracked in a `RULES.md` checklist generated from a rule docstring scraper — bonus, not blocking).
- Updated `validate()` entry point that transparently picks up the new rules.
- Error code catalog documented inline.

**Ownership boundaries:** 3 agents, ~3 days:

- **Agent J:** `rules_837.py` + `rules_837i.py`.
- **Agent K:** `rules_837p.py`.
- **Agent L:** `rules_835.py`.

**Dependencies:** Phase 3.

**Risks:**

- Rule proliferation. Keep each rule a single function, ≤40 lines, one side effect (append `ValidationError`). Reject monolithic "check all claim things" rules in review.
- Rule interaction with payer overrides (Phase 5) — Phase 4 rules stay at SNIP 1-5 generic scope; payer-specific conditionals are explicitly out.

**Definition of Done:**

- [ ] Each rule has at least one pass-test and one fail-test.
- [ ] Error code namespacing consistent (`X12-837I-NNN`, etc.).
- [ ] Fixtures from Phase 2 pass validation; intentionally broken fixtures fail with the expected error codes.
- [ ] Coverage ≥ 85% on `validator/rules/`.

**Parallelism:** J, K, L in parallel. Agent J's shared 837 rules land first; K reviews before writing 837P-specific ones.

---

### Phase 5 — DC Medicaid Payer Profile Extension

**Objective:** Working DC Medicaid profile for 837I, 837P, and 835, aligned to the DC Medicaid 270/271 Companion Guide v1.4 (2026-01-28). The guide is a proprietary external reference — consult the locally-held copy under `metadata/` (gitignored per `CLAUDE.md`); see §3.9. Documents the pattern for future payers.

**Scope:**

- Split the existing `payers/dc_medicaid/profile.py` into `profile_270.py` (existing logic moves unchanged) and leave a lean `profile.py` that re-exports for backcompat.
- Author `constants_common.py` carrying DC Medicaid payer-wide values used across all transactions:
  - `PAYER_ID = "DCMEDICAID"` (ISA08, GS03, NM109 in 2100A per CG §2.1.1).
  - Legacy-rejection list: `LEGACY_PAYER_IDS = ("100000", "77033")` — the profile's `validate()` must **reject** interchanges still using these; CG §2.1.1 mandates the migration.
  - Real-time / batch volume limits: `MAX_REALTIME_TRANSACTIONS = 1`, `MAX_BATCH_TRANSACTIONS = 5000` (CG §7.1).
  - Historical inquiry limit: `MAX_HISTORICAL_MONTHS_BACK = 13` (CG §7.1; 270 relevant but lives in common file).
  - SFTP archive filename template: `"VAN-{sender_id}-DCMEDICAID-{date:%Y%m%d}-{time:%H%M%S}-{file_id}-{txn_reference}-{usage}.edi"` (CG A.4).
- Implement `profile_837i.py`, `profile_837p.py`, `profile_835.py` fulfilling the extended Protocol (§2.5, §2.11). Each declares `snip7_enabled = True` and overrides `build_validation_context(...)` so that **if either `provider_lookup` or `member_lookup` is `None`, it raises `PayerConfigurationError("DC Medicaid requires SNIP 7 registry lookups per CG §3.2")`** before the validator runs. This is the hard-fail side of the contract defined in §2.11; the soft-skip path (warning-only) stays on the base validator for payers without SNIP 7. The library ships no registry; callers inject.
- `ClaimBuildOptions` defaults returned by `profile_837i.get_claim_defaults("837I")` and the 837P equivalent set: `partitioning_strategy=SEPARATE_INTERCHANGES`, `max_transactions_per_interchange=5000`, `archive_filename_template=<CG A.4 template>`.
- Author `constants_837.py` (accepted POS, TOB prefixes, signature-on-file indicator requirements, required REF qualifiers) and `constants_835.py` (CARC/RARC filter, PLB reason code semantic mapping).
- Register all three new profile objects in `payers/dc_medicaid/__init__.py`.
- Unit tests in `test_payers/test_dc_medicaid_<txn>.py` — happy path + at least three payer-specific rejection scenarios each, including: legacy payer-ID rejection, SNIP 7 failure when registry lookup misses, and batch >5,000 transactions rejection.

**Deliverables:**

- DC Medicaid override pack for the full new transaction set.
- A `docs/payer-authoring-guide.md` (Phase 9 actually creates this, but the content source is decided here) documenting the override shape.

**Ownership boundaries:** 1 agent, ~2 days.

**Dependencies:** Phase 4.

**Risks:**

- DC Medicaid companion-guide interpretation. When ambiguous, link the guide section number inline and defer to the RCM SME review in the PR.

**Definition of Done:**

- [ ] DC Medicaid 270 tests still pass (no regression from the split).
- [ ] Each new profile implements all four Protocol methods.
- [ ] Fixtures flagged as DC Medicaid trigger the right additional rules.

**Parallelism:** Single agent. This phase is sequential by design because all changes funnel through `payers/dc_medicaid/`.

---

### Phase 6 — FastAPI Routers, Services, and Schemas

**Objective:** HTTP surface for 837I, 837P, 835 under canonical `/api/v1/{eligibility,claims,remittance}/*` namespaces, with deprecated flat eligibility aliases preserved.

**Scope:**

- **Eligibility migration (additive at the URL level, library-first under the hood):** introduce canonical namespaced routes `/api/v1/eligibility/generate`, `/api/v1/eligibility/parse`, `/api/v1/eligibility/validate`. Preserve existing flat `/generate`, `/parse`, `/validate` as deprecated aliases that forward to the new handlers. Mark aliases `deprecated: true` in OpenAPI and schedule removal in `v0.4.0`. No eligibility request/response schema changes.
- **Library-first refactor of existing eligibility services (v1.3 — see §2.7).** Rewrite `apps/api/app/services/generator.py` as a thin wrapper over `builders.eligibility_270.build_270` + `encoder.encode_all`; delete the inline `Interchange`/`FunctionalGroup`/`Transaction270` construction. Rewrite `apps/api/app/services/parser.py` as a thin wrapper over `parser.parse` + `readers.eligibility_271.read_271`. Both refactors are gated by:
  - A golden-JSON snapshot captured **before the change** against the current API responses for the 270 generate + 271 parse fixtures; asserted byte-equal after the change.
  - `docs/api/openapi.yaml` diff against the FastAPI-generated spec (existing CI gate).
  - A new lint rule added to `scripts/check_api_layering.py`: any import from `x12_edi_tools.models.*` inside `apps/api/app/services/` fails CI. Services may import from `x12_edi_tools.builders`, `x12_edi_tools.readers`, `x12_edi_tools.convenience`, `x12_edi_tools.validator`, and `x12_edi_tools.config` only.
- Author `schemas/claims.py`:
  - `GenerateClaimRequest/Response` — discriminated union of `InstitutionalClaim` / `ProfessionalClaim` on `claim_type`.
  - `SubmissionPackageRequest/Response` — same input shape; response adds per-ST `ControlNumbers`, an interchange/group partition manifest honoring the active payer's `PartitioningStrategy` (DC Medicaid → multiple ISA/IEAs; other payers may land a single ISA with multiple GS/GE groups), and archive entries.
  - `ValidateClaimRequest/Response`.
- Author `schemas/remittance.py`:
  - `RemittanceIngestRequest/Response` — envelope-level validation + receipt summary only.
  - `RemittanceParseRequest/Response` — full typed projection.
  - `ReconcileRemittanceRequest/Response` — takes `RemittanceBatch` (or raw 835) + caller-supplied submission claim corpus; returns matched + both unmatched buckets.
- Author `schemas/acks.py` and `schemas/status.py` — real shapes committed even though handlers return 501.
- Author `services/claims.py`, `services/remittance.py`, `services/eligibility.py`, `services/acks.py`, `services/status.py` — thin wrappers over the library that:
  - Translate request → domain using `SubmitterConfig` + new `ClaimBuildOptions`.
  - Partition claims by `claim_type` and dispatch to `build_837i` / `build_837p`. Partitioning is payer-driven: DC Medicaid forces `SEPARATE_INTERCHANGES` (CG §7.1); other payers may elect `SEPARATE_GROUPS` within one ISA. Builders return `list[Interchange]` (see §2.10).
  - Call `read_835` and `reconcile_835` for inbound/reconcile paths.
  - Run `validate()` at SNIP 1-5 + DC Medicaid profile.
  - Collect metrics (`x12_claims_generated_total{txn}`, `x12_remittance_parsed_total`, `x12_remittance_payment_amount` histogram) via the existing Prometheus path.
- Author routers: `routers/eligibility.py`, `routers/claims.py`, `routers/remittance.py`, `routers/acks.py`, `routers/status.py`, `routers/payers.py`.
- Register in `routers/__init__.py` (sole locked file per §3.2.1; single integration PR).
- Author API tests covering all implemented endpoints + explicit 501 assertions on `/acks/ingest` and `/status/resolve`.

**Deliverables — canonical endpoint matrix:**

| Endpoint | Impl status | Notes |
|----------|-------------|-------|
| `POST /api/v1/eligibility/generate` | implemented (canonical) | Alias `POST /generate` deprecated |
| `POST /api/v1/eligibility/parse` | implemented (canonical) | Alias `POST /parse` deprecated |
| `POST /api/v1/eligibility/validate` | implemented (canonical) | Alias `POST /validate` deprecated |
| `POST /api/v1/claims/generate` | **new** | Preview/build; discriminated union on `claim_type` |
| `POST /api/v1/claims/validate` | **new** | Structured or raw 837 input |
| `POST /api/v1/claims/submission-package` | **new** | Export/submission-prep; interchange/group partition manifest (payer-driven — DC Medicaid = per-ISA/IEA) |
| `POST /api/v1/remittance/ingest` | **new** | Envelope-level validation + receipt summary |
| `POST /api/v1/remittance/parse` | **new** | Full typed `RemittanceBatch` projection |
| `POST /api/v1/remittance/reconcile` | **new** | Stateless projection: matched + both unmatched buckets |
| `GET /api/v1/payers` | **new** | List registered profiles |
| `GET /api/v1/payers/{name}` | **new** | Profile defaults + documented overrides |
| `POST /api/v1/acks/ingest` | documented, **501** | Discriminated-union schema covering TA1/999/824/BRR; returns 501 until ack parsing lands. 824 (`005010X186`) prioritized for DC Medicaid per CG Table 1 |
| `POST /api/v1/status/resolve` | documented, **501** | Stateless projection; returns 501 until ack parsing lands |

- Schemas support both snake_case and camelCase via `AliasChoices` (existing pattern).
- Metrics updated as listed above; 501 endpoints emit `x12_planned_endpoint_hits_total{endpoint}` so we can size demand before implementing.
- API contract tests pass against `docs/api/openapi.yaml` via `schemathesis` (optional Phase 9 hardening).

**Ownership boundaries:** 3 agents, ~3 days:

- **Agent M:** `schemas/claims.py`, `services/claims.py`, `routers/claims.py`, `routers/eligibility.py` (migration + aliases), **`services/generator.py` + `services/parser.py` library-first refactor (per §2.7)**, `routers/payers.py`, tests. Golden-JSON snapshot gate is part of Agent M's DoD.
- **Agent N:** `schemas/remittance.py`, `services/remittance.py`, `routers/remittance.py`, tests.
- **Agent O:** `schemas/{acks,status}.py`, `services/{acks,status}.py`, `routers/{acks,status}.py` (501 handlers), OpenAPI stubs, tests asserting 501.

**Dependencies:** Phase 3b (builders + readers + reconciliation), Phase 4 (validator), Phase 5 (payer).

**Risks:**

- Routers must not leak PHI into logs. Reviewer grep check for `logger.info.*patient` / `logger.info.*member`.
- Response size on 835 parse can be large for big batch files. Add an opt-in `summary_only=true` query param on `/remittance/parse` that returns only the projection summary (the `/remittance/ingest` endpoint already fills this role for most callers).
- Eligibility alias rot. Mitigation: alias handlers are 3-line thin redirects to the canonical handler; a single shared implementation keeps them in sync.

**Definition of Done:**

- [ ] OpenAPI spec in `docs/api/openapi.yaml` matches the FastAPI auto-generated spec (CI diff-check).
- [ ] All implemented endpoints have router + service + schema + unit tests.
- [ ] `/acks/ingest` and `/status/resolve` return 501 with the documented schema.
- [ ] Deprecated eligibility aliases still work and are flagged `deprecated: true` in OpenAPI.
- [ ] 85%+ coverage on new router and service code.
- [ ] Prometheus metrics emitted and scrape-verified in tests.
- [ ] `apps/api/app/services/generator.py` and `apps/api/app/services/parser.py` no longer import from `x12_edi_tools.models.*` (lint rule added). Golden-JSON snapshot for the 270 generate + 271 parse responses passes byte-equal before vs. after the refactor.

**Parallelism:** M, N, O in parallel. Integration point: `routers/__init__.py` — single PR that registers all new routers in one diff.

---

### Phase 7 — Convenience Layer and Public Surface

**Objective:** Expose the new capabilities through the documented high-level API.

**Scope:**

- Extend `convenience.py` with:
  - `build_837i(claims, *, config, profile="dc_medicaid", generated_at=None)` (thin re-export of `builders.claim_837i.build_837i`).
  - `build_837p(...)` similarly.
  - `read_835(path_or_string)` returning `RemittanceResultSet`.
- Add a domain-aware template reader: `from_csv(path, *, template="837i")` dispatches to a new `_parse_claim_template` when the template hint matches. This is additive; existing `from_csv` 270 behavior unchanged and tested via regression.
- Update `__init__.py` to export the new names. Update `__all__`.
- Update the library `README.md` with a short "Claims & remittance" section pointing at the convenience functions and the OpenAPI docs.

**Deliverables:**

- Public functions live and documented.
- `README.md` section added.
- Smoke tests: `test_smoke_837i.py`, `test_smoke_837p.py`, `test_smoke_835.py`.

**Ownership boundaries:** 1 agent, ~2 days.

**Dependencies:** Phase 3.

**Risks:**

- Backwards incompatibility with existing `from_csv`. Mitigation: the new `template` kwarg defaults to `"270"` (the existing behavior), making this additive.

**Definition of Done:**

- [ ] All four public convenience functions importable from the top of `x12_edi_tools`.
- [ ] `test_smoke_*` pass.
- [ ] mypy --strict passes on `convenience.py`.
- [ ] README has a 5-line "Claims & remittance" section.

**Parallelism:** Single agent by design (`convenience.py` is a shared file).

---

### Phase 8 — Fixtures, Property-Based Tests, and End-to-End Verification

**Objective:** Production-grade test coverage.

**Scope:**

- Create synthetic fixtures listed in Section 3.6. Each fixture has:
  - A synthetic sender ID (`SENDER = SYNTHETIC_TEST`)
  - Member IDs in the `999999xxx` synthetic range
  - No real names (Faker with a fixed seed)
- Hypothesis strategies for each transaction:
  - `tests/test_property/test_roundtrip_837i.py` — build random valid `Claim`, `build_837i` → encode → parse → compare; assertion is structural equality.
  - Same pattern for 837P and 835.
- E2E API tests under `apps/api/tests/e2e/` that POST to the new endpoints and verify status codes + response shapes.
- Coverage uplift: `make coverage-lib` target ≥ 95%, `make coverage-api` ≥ 85%.
- Golden-bytes regression guard: a test per transaction asserting encoded output matches a committed fixture byte-for-byte for a canonical input.

**Deliverables:**

- Synthetic fixture pack committed.
- Property-based test suite with Hypothesis health-check set to `NON_INTERACTIVE` for CI.
- `make coverage` passes at the stated thresholds.

**Ownership boundaries:** 3 agents, ~3 days:

- **Agent O:** Fixtures + golden-bytes tests for 837I.
- **Agent P:** Fixtures + golden-bytes tests for 837P.
- **Agent Q:** Fixtures + property-based tests for 835 + E2E tests for all three endpoints.

**Dependencies:** Phases 6 and 7.

**Risks:**

- Hypothesis shrinking may take minutes on CI. Cap `max_examples=50` for CI, `200` for nightly.
- Fixture drift. The conftest synthetic-marker check runs on every test session start.

**Definition of Done:**

- [ ] `make test` runs green with the new suites.
- [ ] Coverage thresholds met.
- [ ] Hypothesis nightly run green for 7 consecutive days before release.
- [ ] No PHI-like strings in any fixture (lint check).

**Parallelism:** O, P, Q in parallel.

---

### Phase 9 — Documentation, ERD, OpenAPI Generation and Publishing

**Objective:** Ship docs that match the code.

**Scope:**

- Finalize `docs/erd.md` + `docs/erd.er` + regenerate `docs/erd.svg`, `docs/erd.html`.
- Finalize `docs/api/openapi.yaml` + `docs/api/index.html`.
- CI gate: `make docs` regenerates; `git diff --exit-code` blocks merge if drift.
- `docs/architecture.md` paragraph update referencing new modules (one paragraph, no bloat).
- `CHANGELOG.md` entry for `0.3.0`.
- Tag release `v0.3.0` when all prior phases merged and green.

**Deliverables:**

- Finalized docs set.
- Release tag.

**Ownership boundaries:** 1 agent, ~1 day.

**Dependencies:** All prior phases.

**Risks:**

- OpenAPI drift between hand-written `openapi.yaml` and FastAPI auto-generated spec. CI diff job must catch this.

**Definition of Done:**

- [ ] `docs/erd.svg` in sync with `erd.er`.
- [ ] `openapi.yaml` validates and renders in Swagger UI.
- [ ] `CHANGELOG.md` has a `0.3.0` entry with all three transactions listed.
- [ ] `scripts/check_repo_hygiene.py` green against the release tag (no `Proprietary and Confidential` markers in `docs/`, `packages/`, `apps/`); `git log --diff-filter=A -- docs/full_text.txt` returns empty after the v1.3 plan merge (§3.9).
- [ ] Release tag pushed.

**Parallelism:** Single agent.

---

## Appendix A — Agent Execution Guardrails

Every agent picking up work from this plan must:

1. Read `CLAUDE.md` and this plan end-to-end before writing any code.
2. Work on a dedicated branch named `feature/<phase>-<short-desc>` (e.g., `feature/phase3-837i-builder`).
3. Open a worktree rather than editing in the main checkout.
4. Commit in small, reviewable units — never a single mega-commit per phase.
5. Run `make lint && make typecheck && make test` locally before pushing.
6. Update this plan's tracking section (below) only via an explicit doc PR, not mid-commit.
7. Never log raw X12 payloads, member IDs, names, or filenames.
8. Never introduce dependencies without adding them to the appropriate `pyproject.toml` and justifying in the PR description.
9. If scope grows beyond the phase, stop and file an issue; do not merge cross-phase.

## Appendix B — Phase Tracking

| Phase | Status | Branch | Owner | Started | Merged |
|-------|--------|--------|-------|---------|--------|
| 0 | Not started | — | — | — | — |
| 1 | Not started | — | — | — | — |
| 2 | Not started | — | — | — | — |
| 3 | Not started | — | — | — | — |
| 4 | Not started | — | — | — | — |
| 5 | Not started | — | — | — | — |
| 6 | Not started | — | — | — | — |
| 7 | Not started | — | — | — | — |
| 8 | Not started | — | — | — | — |
| 9 | Not started | — | — | — | — |

## Appendix C — Glossary (implementation-specific)

- **Interchange** — ISA/IEA-wrapped outer envelope containing one or more functional groups.
- **Functional group** — GS/GE-wrapped group of same-ST01 transactions.
- **Transaction** — ST/SE-wrapped payload (e.g., one 837I).
- **Loop** — Ordered segment group within a transaction (e.g., Loop 2300 Claim Information).
- **SNIP** — Strategic National Implementation Process; industry-standard five-level validation taxonomy.
- **TOB** — Type of Bill; four-digit institutional billing code (837I CLM05 / CL103 context).
- **POS** — Place of Service; two-digit professional service code.
- **CARC** — Claim Adjustment Reason Code (CAS02, 835).
- **RARC** — Remittance Advice Remark Code (LQ02, 835).
- **PLB** — Provider Level Adjustment (835).
- **PSC** — Payer Specific Companion guide — the source of payer deltas.
