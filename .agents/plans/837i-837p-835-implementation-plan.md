# 837I / 837P / 835 Implementation Plan

> **Status:** Draft v1.0 — ready for agent execution
> **Owners:** Platform / RCM Core
> **Target release train:** library `0.2.x` → `0.3.0` cut
> **Companion docs:**
> - [`docs/erd.md`](../../docs/erd.md) — logical data model (generated with `eralchemy`)
> - [`docs/api/openapi.yaml`](../../docs/api/openapi.yaml) — HTTP contract
> - [`docs/api/index.html`](../../docs/api/index.html) — rendered Swagger UI
> - [`docs/architecture.md`](../../docs/architecture.md) — current-state architecture

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
- SNIP 1-5 validators per transaction set, plus payer-profile hook points
- DC Medicaid companion-guide override pack (initial payer) with a documented pattern for adding future payers
- FastAPI routers under `/api/v1/claims/...` and `/api/v1/remittance/...`
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
Phase 3 ── Transaction builders + parsers         (3 agents,  5 days, parallel)
Phase 4 ── Validator & SNIP rules                 (3 agents,  3 days, parallel)
Phase 5 ── Payer profile extension (DC Medicaid)  (1 agent,   2 days)
Phase 6 ── FastAPI routers + services + schemas   (2 agents,  3 days, parallel)
Phase 7 ── Convenience layer                      (1 agent,   2 days)
Phase 8 ── Fixtures, property-based tests, E2E    (3 agents,  3 days, parallel)
Phase 9 ── Docs: ERD regen, OpenAPI, Swagger UI   (1 agent,   1 day)
```

Phases can overlap: Phase 1 (domain) unblocks Phases 2, 3, 4 in parallel. Phase 0 must complete before any parallel work begins — it is the scaffold that prevents file collisions.

### 1.6 Key risks and assumptions

| ID | Risk / Assumption | Severity | Mitigation |
|----|-------------------|----------|------------|
| R-1 | Implementation guide ambiguities (e.g., 2300 CLM05 "Facility Code Value" allowed list drifts between 837I and 837P) | High | Keep guides versioned in `metadata/` (local-only), lock the version pin in `IMPLEMENTATION_REFERENCE` constants per transaction, regression-test against recorded fixtures |
| R-2 | Parser dispatch based on `ST01` can mis-route if payers send non-standard envelopes | Medium | Parser falls back to `GenericSegment` for unknown bodies (existing pattern); add a `TransactionParseError` with `st_control_number` context |
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

1. **"Claim generation" and "claim export / submission preparation" are the same endpoint, not two — and 837I and 837P share that endpoint.** The library is stateless; generation *is* the preparation. Exposing separate generate/export endpoints creates ambiguity about where control-number allocation lives. Exposing separate 837I and 837P routes is ceremonial — the request body already carries `claim_type` as a discriminator, and validation dispatches on it internally. I'm collapsing to one endpoint: `POST /claims/generate`, which accepts a discriminated union of `InstitutionalClaim` and `ProfessionalClaim` and returns the X12 payload plus a typed envelope manifest (`ControlNumbers`, `ArchiveEntry[]`). Mixed batches are supported and split into separate GS/GE functional groups so each ST uses the correct implementation reference (`005010X223A2` vs `005010X222A1`). **Cost accepted:** we lose free per-transaction-type operational levers (separate rate limits, per-route metrics). Those are handled via `x12_claims_generated_total{txn}` labels and profile-scoped rate limits instead.

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
│  /api/v1/generate          (existing, 270)                          │
│  /api/v1/parse             (existing, 271)                          │
│  /api/v1/validate          (existing)                               │
│  /api/v1/claims/*          (NEW — unified 837I/P via claim_type)    │
│  /api/v1/remittance/835/*  (NEW)                                    │
│  /api/v1/acks/*            (NEW — scaffold for 999/277CA)           │
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
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────────┐     │
│  │  builders/     │  │   parser/    │  │   encoder/           │     │
│  │  claim_837i.py │  │  dispatches  │  │  serializes typed    │     │
│  │  claim_837p.py │  │  by ST01     │  │  interchange → text  │     │
│  │  remit_835.py  │  │              │  │                      │     │
│  └────────┬───────┘  └──────┬───────┘  └──────────┬───────────┘     │
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
├── config.py                     # SubmitterConfig — extended with claim-scoped defaults
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

**Parser dispatch** is a pure function. `parser/transaction_dispatch.py` exposes `dispatch(st01: str, implementation_reference: str) -> TransactionLoopBuilder`. The existing `x12_parser.parse()` calls this before building the transaction body. Unknown `ST01` falls back to `GenericSegment` (existing behavior preserved).

**Validator layering** stays at three tiers:

1. **SNIP 1** (existing) — ISA/IEA structural integrity; transaction-agnostic
2. **SNIP 2-3** (existing + extended) — Segment/element syntax and code-set validation; per-transaction enum dispatch
3. **SNIP 4-5** (new, per transaction) — Situational and payer-specific rules, pluggable via `validator/rules/rules_<txn>.py` and `payers/<payer>/profile_<txn>.py`

**Logging and correlation IDs** are unchanged. All new code uses `x12_edi_tools._logging.build_log_extra` with the documented non-PHI fields only. Reviewer checklist for new code: zero raw payloads, zero member identifiers, zero names, zero filenames in log statements.

### 2.5 Payer override strategy

Payer profiles are hierarchical, not hard-coded. The existing `PayerProfile` Protocol in `payers/base.py` is extended:

```python
class PayerProfile(Protocol):
    name: str

    # Existing
    def validate(self, interchange: Interchange) -> Sequence[ValidationError]: ...
    def get_defaults(self) -> dict[str, object]: ...

    # NEW
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
3. **Post-encode or on-parse (SNIP 4-5)** — Full validator sweep including payer deltas. For outbound, this is the pre-flight gate before submission. For inbound (835), it is the receipt gate before projection.

The existing `ValidationResult` shape is preserved (severity, level, code, message, location). New transaction-scoped error codes are namespaced: `X12-837I-*`, `X12-837P-*`, `X12-835-*`.

### 2.7 Data flow between domain models, transaction builders/parsers, and APIs

**Outbound flow (claim submission):**

```
POST /api/v1/claims/generate          { claims: [ { claim_type: "INSTITUTIONAL" | "PROFESSIONAL", ... } ] }
  │
  ▼
apps/api/app/schemas/claims.py::GenerateClaimRequest (Pydantic, camelCase-compat; discriminated union on claim_type)
  │
  ▼
apps/api/app/services/claims.py::generate_claims_response()
  │  — partitions by claim_type → domain.InstitutionalClaim[] / ProfessionalClaim[] + SubmitterConfig
  ▼
x12_edi_tools.builders.claim_837.build_837(claims, config, profile)
  │  — dispatches to build_837i / build_837p per partition; emits separate GS/GE groups when mixed
  ▼
x12_edi_tools.validator.validate(interchange, levels=[1..5], profile=...)
  │
  ▼
x12_edi_tools.encoder.encode(interchange, config=config, correlation_id=...)
  │
  ▼
apps/api/app/services/claims.py wraps x12 payload + ControlNumbers + ArchiveEntry[]
  │
  ▼
apps/api/app/schemas/claims.py::GenerateClaimResponse
  │
  ▼
Client receives JSON { x12_content, control_numbers, archive_entries, validation: {...} }
```

**Inbound flow (remittance parsing):**

```
POST /api/v1/remittance/835/parse (multipart .835 or inline payload)
  │
  ▼
apps/api/app/services/remittance.py
  │
  ▼
x12_edi_tools.parser.parse(raw, strict=False, on_error="collect")
  │
  ▼
x12_edi_tools.readers.remittance_835.read_835(parse_result)
  │  — projects Transaction835 → RemittanceResultSet (domain objects)
  ▼
apps/api/app/services/remittance.py wraps projection + parse_errors + summary
  │
  ▼
apps/api/app/schemas/remittance.py::RemittanceParseResponse
  │
  ▼
Client receives JSON { payments: [...], unmatched_claims: [...], summary: {...} }
```

**Acknowledgement / reconciliation flow** is out of scope for Phase-complete delivery but the scaffold lives at `x12_edi_tools.readers.acknowledgement_*` and `apps/api/app/routers/acks.py` behind an `X12_API_ENABLE_ACKS=false` feature flag in `settings`. When enabled, it surfaces 999/277CA parsing results. This prevents future re-scaffolding churn.

### 2.8 Fit alongside existing 270/271 support

The new transactions are purely additive. No existing public API changes. The current `build_270` / `read_271` / `parse` / `encode` / `validate` signatures are preserved. New public functions are added to `x12_edi_tools.__init__` via Phase 7.

Contract tests in `tests/test_smoke.py` continue to exercise 270/271. New contract tests mirror that structure (`test_smoke_837i.py`, `test_smoke_837p.py`, `test_smoke_835.py`) — each ensures the public surface of the respective transaction round-trips through `build → encode → parse → compare`.

### 2.9 Architecture documentation source

The architecture diagram in Section 2.1 is the authoritative high-level view. A detailed module-relationship diagram is rendered by `eralchemy` from the same source file that drives the ERD ([`docs/erd.md`](../../docs/erd.md)). See Section 3.5 below for where the source lives and how it's regenerated.

Swagger/OpenAPI is the authoritative HTTP contract ([`docs/api/openapi.yaml`](../../docs/api/openapi.yaml)). Keep both regenerations gated in CI (see Phase 9).

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
│   │   ├── config.py                                      [M]  ← + claim_scoped defaults (opt-in)
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
| `src/x12_edi_tools/parser/transaction_dispatch.py` | Phase 3 | New file |
| `src/x12_edi_tools/encoder/claim_encoder.py` | Phase 3 | New file |
| `src/x12_edi_tools/builders/*` | Phase 3 | New files |
| `src/x12_edi_tools/readers/*` | Phase 3 | New files |
| `src/x12_edi_tools/validator/rules/*` | Phase 4 | New files |
| `src/x12_edi_tools/payers/base.py` | Phase 0 + Phase 5 | Phase 0 extends Protocol; Phase 5 fills implementations |
| `src/x12_edi_tools/payers/dc_medicaid/*` | Phase 5 | New files |
| `src/x12_edi_tools/convenience.py` | Phase 7 | Single agent appends new public functions |
| `src/x12_edi_tools/__init__.py` | Phase 0 + Phase 7 | Phase 0 reserves import slots; Phase 7 fills them |
| `src/x12_edi_tools/common/enums.py` | Phase 2 | Appended to (single agent per transaction batch) |
| `apps/api/app/routers/claims.py` | Phase 6 | New file |
| `apps/api/app/routers/remittance.py` | Phase 6 | New file |
| `apps/api/app/routers/__init__.py` | Phase 6 | Single agent merges the two new routers |
| `apps/api/app/schemas/{claims,remittance,acks}.py` | Phase 6 | New files |
| `apps/api/app/services/{claims,remittance,acks}.py` | Phase 6 | New files |
| `tests/fixtures/{claims,remittance}` | Phase 8 | New directories |
| `tests/test_*` (new paths only) | Phase 8 | New files |

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

---

## 4. Phased Implementation Plan

### Phase 0 — Scaffolding & Placeholder Modules

**Objective:** Create the skeleton so every subsequent phase has an uncontested target.

**Scope:**

- Create all new directories (Section 3.1) as empty packages with `__init__.py` containing `"""TODO: Phase N."""` docstrings.
- Add a single placeholder in each `segments/`, `loops/`, `transactions/`, `builders/`, `readers/`, `validator/rules/`, `domain/` file with a `NotImplementedError`-raising sentinel or a commented contract stub so imports resolve.
- Extend `payers/base.py::PayerProfile` Protocol with the four new methods (no implementations; existing `dc_medicaid.profile` gets default `raise NotImplementedError` stubs).
- Reserve public-surface slots in `x12_edi_tools/__init__.py` under a `TYPE_CHECKING`-gated import block. Do not yet add to `__all__`.
- Add `eralchemy`, `openapi-spec-validator`, and `hypothesis` to the dev extras in `pyproject.toml`.
- Add `.agents/plans/`, `docs/api/`, and `docs/erd.er` to the repository with the content from this plan set.
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

### Phase 3 — Transaction Builders, Parsers, and Readers

**Objective:** End-to-end typed transactions plus domain ↔ wire translation.

**Scope:**

- Author `transaction_837i.py`, `transaction_837p.py`, `transaction_835.py` (transaction model classes mirroring `Transaction270`).
- Author `parser/transaction_dispatch.py` — pure function that maps `ST01` → transaction-specific loop builder.
- Modify `parser/x12_parser.py` minimally: replace the inline dispatch with a call to `transaction_dispatch`. Preserve the existing 270/271 behavior; regression test it.
- Author `builders/_common.py` — envelope helper shared by all builders. Refactor `convenience.build_270` to call it (no behavior change).
- Author `builders/claim_837i.py::build_837i(claims, config, profile, generated_at)` returning `Interchange`.
- Author `builders/claim_837p.py::build_837p(claims, config, profile, generated_at)` returning `Interchange`.
- Author `readers/remittance_835.py::read_835(payload_or_path)` returning a `RemittanceResultSet` projection.
- Author `encoder/claim_encoder.py` if any transaction needs structure beyond generic `segment_encoder` (e.g., enforcing NM1 short form for payer in 835). Keep scope surgical.
- Unit tests: `test_transactions/`, `test_builders/`, `test_readers/` covering happy paths and two failure modes each.

**Deliverables:**

- Three new `Transaction*` classes.
- `build_837i`, `build_837p`, `read_835` public functions (internal to `builders/` and `readers/` for now; surfaced in Phase 7).
- Parser dispatch live; 270/271 behavior unchanged.
- 70%+ coverage on new code.

**Ownership boundaries:** 3 agents, ~5 days:

- **Agent G:** `transaction_837i.py` + `builders/claim_837i.py` + `test_builders/test_build_837i.py`.
- **Agent H:** `transaction_837p.py` + `builders/claim_837p.py` + `test_builders/test_build_837p.py`.
- **Agent I:** `transaction_835.py` + `readers/remittance_835.py` + `parser/transaction_dispatch.py` + `test_readers/test_read_835.py` + 270/271 regression tests.

**Dependencies:** Phases 1 and 2.

**Risks:**

- Agent I owns the parser dispatch change, which touches an existing file (`x12_parser.py`). Coordinate with Phase 2 agents at end-of-phase merge window; lock the file for a 24-hour PR window.
- `builders/_common.py` refactor of `convenience.build_270` must not change its emitted bytes. Add a golden-bytes fixture test before refactoring and assert equality after.

**Definition of Done:**

- [ ] Every transaction class builds a complete `Interchange` from a representative fixture.
- [ ] 270/271 tests unchanged and green.
- [ ] Roundtrip invariant holds: `parse(encode(build_x(domain))) == build_x(domain)` for ≥1 fixture per transaction.
- [ ] Coverage ≥ 75% on `builders/`, `readers/`, `transactions/`.

**Parallelism:** G, H, I in parallel. Sole serialized dependency: the `x12_parser.py` refactor in Agent I's PR must land before G and H's final integration.

---

### Phase 4 — Validator and SNIP Rules

**Objective:** SNIP level 1-5 validation for the three new transactions.

**Scope:**

- Implement `validator/rules/rules_837.py` (shared 837-family checks: billing provider NPI, subscriber/patient HL hierarchy, CLM control number uniqueness, service line totals vs. claim total).
- Implement `rules_837i.py` (institutional-only: TOB prefix rules, statement-covers-period dates, DRG if applicable, attending provider required for inpatient).
- Implement `rules_837p.py` (professional-only: rendering provider rules, POS validation, CPT/HCPCS code format, NDC rules on 2410, anesthesia units).
- Implement `rules_835.py` (CLP status code ∈ valid set, CAS group codes ∈ {CO,CR,OA,PI,PR}, BPR monetary reconciliation, PLB provider-level totals).
- Extend `validator/x12_validator.py` to dispatch rule modules by transaction.
- Unit tests in `test_validator/test_rules_<txn>.py` — each rule has a "pass" test and a "fail" test with the expected error code.

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

**Objective:** Working DC Medicaid profile for 837I, 837P, and 835. Documents the pattern for future payers.

**Scope:**

- Split the existing `payers/dc_medicaid/profile.py` into `profile_270.py` (existing logic moves unchanged) and leave a lean `profile.py` that re-exports for backcompat.
- Implement `profile_837i.py`, `profile_837p.py`, `profile_835.py` fulfilling the extended Protocol.
- Author `constants_837.py` (accepted POS, TOB prefixes, signature-on-file indicator requirements, required REF qualifiers) and `constants_835.py` (CARC/RARC filter, PLB reason code semantic mapping).
- Register all three new profile objects in `payers/dc_medicaid/__init__.py`.
- Unit tests in `test_payers/test_dc_medicaid_<txn>.py` — happy path + at least three payer-specific rejection scenarios each.

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

**Objective:** HTTP surface for 837I, 837P, 835 under `/api/v1/claims/*` and `/api/v1/remittance/*`.

**Scope:**

- Author `schemas/claims.py` (`GenerateClaimRequest/Response` — discriminated union of `InstitutionalClaim` / `ProfessionalClaim` on `claim_type`; `ValidateClaimRequest/Response`).
- Author `schemas/remittance.py` (`ParseRemittance835Request/Response`, `ReconcileRemittance835Request/Response`).
- Author `schemas/acks.py` scaffold (feature-flagged behind `X12_API_ENABLE_ACKS`).
- Author `services/claims.py` and `services/remittance.py` — thin wrappers over the library that:
  - Translate request → domain
  - Partition claims by `claim_type` and dispatch to `build_837i` / `build_837p` (mixed batches emit separate GS/GE groups); call `read_835` for inbound
  - Run `validate()` at SNIP 1-5 + DC Medicaid profile
  - Collect metrics (segment_count, claim_count, payment_count) via the existing Prometheus path
  - Return response payloads
- Author routers: `routers/claims.py`, `routers/remittance.py`, `routers/acks.py`.
- Register in `routers/__init__.py`.
- Author API tests: `apps/api/tests/routers/test_claims.py`, `test_remittance.py` + service-level tests.

**Deliverables:**

- Four new endpoints live in OpenAPI (unified 837 generate route — see §1.7 disagreement #1):
  - `POST /api/v1/claims/generate` — dispatches to 837I or 837P per-claim via the `claim_type` discriminator in the request body. Mixed batches emit separate GS/GE groups so each ST uses the correct implementation reference.
  - `POST /api/v1/claims/validate` (accepts either 837I or 837P payload, dispatches by declared `claim_type` or by the parsed ST03)
  - `POST /api/v1/remittance/835/parse`
  - `POST /api/v1/remittance/835/reconcile`
- Schemas support both snake_case and camelCase via `AliasChoices` (existing pattern).
- Metrics updated: `x12_claims_generated_total{txn}`, `x12_remittance_parsed_total`, `x12_remittance_payment_amount` histogram.
- API contract tests pass against `docs/api/openapi.yaml` via `schemathesis` (optional Phase 9 hardening).

**Ownership boundaries:** 2 agents, ~3 days:

- **Agent M:** `schemas/claims.py`, `services/claims.py`, `routers/claims.py`, tests.
- **Agent N:** `schemas/remittance.py`, `services/remittance.py`, `routers/remittance.py`, tests. Also owns the acks scaffold (disabled by default).

**Dependencies:** Phase 3 (builders), Phase 4 (validator), Phase 5 (payer).

**Risks:**

- Routers must not leak PHI into logs. Reviewer grep check for `logger.info.*patient` / `logger.info.*member`.
- Response size on 835 parse can be large for big batch files. Add an opt-in `summary_only=true` query param that returns only the projection summary.

**Definition of Done:**

- [ ] OpenAPI spec in `docs/api/openapi.yaml` matches the FastAPI auto-generated spec (CI diff-check).
- [ ] All five endpoints have router + service + schema + unit tests.
- [ ] 85%+ coverage on new router and service code.
- [ ] Prometheus metrics emitted and scrape-verified in tests.

**Parallelism:** M and N in parallel. Integration point: `routers/__init__.py` — single PR that adds both includes in one diff.

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
