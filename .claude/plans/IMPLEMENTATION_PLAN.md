# X12 EDI Parser & Encoder — Implementation Plan (v2)

---

## Index

- [Tech-Stack](#tech-stack)
- [Context](#context)
- [Assumptions](#assumptions)
- [Summary](#summary)
- [Architecture Diagrams](#architecture-diagrams)
- [Recommended Delivery Strategy](#recommended-delivery-strategy)
- [Design Philosophy: Zero Cognitive Load](#design-philosophy-zero-cognitive-load)
- [Configuration System](#configuration-system)
- [Monorepo Scaffolding](#monorepo-scaffolding)
- [Phase 0: Scaffolding + Tooling](#phase-0-scaffolding--tooling)
- [Phase 1: Library — Pydantic Models + Enums](#phase-1-library--pydantic-models--enums)
- [Phase 2: Library — Parser](#phase-2-library--parser)
- [Phase 3: Library — Encoder](#phase-3-library--encoder)
- [Phase 4: Library — Validator + DC Medicaid Profile Pack](#phase-4-library--validator--dc-medicaid-profile-pack)
- [Phase 5: Web Backend — FastAPI API](#phase-5-web-backend--fastapi-api)
- [Phase 6: Web Frontend — React UI](#phase-6-web-frontend--react-ui)
- [Phase 7: Integration + Docker](#phase-7-integration--docker)
- [Phase 8: CI/CD + Docs + Hardening + Release](#phase-8-cicd--docs--hardening--release)
- [Library Public API](#library-public-api)
- [Critical Files Reference](#critical-files-reference)
- [Open Source Considerations](#open-source-considerations)

---

## Tech-Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Product architecture | Reusable Python library plus deployable web application | Keeps domain logic reusable while giving non-technical users a UI |
| Python runtime | Python 3.12 default, support 3.11-3.13 | One stable dev target, broad compatibility in CI |
| Library modeling | Pydantic v2 plus lightweight dataclasses where appropriate | Strong validation and typed X12 models |
| API | FastAPI, Uvicorn, pydantic-settings, python-multipart, openpyxl | Clean request/response contracts and file-processing endpoints |
| Frontend | React, TypeScript, Vite, Tailwind CSS v4 | Good fit if the eligibility dashboard stays interactive |
| UI behavior | React Router for flow, TanStack Table only if the dashboard outgrows a simple table | Keep dependencies earned, not assumed |
| Testing | pytest, httpx/TestClient, Vitest, Playwright, targeted Hypothesis | Balance fast feedback with high-signal regression coverage |
| Quality gates | Ruff, mypy, pytest-cov, pre-commit, detect-secrets | Fast local feedback and basic supply-chain hygiene |
| Packaging | Hatchling, PyPI trusted publishing, GHCR | Clean library release path plus container publishing |
| Runtime packaging | Docker single-container deploy, docker-compose for local dev | Same-origin frontend/API and simpler operations |
| Production hosting | Google Cloud Run for PHI-capable production, Vercel/Render only for non-PHI demos | Keeps compliance-sensitive traffic off hobby hosting |
| Security boundary | External identity layer, PHI-redacted structured logging, no app-managed credentials | Push auth and perimeter concerns into infrastructure |

### Key Technology Decisions

1. **Keep the backend Python-native end to end**. Even if React is used, production runtime remains one Python service plus static assets.
2. **Prefer a thin React stack**. No client-side Excel export in v1, and no animation library unless the workflow proves it is needed.
3. **Keep the library generic where it matters, but fixture-first everywhere else**. Generic envelope/segment design is worthwhile; speculative support for unused loops is not.
4. **Keep the system stateless**. No database, no background queue, and no persistent server-side file retention in the initial architecture.
5. **Make performance a benchmarked target, not a slogan**. Stay synchronous while batch sizes remain small enough; add short-lived async processing only if real measurements justify it.
6. **Delegate auth to infrastructure**. The app should trust a hardened identity boundary rather than owning password or session management.
7. **Two API layers: convenience + granular**. High-level functions (`from_csv`, `build_270`, `read_271`) for agents and non-expert callers. Granular functions (`parse`, `encode`, `validate`) for developers who need full control. Both are first-class.
8. **Auto-correct by default, report what was fixed**. The system normalizes dates, names, whitespace, and defaults silently but transparently — corrections are always surfaced in the response so the user/agent can verify.

---

## Context

**Problem**: A non-technical colleague in DC home healthcare needs to perform bulk Medicaid eligibility checks (270/271 transactions) against Gainwell Technologies' DC MMIS system. Currently this is manual and error-prone. There is no lightweight, open-source, Python-native tool for constructing and parsing X12 270/271 eligibility transactions that complies with the DC Medicaid Companion Guide (v1.4, January 2026, 005010X279A1).

**Solution**: Two deliverables:
1. **`x12-edi-tools`** — A pip-installable Python library for parsing, encoding, and validating X12 transactions. Generic X12-first, but the first production-ready profile pack is `270/271 005010X279A1` for DC Medicaid (Gainwell).
2. **Eligibility Workbench** (`apps/`) — A stateless web application (FastAPI + React) that wraps the library with a drag-and-drop UI for non-technical users doing bulk eligibility workflows.

**Why two parts**: The library is independently useful for developers (pip install, import, done). The web app is the tool for the colleague. Separating them makes the library forkable/reusable without the UI.

---

## Assumptions

1. Python 3.11+ (Pydantic v2 compatibility, modern type hints)
2. Only 270/271 transaction types in v1.0 (extensible for 837/835 later via payer profile packs)
3. DC Medicaid-specific: ISA08/GS03 = "DCMEDICAID", no dependent loops (all members are primary subscribers)
4. Stateless web app — no database, no app-managed user accounts, no app-managed sessions, no server-side file retention
5. Near-zero deployment cost for demos/non-PHI traffic (Vercel + Render for quick start; Cloud Run for production PHI workloads)
6. The companion guide at `metadata/full_text.txt` is the development reference — **it MUST NOT be published in the open-source repo** (it says "Proprietary and Confidential (c) 2026 Gainwell Technologies"). Only original rule abstractions, synthetic fixtures, and instructions for users to obtain payer guides themselves.
7. MIT license, open source from day one
8. **PHI Safety**: This tool processes real Protected Health Information. No PHI in logs, no PHI in test fixtures, no server-side file retention after request completion. All test fixtures must be synthetic.
9. UI import is strictly **template-based** (documented canonical columns), not heuristic column guessing
10. Library is generic X12-first; DC Medicaid rules live in a pluggable **payer profile pack**
11. `parse()` always returns `ParseResult` (wrapping `Interchange` + optional `errors`), never a bare `Interchange` — see [Phase 2](#phase-2-library--parser) for the contract
12. Unknown but well-formed segments are preserved as `GenericSegment` raw tokens — never silently dropped
13. Library base install depends only on `pydantic>=2.0`; Excel (`openpyxl`) and DataFrame (`pandas`) support are optional extras
14. Control numbers (ISA13, GS06, ST02) are auto-generated as zero-padded sequential integers per call, overridable via `SubmitterConfig`
15. Browser-side PHI boundary: no PHI may be persisted to `localStorage`, `sessionStorage`, `IndexedDB`, or any client-side cache — only `SubmitterConfig` settings (which contain no PHI) are persisted client-side
16. Uploaded filenames are treated as PHI and never logged — only MIME type, byte size, and correlation metadata appear in logs
17. Server-side temp files are prohibited — all file processing uses in-memory `SpooledTemporaryFile` (within the 5MB upload cap) and `BytesIO`

---

## Summary

| Phase | What | Test Criteria | Estimated Files |
|-------|------|--------------|-----------------|
| 0 | Scaffolding + Tooling | `pip install -e .[dev]` works, lint passes, no proprietary content in tracked files | ~20 config/init files |
| 1 | Library: Models + Enums | All Pydantic models instantiate, serialize to JSON | ~25 model files |
| 2 | Library: Parser | Parse fixture 270/271 files into typed objects | ~8 parser files |
| 3 | Library: Encoder | Roundtrip: `parse(encode(parse(raw))) == parse(raw)` | ~4 encoder files |
| 4 | Library: Validator + DC Medicaid Profile Pack | SNIP 1-5 + DC Medicaid rules catch known-bad fixtures | ~10 validator files |
| 5 | Web Backend: FastAPI API | All endpoints return correct responses via TestClient | ~18 backend files |
| 6 | Web Frontend: React UI + Settings | Components render, hooks work, pages navigate, settings persist | ~45 frontend files |
| 7 | Integration + Docker | Full flow works in docker-compose | ~6 docker files |
| 8 | CI/CD + Docs + Hardening + Release | GitHub Actions green, README complete, PyPI publishable, property-based tests, OSS docs | ~25 config/doc files |

---

## Architecture Diagrams

### System Architecture — Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           X12-Parser-Encoder Monorepo                           │
│                                                                                 │
│  ┌───────────────────────────────────────────┐  ┌────────────────────────────┐  │
│  │           packages/x12-edi-tools          │  │        apps/ (Web)         │  │
│  │          ─────────────────────────         │  │      ──────────────       │  │
│  │          pip-installable library           │  │   deployable application  │  │
│  │                                           │  │                            │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────────┐ │  │  ┌──────────────────────┐  │  │
│  │  │ Models  │ │ Common  │ │ Exceptions  │ │  │  │      apps/api/       │  │  │
│  │  │         │ │         │ │             │ │  │  │    FastAPI Backend    │  │  │
│  │  │Segments │ │ Enums   │ │ X12Error    │ │  │  │                      │  │  │
│  │  │ Loops   │ │Delimitrs│ │ ParseError  │ │  │  │ Routers  Services    │  │  │
│  │  │ Trans.  │ │ Types   │ │ EncodeError │ │  │  │ Schemas  Middleware  │  │  │
│  │  └────┬────┘ └────┬────┘ └─────────────┘ │  │  │ Templates            │  │  │
│  │       │           │                       │  │  └──────────┬───────────┘  │  │
│  │  ┌────▼───────────▼────┐                  │  │             │ consumes     │  │
│  │  │       Parser        │                  │  │             │ library      │  │
│  │  │                     │                  │  │             │              │  │
│  │  │ ISA Parser          │                  │  │  ┌──────────▼───────────┐  │  │
│  │  │ Tokenizer           │                  │  │  │      apps/web/       │  │  │
│  │  │ Segment Parser      │                  │  │  │   React + Vite +     │  │  │
│  │  │ Loop Builder        │                  │  │  │   Tailwind Frontend  │  │  │
│  │  │ X12 Parser (orch.)  │                  │  │  │                      │  │  │
│  │  └────────┬────────────┘                  │  │  │ Pages  Components    │  │  │
│  │           │                               │  │  │ Hooks  Utils         │  │  │
│  │  ┌────────▼────────────┐                  │  │  └──────────────────────┘  │  │
│  │  │      Encoder        │                  │  │                            │  │
│  │  │                     │                  │  └────────────────────────────┘  │
│  │  │ Segment Encoder     │                  │                                  │
│  │  │ ISA Encoder         │                  │                                  │
│  │  │ X12 Encoder (orch.) │                  │                                  │
│  │  └────────┬────────────┘                  │                                  │
│  │           │                               │                                  │
│  │  ┌────────▼────────────┐                  │                                  │
│  │  │     Validator       │                  │                                  │
│  │  │                     │                  │                                  │
│  │  │ SNIP 1-5 (generic)  │                  │                                  │
│  │  │ X12 Validator(orch.)│                  │                                  │
│  │  └────────┬────────────┘                  │                                  │
│  │           │                               │                                  │
│  │  ┌────────▼────────────┐                  │                                  │
│  │  │    Payer Profiles   │                  │                                  │
│  │  │                     │                  │                                  │
│  │  │ PayerProfile proto. │                  │                                  │
│  │  │ dc_medicaid/        │                  │                                  │
│  │  │   profile.py        │                  │                                  │
│  │  │   constants.py      │                  │                                  │
│  │  │   search_criteria   │                  │                                  │
│  │  └─────────────────────┘                  │                                  │
│  │                                           │                                  │
│  │  ┌─────────────────────┐                  │                                  │
│  │  │   Convenience API   │                  │                                  │
│  │  │  from_csv/excel()   │                  │                                  │
│  │  │  build_270()        │                  │                                  │
│  │  │  read_271()         │                  │                                  │
│  │  └─────────────────────┘                  │                                  │
│  └───────────────────────────────────────────┘                                  │
│                                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │   docker/    │  │    docs/     │  │  .github/    │  │    metadata/       │  │
│  │  Dockerfile  │  │architecture  │  │  workflows/  │  │  full_text.txt     │  │
│  │  compose     │  │payer-packs   │  │  ci/release  │  │  (LOCAL ONLY -     │  │
│  │              │  │frontend-std  │  │  deploy      │  │   NEVER published) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Library Internals — Parser Pipeline

The parser operates as a four-stage pipeline that transforms a raw X12 string into a fully-typed Pydantic model tree:

```
 Raw X12 String
 ┌──────────────────────────────────────────────────────────────┐
 │ ISA*00*          *00*          *ZZ*SENDER         *ZZ*DC... │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Stage A: ISA Parser  (isa_parser.py)                        │
 │                                                              │
 │  • ISA is ALWAYS exactly 106 characters                      │
 │  • Extract delimiters by POSITION (not by splitting):        │
 │      pos 3  → element separator    (*)                       │
 │      pos 82 → repetition separator (^)                       │
 │      pos 104 → sub-element separator (:)                     │
 │      pos 105 → segment terminator  (~)                       │
 │  • Parse ISA fields by fixed-width positions                 │
 │                                                              │
 │  Output: ISASegment + Delimiters                             │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Stage B: Tokenizer  (tokenizer.py)                          │
 │                                                              │
 │  • Split remaining string on segment terminator (~)          │
 │  • For each segment, split on element separator (*)          │
 │  • Strip whitespace/newlines between segments                │
 │  • Preserve empty trailing elements                          │
 │                                                              │
 │  Output: list[SegmentToken(id, elements, position)]          │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Stage C: Segment Parser  (segment_parser.py)                │
 │                                                              │
 │  • Registry maps segment_id → Pydantic model class           │
 │      "NM1" → NM1Segment                                     │
 │      "EB"  → EBSegment                                      │
 │      "DTP" → DTPSegment  ...                                 │
 │  • Each model's from_elements() uses _element_map            │
 │  • Strict mode: raise on unknown segment                     │
 │  • Lenient mode: skip unknown segment                        │
 │                                                              │
 │  Output: list[Pydantic Segment Models]                       │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Stage D: Loop Builder  (loop_builder.py)                    │
 │                                                              │
 │  State machine builds nested HL tree:                        │
 │                                                              │
 │    HL*1**20*1~     ← Level 20: Information Source            │
 │      └─ NM1*PR... ← opens Loop 2100A (Payer)                │
 │    HL*2*1*21*1~    ← Level 21: Information Receiver          │
 │      └─ NM1*1P... ← opens Loop 2100B (Provider)             │
 │    HL*3*2*22*0~    ← Level 22: Subscriber                   │
 │      └─ NM1*IL... ← opens Loop 2100C (Subscriber)           │
 │      └─ EQ*30~    ← opens Loop 2110C (Eligibility Inquiry)  │
 │                                                              │
 │  • SE closes transaction, GE closes group, IEA closes all   │
 │  • LS/LE bracket 2115C/2120C in 271 responses               │
 │                                                              │
 │  Output: Interchange (fully nested typed model tree)         │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Orchestrator  (x12_parser.py)                               │
 │                                                              │
 │  parse(raw, strict=True, on_error="raise") → ParseResult    │
 │                                                              │
 │  Error strategies:                                           │
 │    "raise"   → X12ParseError on first malformed segment      │
 │    "skip"    → silently drop bad transactions                │
 │    "collect" → return valid + list[TransactionParseError]    │
 └──────────────────────────────────────────────────────────────┘
```

### Model Hierarchy — X12 Envelope Nesting

```
Interchange (ISA/IEA envelope)
│
├── ISASegment .............. 16 fixed-width fields, exactly 106 chars
│
├── FunctionalGroup (GS/GE envelope)          ◄── can repeat
│   │
│   ├── GSSegment .......... version, sender/receiver IDs, date/time
│   │
│   ├── Transaction270 (or 271)  (ST/SE envelope)    ◄── can repeat
│   │   │
│   │   ├── STSegment .......... transaction set header (ST01=270|271)
│   │   ├── BHTSegment ......... begin hierarchical transaction
│   │   │
│   │   ├── Loop2000A .......... HL level 20 — Information Source
│   │   │   ├── HLSegment
│   │   │   └── Loop2100A ...... NM1*PR — Payer identification
│   │   │       ├── NM1Segment
│   │   │       ├── REFSegment (opt)
│   │   │       └── PERSegment (opt)
│   │   │
│   │   ├── Loop2000B .......... HL level 21 — Information Receiver
│   │   │   ├── HLSegment
│   │   │   └── Loop2100B ...... NM1*1P — Provider identification
│   │   │       ├── NM1Segment
│   │   │       ├── REFSegment (opt)
│   │   │       └── PRVSegment (opt, 270 only)
│   │   │
│   │   └── Loop2000C .......... HL level 22 — Subscriber        ◄── repeats per patient
│   │       ├── HLSegment
│   │       ├── TRNSegment (opt)
│   │       │
│   │       ├── Loop2100C ...... NM1*IL — Subscriber identification
│   │       │   ├── NM1Segment
│   │       │   ├── REFSegment (opt)
│   │       │   ├── DMGSegment (opt)
│   │       │   ├── DTPSegment (opt)
│   │       │   ├── N3Segment (opt, 271)
│   │       │   ├── N4Segment (opt, 271)
│   │       │   └── AAASegment (opt, 271) .... rejection reason codes
│   │       │
│   │       └── Loop2110C ...... EQ (270) / EB (271) — Eligibility    ◄── repeats
│   │           ├── EQSegment (270) ... service type inquiry
│   │           │   └── DTPSegment .... service date
│   │           │
│   │           ├── EBSegment (271) ... eligibility/benefit info
│   │           │   └── DTPSegment .... eligibility dates
│   │           │
│   │           └── Loop2120C (opt, 271) ... benefit-related entities
│   │               ├── NM1Segment ......... PCP, plan sponsor, etc.
│   │               ├── N3Segment (opt)
│   │               └── N4Segment (opt)
│   │
│   ├── SESegment ........... segment count + control number
│   └── GESegment ........... transaction count + control number
│
└── IEASegment .............. group count + control number
```

### Validator Architecture — SNIP Levels + Payer Profiles

```
                    Interchange Model
                          │
                          ▼
              ┌───────────────────────┐
              │   x12_validator.py    │
              │     (orchestrator)    │
              └───────────┬───────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐
   │ Generic SNIP│ │ Generic SNIP│ │   Payer Profile      │
   │  Levels 1-5 │ │  (contd.)   │ │   (pluggable)        │
   └──────┬──────┘ └──────┬──────┘ └──────────┬────────────┘
          │               │                   │
    ┌─────┴─────┐   ┌─────┴─────┐   ┌────────▼─────────────┐
    │ SNIP 1    │   │ SNIP 4    │   │ PayerProfile Protocol │
    │ Syntax    │   │ Inter-seg │   │                       │
    │ integrity │   │ situation │   │  name: str            │
    │           │   │ rules     │   │  validate() → errors  │
    │• ISA=106  │   │           │   │  get_defaults() →dict │
    │• valid IDs│   │• HL parent│   └────────┬──────────────┘
    │• nesting  │   │• NM1 ctx  │            │
    └───────────┘   │• DTP fmt  │   ┌────────▼──────────────┐
    ┌───────────┐   └───────────┘   │  dc_medicaid/         │
    │ SNIP 2    │   ┌───────────┐   │  profile.py           │
    │ TR3 reqs  │   │ SNIP 5    │   │                       │
    │           │   │ External  │   │• ISA08=DCMEDICAID     │
    │• required │   │ code sets │   │• No HL03=23 (no deps) │
    │  segments │   │           │   │• Max 5000 batch       │
    │• required │   │• state cd │   │• No future svc dates  │
    │  elements │   │• calendar │   │• Max 13mo historical  │
    │• lengths  │   │• gender   │   │• Valid svc type codes │
    │• code vals│   │• NPI Luhn │   │• Search criteria      │
    └───────────┘   │• svc type │   │• AAA reject mappings  │
    ┌───────────┐   └───────────┘   └───────────────────────┘
    │ SNIP 3    │
    │ Balancing │          All results normalized into:
    │           │   ┌──────────────────────────────────┐
    │• SE01 cnt │   │ ValidationError                  │
    │• GE01 cnt │   │   severity: error|warning|info   │
    │• IEA01 cnt│   │   level: snip1..5 | dc_medicaid  │
    │• ctrl nums│   │   code: machine-readable          │
    └───────────┘   │   message: plain English           │
                    │   suggestion: actionable fix        │
                    │   location: ISA.08, Loop2100C.NM1  │
                    └──────────────────────────────────┘
```

### Web Application — Request Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        React Frontend (apps/web/)                       │
│                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ HomePage  │  │ Preview  │  │ Generate │  │ Validate │  │Eligiblty │ │
│  │          │  │  Page    │  │  Result  │  │  Result  │  │Dashboard │ │
│  │ 3 action │  │          │  │          │  │          │  │          │ │
│  │ cards +  │  │ row/seg  │  │ X12 prev │  │ PASS/FAIL│  │ stat crds│ │
│  │ drop zone│  │ preview  │  │ download │  │ issues   │  │ table    │ │
│  └─────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│        │            │             │              │              │       │
│        └──────┬─────┴──────┬──────┴──────┬───────┴──────┬───────┘       │
│               │            │             │              │               │
│               ▼            ▼             ▼              ▼               │
│         useFileUpload  useConvert   useGenerate    useParseX12          │
│         useApi         File         X12            useValidate          │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │  HTTP (same origin)
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (apps/api/)                          │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Middleware Layer                                                 │   │
│  │  • Request correlation ID (X-Correlation-ID)                     │   │
│  │  • PHI-safe structured logging (NEVER logs bodies/names/IDs)     │   │
│  │  • Max upload size enforcement (5MB)                             │   │
│  │  • External auth boundary validation (production)                │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────┬───────────────┼───────────────┬──────────────────┐   │
│  │              │               │               │                  │   │
│  ▼              ▼               ▼               ▼                  ▼   │
│ POST          POST            POST            POST               POST  │
│ /convert      /generate       /validate       /parse             /pipe │
│ .xlsx/.csv    JSON→X12 270    .x12→issues     .x12 271→          line  │
│ →JSON                                         dashboard          (all  │
│                                                                  in 1) │
│  │              │               │               │                  │   │
│  ▼              ▼               ▼               ▼                  ▼   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Service Layer                                                   │   │
│  │                                                                  │   │
│  │  converter.py ─── Template-based import + auto-correction        │   │
│  │  generator.py ─── PatientRecord[] → Interchange → encode()      │   │
│  │  validator.py ─── parse() → validate(snip 1-5 + payer profile)  │   │
│  │  parser.py ────── parse() 271 → structured EligibilityResult[]  │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
│                                 │                                       │
│                                 ▼                                       │
│               ┌─────────────────────────────────┐                      │
│               │  x12-edi-tools Library           │                      │
│               │  (imported as Python dependency) │                      │
│               │                                  │                      │
│               │  parse() → Interchange           │                      │
│               │  encode() → X12 string           │                      │
│               │  validate() → ValidationResult   │                      │
│               │  from_csv/excel → PatientRecord[] │                      │
│               │  build_270() → Interchange        │                      │
│               │  read_271() → EligibilityResult[] │                      │
│               └─────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flows — Three Primary Workflows

```
═══════════════════════════════════════════════════════════════════════════
 WORKFLOW A: Generate 270 Eligibility Inquiry
═══════════════════════════════════════════════════════════════════════════

  User drops .xlsx/.csv          Preview validated rows       Download .x12
  ┌─────────┐                    ┌─────────────────┐         ┌───────────┐
  │ Excel/  │ ──POST /convert──▶ │ PatientRecord[] │──POST──▶│ X12 270   │
  │ CSV     │    auto-correct:   │ + corrections[] │/generate│ content   │
  │ file    │    • dates         │ + warnings[]    │         │ (encoded) │
  └─────────┘    • names→UPPER   └─────────────────┘         └───────────┘
                 • pad member IDs                      auto-computes:
                 • fill defaults                       • ISA/GS/ST envelopes
                 (30, entity=2)                        • HL hierarchy (20→21→22)
                                                       • SE/GE/IEA counts
                                                       • auto-split at 5000

═══════════════════════════════════════════════════════════════════════════
 WORKFLOW B: Validate 270 for Compliance
═══════════════════════════════════════════════════════════════════════════

  User drops .x12 (270)         Parse + validate              Show results
  ┌─────────┐                   ┌──────────────┐              ┌───────────┐
  │ X12 270 │──POST /validate──▶│ SNIP 1: Syntax│────────────▶│ PASS/FAIL │
  │ file    │                   │ SNIP 2: TR3   │             │           │
  └─────────┘                   │ SNIP 3: Counts│             │ Issues[]  │
                                │ SNIP 4: Rules │             │ with plain│
                                │ SNIP 5: Codes │             │ English & │
                                │ DC Medicaid   │             │suggestion │
                                └──────────────┘              └───────────┘

═══════════════════════════════════════════════════════════════════════════
 WORKFLOW C: Parse 271 Eligibility Response
═══════════════════════════════════════════════════════════════════════════

  User drops .x12 (271)        Parse to structured data       Dashboard
  ┌─────────┐                  ┌──────────────────┐          ┌───────────┐
  │ X12 271 │──POST /parse────▶│ Per subscriber:  │─────────▶│ Stat cards│
  │ file    │   on_error=      │ • member_name    │          │ A:34 I:8  │
  └─────────┘   "collect"      │ • member_id      │          │ E:3  N:2  │
                (partial        │ • overall_status │          │           │
                 success)       │ • EB segments[]  │          │ Sortable  │
                                │ • benefits[]     │   ┌─────▶│ table     │
                                │ • AAA errors[]   │   │     │           │
                                └──────────────────┘   │     │ Detail    │
                                                       │     │ expand    │
                                POST /export/xlsx ─────┘     └───────────┘
                                (server-side Excel generation)
```

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  LOCAL DEVELOPMENT                                                   │
│                                                                      │
│  docker-compose.yml                                                  │
│  ┌────────────────────────────────────────────┐                     │
│  │  Single Container (docker/Dockerfile.dev)   │                     │
│  │                                             │                     │
│  │  ┌─────────────────────────────────────┐   │                     │
│  │  │  FastAPI (uvicorn --reload)          │   │  ◄── :8000/api/v1/ │
│  │  │  Serves API endpoints               │   │                     │
│  │  └─────────────────────────────────────┘   │                     │
│  │  ┌─────────────────────────────────────┐   │                     │
│  │  │  Vite Dev Server (npm run dev)      │   │  ◄── :5173/        │
│  │  │  Hot-reload React frontend          │   │                     │
│  │  └─────────────────────────────────────┘   │                     │
│  │                                             │                     │
│  │  Volume mounts: packages/, apps/ (live edit)│                     │
│  └────────────────────────────────────────────┘                     │
│                                                                      │
│  No auth required · No PHI allowed in dev fixtures                   │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│  PRODUCTION (Google Cloud Run — HIPAA-eligible with BAA)             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Cloud IAP / OIDC Proxy                                        │ │
│  │  (External identity boundary — app trusts identity headers)    │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
│                              │                                      │
│  ┌───────────────────────────▼────────────────────────────────────┐ │
│  │  Single Container (docker/Dockerfile)                          │ │
│  │  Multi-stage build:                                            │ │
│  │                                                                │ │
│  │   Stage 1: npm run build → static assets (dist/)              │ │
│  │   Stage 2: pip install x12-edi-tools + api deps               │ │
│  │   Stage 3: FastAPI serves both:                                │ │
│  │            /api/v1/*  → API endpoints                          │ │
│  │            /*         → React static files (same origin)       │ │
│  │                                                                │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │  STATELESS: No DB · No sessions · No temp files          │  │ │
│  │  │  No PHI retained after request completion                │  │ │
│  │  │  PHI-redacted structured logging only                    │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Secret Manager: trading partner credentials (future)                │
│  Cloud Logging: PHI-safe structured JSON logs only                   │
│  Cost: ~$0-5/month (pay-per-use, scale to zero)                     │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│  CI/CD Pipeline (.github/workflows/)                                 │
│                                                                      │
│  PR / Push to main:                                                  │
│  ┌────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌───────┐│
│  │  lint  │  │ typecheck │  │ test-lib   │  │ test-api │  │test-  ││
│  │  ruff  │  │  mypy    │  │ py3.11-13  │  │ httpx    │  │web    ││
│  │        │  │  strict  │  │ cov≥90%    │  │ cov≥85%  │  │vitest ││
│  └────────┘  └──────────┘  │ hypothesis │  └──────────┘  │eslint ││
│                             └────────────┘                └───────┘│
│                                                                      │
│  Tag v*.*.*:                                                         │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────┐               │
│  │ Build wheel│  │ Publish PyPI │  │ Build + push   │               │
│  │ + sdist    │──▶│ (OIDC trust) │  │ Docker → GHCR  │               │
│  └────────────┘  └──────────────┘  └───────┬────────┘               │
│                                            │                         │
│                                            ▼                         │
│                                    Deploy to Cloud Run               │
└─────────────────────────────────────────────────────────────────────┘
```

### Security & PHI Boundaries

```
┌───────────────────────────────────────────────────────────────────────┐
│                          TRUST BOUNDARY                               │
│                                                                       │
│  ┌─────────────┐        ┌──────────────────────────────────────────┐ │
│  │  Internet    │        │  Identity Boundary (Cloud IAP / OIDC)    │ │
│  │  (untrusted) │───────▶│  • Authenticates users                   │ │
│  └─────────────┘        │  • Sets trusted identity headers          │ │
│                          │  • App NEVER manages credentials          │ │
│                          └─────────────────┬────────────────────────┘ │
│                                            │ trusted headers          │
│                                            ▼                          │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Application (Stateless)                                        │ │
│  │                                                                  │ │
│  │  PHI flows IN (request) ──────────▶ PHI flows OUT (response)    │ │
│  │                                                                  │ │
│  │  ┌────────────────────────────────────────────────────────────┐ │ │
│  │  │  NEVER persisted:                                          │ │ │
│  │  │  • No database          • No temp files on disk            │ │ │
│  │  │  • No session storage   • No server-side file retention    │ │ │
│  │  │  • No PHI in logs       • No PHI in error messages         │ │ │
│  │  │  • No PHI in fixtures   • No PHI in published artifacts    │ │ │
│  │  └────────────────────────────────────────────────────────────┘ │ │
│  │                                                                  │ │
│  │  Logs contain ONLY:                                              │ │
│  │  correlation_id, endpoint, status_code, duration,                │ │
│  │  file_metadata (name, size, type), error_codes                  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Build/Publish Boundary                                         │ │
│  │                                                                  │ │
│  │  metadata/full_text.txt ── .gitignore'd, NEVER in wheel/sdist  │ │
│  │  All test fixtures ─────── synthetic only, no real patient data │ │
│  │  Payer rules ───────────── original abstractions, not copied    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Recommended Delivery Strategy

The phases below remain useful, but execution should be managed as vertical slices rather than as directory completion.

1. Deliver slice A first: canonical template intake, row validation, 270 generation, validation of generated output, and file download.
2. Deliver slice B second: 271 upload, tolerant parsing, eligibility dashboard rendering, and Excel export.
3. Generalize only after slices A and B are green with synthetic DC Medicaid fixtures. That is the point to broaden optional segment coverage, deepen payer-profile seams, and expand SNIP rule depth.
4. Treat packaging, OSS ceremony, and stricter quality gates as hardening work once the workflow contract is stable.

This sequencing reduces churn and keeps the library aligned with real operator workflows instead of speculative completeness.

---

## Design Philosophy: Zero Cognitive Load

The primary user is a non-technical healthcare worker doing bulk eligibility checks. Every design decision should be measured against: **"Does this make the user think less?"**

### Principles

1. **One happy path, guided configuration**. The user configures their provider/payer identity once in the Settings panel, then uploads files and gets results. Sensible defaults for everything (DC Medicaid profile, service type code 30, entity type 2, today's date). Settings are required before generation but pre-filled with payer profile defaults — the user confirms, not constructs. No per-row provider fields in the CSV; those come from settings.

2. **The system tells you what to do next**. Every screen has exactly one primary action. After upload: "Preview." After preview: "Generate." After generate: "Download." The UI is a guided corridor, not an open floor plan.

3. **Errors are instructions, not codes**. Never show "SNIP Level 2 Error: E2.05". Show "Row 12: Member ID '1234' is too short — DC Medicaid requires 8 digits." Every error has a plain-English message and a concrete fix suggestion. Group errors by the row/record they affect, not by SNIP level.

4. **Auto-detect, auto-correct, auto-fill**. The system should do work the user would otherwise do manually:
   - **Auto-detect file type** from content, not just extension (ISA header = X12, column headers = spreadsheet)
   - **Auto-correct date formats** — accept `01/15/1985`, `1/15/85`, `19850115`, `1985-01-15` and normalize silently
   - **Auto-uppercase names** — accept `john smith`, output `JOHN SMITH`
   - **Flag short member IDs as a confirmation prompt** — accept `1234567`, surface a warning: *"Member ID '1234567' appears short — DC Medicaid requires 8 digits. Pad to '12345670'?"* Never silently alter payer/member identifiers — in a PHI workflow, changing an identifier could cause a valid member to match the wrong person or fail to match. If the payer profile defines a deterministic padding rule, present it as a user-confirmable suggestion, not an auto-correction
   - **Auto-fill defaults** — service type code defaults to `30` (Health Benefit Plan Coverage), provider entity type defaults to `2` (Non-Person Entity)
   - **Auto-split batches** — >5000 records silently splits into multiple interchanges, user just gets one download

5. **Progressive disclosure**. Show summary first, details on demand. The eligibility dashboard shows status badges (Active/Inactive/Error); click a row to see benefit detail, EB segments, PCP info. The validation result shows PASS/FAIL; expand to see individual issues. Raw X12 is never shown unless explicitly requested.

6. **Drag-and-drop is the entire interface**. The home page IS a drop zone. Drop any supported file and the system figures out what to do: `.xlsx`/`.csv` → generate flow, `.x12`/`.edi` → detect 270 (validate) vs 271 (parse) from the ST01 segment.

### Agent-Driven Automation

The library and API should support an **agent-first** workflow where a Claude Code agent (or any LLM agent) can drive the entire eligibility check pipeline programmatically:

**Library as agent tool surface**:
```python
# An agent can drive the full pipeline with a config object
import x12_edi_tools
from x12_edi_tools.config import SubmitterConfig

config = SubmitterConfig(
    organization_name="ACME HOME HEALTH",
    provider_npi="1234567890",
    trading_partner_id="MYTP123456",
    payer_name="DC MEDICAID",
    payer_id="DCMEDICAID",
    interchange_receiver_id="DCMEDICAID",
)

patients = x12_edi_tools.from_csv("patients.csv")                          # auto-detect, auto-correct
interchange = x12_edi_tools.build_270(patients, config=config, profile="dc_medicaid")
result = x12_edi_tools.validate(interchange, profile="dc_medicaid")

if result.is_valid:
    x12_content = x12_edi_tools.encode(interchange)
    Path("output.x12").write_text(x12_content)
else:
    print(result.human_readable_summary())  # plain English, not SNIP codes
```

**High-level convenience API** (in addition to the granular parse/encode/validate):
- `x12_edi_tools.from_csv(path)` / `from_excel(path)` — template-aware import with auto-correction, returns list of `PatientRecord`
- `x12_edi_tools.build_270(patients, config=..., profile=...)` — one-call 270 generation; `config` (SubmitterConfig) provides provider/payer/envelope values, `profile` provides payer-specific validation rules
- `x12_edi_tools.read_271(path_or_string)` — one-call 271 parsing that returns structured eligibility results, not raw X12 models
- `result.human_readable_summary()` — validation results formatted for humans (or agent context windows), not SNIP-level technical output
- `result.to_dataframe()` — eligibility results as a pandas DataFrame for analysis (pandas is an optional dependency)

**Web API as agent endpoint**:
- All endpoints accept and return JSON — agents don't need to deal with multipart forms
- Add `POST /api/v1/pipeline` — single endpoint that accepts a CSV/Excel file and returns the full result (generated X12 + validation report) in one round-trip. This is the "I don't want to think" endpoint.
- All error responses include `suggestion` fields that an agent can act on programmatically

**MCP tool potential** (future): The library's convenience functions map naturally to MCP tool definitions. An agent with `build_270`, `validate`, and `read_271` tools can autonomously manage eligibility workflows.

---

## Configuration System

The web UI includes a **Settings panel** where the user configures their provider identity, target payer, and envelope defaults **before** uploading files for 270 generation. These values are persisted in browser `localStorage` (no server-side storage — maintaining stateless architecture) and sent with each API request. The library accepts a `SubmitterConfig` dataclass — **no values are hardcoded in library code**.

### Why configuration matters

Without a settings panel, provider-specific values (`provider_npi`, `provider_name`, `trading_partner_id`) would need to appear in every row of the CSV template. That's redundant (same provider for every row in a batch), error-prone, and forces the non-technical user to understand X12 envelope fields. Moving these to settings means the CSV contains **only patient data**.

### Configuration Groups

#### Group 1: Submitter / Provider Identity
*Who you are — set once, used for every 270 file you generate.*

| Setting | Required | Description | Example | X12 Mapping |
|---------|----------|-------------|---------|-------------|
| **Organization Name** | Yes | Agency / provider name | `ACME HOME HEALTH` | NM103 in Loop 2100B |
| **Provider NPI** | Yes | 10-digit National Provider Identifier (Luhn-validated on input) | `1234567890` | NM109 in Loop 2100B (qualifier XX) |
| **Provider Entity Type** | Yes (default: `2`) | `1` = Individual, `2` = Organization | `2` | NM102 in Loop 2100B |
| **Trading Partner ID** | Yes | Payer-assigned ID identifying your organization | `MYTP123456` | ISA06 (padded to 15 chars), GS02 |
| **Provider Taxonomy Code** | No | Optional taxonomy code for PRV segment | `251E00000X` | PRV03 (if present) |
| **Submitter Contact Name** | No | Contact person name | `JANE DOE` | PER02 |
| **Submitter Contact Phone** | No | Contact phone number | `2025551234` | PER04 (qualifier TE) |
| **Submitter Contact Email** | No | Contact email address | `jane@acme.com` | PER06 (qualifier EM) |

#### Group 2: Payer / Receiver Identity
*Who you're sending to — auto-populated from the selected payer profile, editable for overrides.*

| Setting | Required | Description | Default (DC Medicaid) | X12 Mapping |
|---------|----------|-------------|-----------------------|-------------|
| **Payer Profile** | Yes | Selected payer profile (drives all defaults below) | `DC Medicaid` | Profile selection |
| **Payer Name** | Yes | Payer organization name | `DC MEDICAID` | NM103 in Loop 2100A |
| **Payer ID** | Yes | Payer identifier code | `DCMEDICAID` | NM109 in Loop 2100A (qualifier PI) |
| **Interchange Receiver ID** | Yes | Receiver ID in ISA envelope | `DCMEDICAID` | ISA08 (padded to 15 chars) |
| **Receiver ID Qualifier** | Yes (default: `ZZ`) | Qualifier for receiver ID | `ZZ` | ISA07 |

#### Group 3: Interchange / Envelope Defaults
*X12 envelope settings — rarely change but must be configurable, not hardcoded.*

| Setting | Required | Description | Default |  X12 Mapping |
|---------|----------|-------------|---------|--------------|
| **Sender ID Qualifier** | Yes (default: `ZZ`) | Qualifier for sender ID | `ZZ` | ISA05 |
| **Usage Indicator** | Yes (default: `T`) | `T` = Test, `P` = Production | `T` | ISA15 |
| **Acknowledgment Requested** | Yes (default: `0`) | `0` = No, `1` = Yes | `0` | ISA14 |
| **X12 Version** | Read-only | Version/release code (displayed for user awareness) | `005010X279A1` | GS08, ST03 |

#### Group 4: Transaction Defaults
*Defaults applied when the CSV doesn't specify a value per row.*

| Setting | Required | Description | Default | Notes |
|---------|----------|-------------|---------|-------|
| **Default Service Type Code** | Yes (default: `30`) | Default eligibility inquiry type | `30` (Health Benefit Plan Coverage) | Overridable per-row in CSV via `service_type_code` column |
| **Default Service Date** | No | Default if not in CSV | Today's date | Overridable per-row in CSV via `service_date` column |
| **Max Batch Size** | Yes (default: `5000`) | Max transactions per interchange before auto-split | `5000` | DC Medicaid hard limit |

### Configuration UX

1. **Settings panel** accessible via a gear icon in the app header — always one click away.
2. **Config status bar** displayed on the Home Page showing current provider name, NPI, and payer profile so the user always knows what's configured.
3. **Validation gate**: The "Generate 270" flow checks that all required settings are filled before allowing file upload. Missing settings produce a prompt: *"Set up your provider details in Settings before generating files."*
4. **Payer profile selector**: Choosing a payer profile auto-fills Group 2 values. User can override individual fields if needed.
5. **NPI validation**: Provider NPI is Luhn-checked on input with immediate feedback.
6. **localStorage persistence**: Settings survive page refreshes and browser sessions. No server round-trip needed.
7. **Export/Import config** (v1 scope): "Download Settings JSON" / "Upload Settings JSON" button pair on the Settings page. This is critical for production because `localStorage` is fragile — browser updates, clearing data, switching machines, or IT resets can wipe settings and block the entire Generate workflow. Implementation is trivial (JSON serialize/deserialize `SubmitterConfig`) and prevents a complete workflow block.
8. **Environment pre-seeding** (production): For managed deployments, Settings can be pre-seeded from a JSON file or environment variable (`X12_DEFAULT_CONFIG`) so the admin configures once and users don't need to touch Settings. The pre-seeded values populate `localStorage` on first load; user overrides take precedence afterward.

### Configuration in the Library

The library uses a `SubmitterConfig` dataclass (not hardcoded constants) that the API passes through from the frontend:

```python
# x12_edi_tools/config.py
from pydantic import BaseModel, Field

class SubmitterConfig(BaseModel):
    """Provider/submitter identity and envelope settings for 270 generation."""
    # Group 1: Submitter Identity
    organization_name: str                          # NM103 in 2100B
    provider_npi: str                               # NM109 in 2100B
    provider_entity_type: str = "2"                 # NM102 in 2100B
    trading_partner_id: str                         # ISA06, GS02
    provider_taxonomy_code: str | None = None       # PRV03
    contact_name: str | None = None                 # PER02
    contact_phone: str | None = None                # PER04
    contact_email: str | None = None                # PER06

    # Group 2: Payer/Receiver (from profile, overridable)
    payer_name: str                                 # NM103 in 2100A
    payer_id: str                                   # NM109 in 2100A
    interchange_receiver_id: str                    # ISA08
    receiver_id_qualifier: str = "ZZ"               # ISA07

    # Group 3: Envelope
    sender_id_qualifier: str = "ZZ"                 # ISA05
    usage_indicator: str = "T"                      # ISA15
    acknowledgment_requested: str = "0"             # ISA14

    # Group 4: Transaction Defaults
    default_service_type_code: str = "30"
    default_service_date: str | None = None         # None = today
    max_batch_size: int = 5000

    # Group 5: Control Numbers (optional override for orgs maintaining their own sequences)
    isa_control_number_start: int | None = None     # ISA13 — None = auto-generate from 000000001
    gs_control_number_start: int | None = None      # GS06 — None = auto-generate from 1
    st_control_number_start: int | None = None      # ST02 — None = auto-generate from 0001
```

**Control number generation**: By default, the encoder auto-generates zero-padded sequential integers starting at `000000001` (ISA13), `1` (GS06), and `0001` (ST02) per API call. Organizations that maintain their own control-number sequences can override these via `SubmitterConfig`. **Production note**: if a user submits the same batch twice with the same control numbers, the clearinghouse may reject the duplicate — this behavior should be documented in the UI and API responses.

The convenience API and encoder consume this config:

```python
# Usage in convenience API
config = SubmitterConfig(
    organization_name="ACME HOME HEALTH",
    provider_npi="1234567890",
    trading_partner_id="MYTP123456",
    payer_name="DC MEDICAID",
    payer_id="DCMEDICAID",
    interchange_receiver_id="DCMEDICAID",
)
interchange = x12_edi_tools.build_270(patients, config=config, profile="dc_medicaid")
```

### Configuration in the API

The backend receives config as part of the request body — it does **not** read from server-side config files or environment variables for submitter identity. This keeps the API stateless and multi-tenant safe.

```python
# API request schema
class GenerateRequest(BaseModel):
    config: SubmitterConfig
    patients: list[PatientRecord]
    profile: str = "dc_medicaid"
```

### Payer Profile Defaults

Each payer profile provides a `get_defaults()` method that returns the Group 2 (payer/receiver) values and any Group 3/4 overrides. The frontend uses this to auto-populate settings when a payer profile is selected:

```python
# payers/dc_medicaid/profile.py
class DCMedicaidProfile(PayerProfile):
    def get_defaults(self) -> dict:
        return {
            "payer_name": "DC MEDICAID",
            "payer_id": "DCMEDICAID",
            "interchange_receiver_id": "DCMEDICAID",
            "receiver_id_qualifier": "ZZ",
            "default_service_type_code": "30",
            "max_batch_size": 5000,
        }
```

A new `GET /api/v1/profiles/{name}/defaults` endpoint serves these defaults to the frontend.

---

## Monorepo Scaffolding

```
X12-Parser-Encoder/
├── .claude/
│   ├── commands/
│   │   ├── bump-version.md          # /bump-version <major|minor|patch|X.Y.Z>
│   │   ├── update-docs.md           # /update-docs (alias: /refresh-docs)
│   │   └── check-coverage.md        # /check-coverage <python|web|all>
│   └── settings.json
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── ci.yml                   # Lint + test + coverage on PR/push
│       ├── release.yml              # Build + publish to PyPI on tag
│       └── deploy.yml               # Deploy web app on push to main
├── docker/
│   ├── Dockerfile                   # Single container: FastAPI serves API + built frontend
│   ├── Dockerfile.dev               # Dev container with hot-reload
│   └── nginx.conf                   # For split frontend/backend if needed
├── metadata/                        # LOCAL ONLY — .gitignore'd from published artifacts
│   └── full_text.txt                # (existing) DC Medicaid companion guide — PROPRIETARY, NOT SHIPPED
├── packages/
│   └── x12-edi-tools/               # ===== PyPI LIBRARY =====
│       ├── src/
│       │   └── x12_edi_tools/
│       │       ├── __init__.py      # Public API + __version__
│       │       ├── __about__.py     # Version metadata
│       │       ├── py.typed         # PEP 561 marker
│       │       ├── config.py        # SubmitterConfig model (provider/payer/envelope settings)
│       │       ├── exceptions.py
│       │       ├── common/
│       │       │   ├── __init__.py
│       │       │   ├── enums.py     # EntityIdCode, ServiceTypeCode, EligibilityCode, etc.
│       │       │   ├── delimiters.py
│       │       │   └── types.py
│       │       ├── models/
│       │       │   ├── __init__.py
│       │       │   ├── base.py      # X12Segment, X12Loop, X12Envelope base classes
│       │       │   ├── segments/    # One file per segment: isa.py, gs.py, st.py, bht.py,
│       │       │   │   └── ...      #   hl.py, nm1.py, ref.py, dmg.py, dtp.py, eq.py,
│       │       │   │                #   eb.py, aaa.py, trn.py, n3.py, n4.py, per.py,
│       │       │   │                #   prv.py, ls_le.py, se.py, ge.py, iea.py
│       │       │   ├── loops/       # loop_2000a.py, loop_2000b.py, loop_2000c.py,
│       │       │   │   └── ...      #   loop_2100a.py, loop_2100b.py, loop_2100c.py,
│       │       │   │                #   loop_2110c.py, loop_2115c.py, loop_2120c.py
│       │       │   └── transactions/
│       │       │       ├── interchange.py      # ISA/IEA envelope
│       │       │       ├── functional_group.py # GS/GE envelope
│       │       │       ├── transaction_270.py  # Full 270 transaction set
│       │       │       └── transaction_271.py  # Full 271 transaction set
│       │       ├── parser/
│       │       │   ├── __init__.py
│       │       │   ├── isa_parser.py       # Delimiter detection + ISA fixed-width parse
│       │       │   ├── tokenizer.py        # Raw string -> SegmentToken list
│       │       │   ├── segment_parser.py   # SegmentToken -> Pydantic model (registry)
│       │       │   ├── loop_builder.py     # Flat segments -> nested HL tree (state machine)
│       │       │   └── x12_parser.py       # Top-level parse() orchestrator
│       │       ├── encoder/
│       │       │   ├── __init__.py
│       │       │   ├── segment_encoder.py  # Pydantic model -> X12 segment string
│       │       │   ├── isa_encoder.py      # ISA fixed-width encoding (106 chars)
│       │       │   └── x12_encoder.py      # Top-level encode() orchestrator
│       │       ├── validator/
│       │       │   ├── __init__.py
│       │       │   ├── base.py             # ValidationResult, ValidationError, SnipLevel
│       │       │   ├── snip1.py            # Syntax integrity
│       │       │   ├── snip2.py            # TR3 requirement checking
│       │       │   ├── snip3.py            # Balancing (counts, control numbers)
│       │       │   ├── snip4.py            # Inter-segment situational rules
│       │       │   ├── snip5.py            # External code set validation
│       │       │   └── x12_validator.py    # Orchestrator
│       │       └── payers/                 # ===== PAYER PROFILE PACKS =====
│       │           ├── __init__.py
│       │           ├── base.py             # PayerProfile protocol/base class
│       │           └── dc_medicaid/        # First profile pack
│       │               ├── __init__.py
│       │               ├── profile.py      # DC Medicaid rules (ISA08, batch limits, dates, etc.)
│       │               ├── constants.py    # DCMEDICAID IDs, service type codes, AAA mappings
│       │               └── search_criteria.py  # Valid search combinations per companion guide
│       ├── tests/
│       │   ├── conftest.py
│       │   ├── fixtures/               # SYNTHETIC ONLY — no real PHI
│       │   │   ├── README.md           # "All fixtures are synthetic. No real patient data."
│       │   │   ├── 270_realtime_single.x12
│       │   │   ├── 270_batch_multi.x12
│       │   │   ├── 271_active_response.x12
│       │   │   ├── 271_inactive_response.x12
│       │   │   ├── 271_rejected_provider.x12
│       │   │   ├── 271_rejected_subscriber.x12
│       │   │   ├── 270_custom_delimiters.x12
│       │   │   └── 271_multiple_eb_segments.x12
│       │   ├── test_models/
│       │   ├── test_parser/
│       │   ├── test_encoder/
│       │   ├── test_validator/
│       │   ├── test_payers/
│       │   └── test_roundtrip.py
│       ├── pyproject.toml
│       ├── CHANGELOG.md
│       └── README.md                   # Library-specific (shown on PyPI)
│
├── apps/                               # ===== DEPLOYABLE APPLICATIONS =====
│   ├── api/                            # FastAPI backend
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                 # FastAPI app + CORS + routers + middleware
│   │   │   ├── core/
│   │   │   │   ├── config.py           # Settings via pydantic-settings
│   │   │   │   ├── middleware.py       # Request correlation IDs, PHI-safe logging
│   │   │   │   └── logging.py         # Structured logging that NEVER logs PHI
│   │   │   ├── routers/
│   │   │   │   ├── convert.py          # POST /api/v1/convert (import preview)
│   │   │   │   ├── generate.py         # POST /api/v1/generate (accepts SubmitterConfig)
│   │   │   │   ├── validate.py         # POST /api/v1/validate
│   │   │   │   ├── parse.py            # POST /api/v1/parse
│   │   │   │   ├── profiles.py         # GET /api/v1/profiles, GET /api/v1/profiles/{name}/defaults
│   │   │   │   └── export.py           # POST /api/v1/export/xlsx
│   │   │   ├── schemas/
│   │   │   │   ├── config.py           # SubmitterConfig API schema, ProfileDefaults
│   │   │   │   ├── patient.py          # PatientRecord, ConvertResponse
│   │   │   │   ├── generate.py         # GenerateRequest/Response (includes config)
│   │   │   │   ├── validate.py         # ValidateResponse, ValidationIssue
│   │   │   │   ├── parse.py            # ParseResponse, EligibilityResult
│   │   │   │   └── common.py           # ErrorResponse, CorrelationMeta
│   │   │   └── services/
│   │   │       ├── converter.py        # Template-based Excel/TXT -> PatientRecord list
│   │   │       ├── generator.py        # PatientRecord list -> X12 270 (with auto-split)
│   │   │       ├── validator.py        # X12 string -> validation issues
│   │   │       └── parser.py           # X12 271 -> EligibilityResult list
│   │   ├── templates/                  # Canonical import templates
│   │   │   ├── eligibility_template.xlsx
│   │   │   ├── eligibility_template.csv
│   │   │   └── template_spec.md        # Column definitions, rules, examples
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── fixtures/               # SYNTHETIC ONLY
│   │   │   ├── test_convert.py
│   │   │   ├── test_generate.py
│   │   │   ├── test_validate.py
│   │   │   ├── test_parse.py
│   │   │   └── test_export.py
│   │   └── pyproject.toml
│   │
│   └── web/                            # React + Vite + Tailwind frontend
│       ├── src/
│       │   ├── main.tsx
│       │   ├── App.tsx                  # Route definitions
│       │   ├── styles/
│       │   │   ├── tokens.css           # THE single design token file
│       │   │   └── global.css           # @import "tailwindcss" + tokens
│       │   ├── components/
│       │   │   ├── ui/                  # Button, Badge, Card, FileUpload, Input,
│       │   │   │   └── index.ts         #   Modal, Table, Spinner, StatCard, Tabs
│       │   │   ├── layout/             # AppShell, Header, Footer
│       │   │   ├── features/           # ActionCard, FilePreview, X12RawPreview,
│       │   │   │   └── ...             #   ValidationResultsTable, EligibilityDashboard,
│       │   │   │                       #   EligibilityDetailPanel, ExportButton,
│       │   │   │                       #   TemplateDownloader
│       │   │   └── transitions/        # SlideTransition, FadeTransition
│       │   ├── pages/
│       │   │   ├── HomePage.tsx
│       │   │   ├── PreviewPage.tsx
│       │   │   ├── GenerateResultPage.tsx
│       │   │   ├── ValidateResultPage.tsx
│       │   │   ├── EligibilityDashboardPage.tsx
│       │   │   ├── SettingsPage.tsx      # Provider/payer/envelope configuration
│       │   │   └── TemplatesPage.tsx    # Download templates, view column spec
│       │   ├── hooks/
│       │   │   ├── useFileUpload.ts
│       │   │   ├── useSettings.ts       # Read/write settings from localStorage
│       │   │   ├── useApi.ts
│       │   │   ├── useGenerateX12.ts
│       │   │   ├── useValidateX12.ts
│       │   │   ├── useParseX12.ts
│       │   │   └── useConvertFile.ts
│       │   ├── utils/
│       │   │   ├── fileDetection.ts
│       │   │   ├── formatters.ts
│       │   │   ├── npiValidator.ts      # Luhn check for NPI validation
│       │   │   ├── downloads.ts
│       │   │   └── constants.ts
│       │   ├── types/
│       │   │   ├── api.ts
│       │   │   ├── settings.ts          # SubmitterConfig, PayerProfile types
│       │   │   ├── eligibility.ts
│       │   │   └── patient.ts
│       │   └── __tests__/
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       ├── vitest.config.ts
│       └── eslint.config.mjs
│
├── docs/                               # Architecture, API docs, payer-pack docs
│   ├── architecture.md
│   ├── payer-packs.md                  # How to add a new payer profile
│   ├── design-system.md                # Visual + composition source of truth
│   ├── ui-components.md                # Primitive catalog (Button, Table, …)
│   ├── template-spec.md               # Import template column definitions
│   └── deployment.md
├── .pre-commit-config.yaml
├── .gitignore                          # MUST include metadata/ for published artifacts
├── CLAUDE.md                           # Agent rules
├── CONTRIBUTING.md
├── SECURITY.md                         # Vulnerability reporting, PHI handling notes
├── CODE_OF_CONDUCT.md
├── docker-compose.yml                  # Local dev
├── docker-compose.prod.yml             # Production
├── LICENSE                             # (existing) MIT
├── Makefile
├── VERSION                             # Single source of truth for repo-wide version
└── README.md
```

### Key Structural Decision: `packages/` vs `apps/`
- **`packages/`** = publishable artifacts (PyPI library). Independently versionable.
- **`apps/`** = deployable applications (FastAPI API + React UI). Consume the library as a dependency.

---

## Phase 0: Scaffolding + Tooling

**Goal**: Minimal working dev environment — install, lint, test, and run. No proprietary content in tracked files. Defer OSS ceremony (CONTRIBUTING.md, issue templates, custom commands, CODE_OF_CONDUCT.md) to Phase 8.

### Tasks
1. Create all directories and `__init__.py` files
2. Write `packages/x12-edi-tools/pyproject.toml` (hatchling backend, pydantic dep, ruff config, mypy config, pytest config). Define optional extras from day one: `x12-edi-tools[excel]` (adds `openpyxl`), `x12-edi-tools[pandas]` (adds `pandas`), `x12-edi-tools[all]` (both). Base install depends only on `pydantic>=2.0` — this is important for the PyPI story, agent environments, and Docker image size
3. Write `apps/api/pyproject.toml` (fastapi, uvicorn, pydantic-settings, python-multipart, openpyxl deps)
4. Scaffold `apps/web/` with Vite: `npm create vite@latest -- --template react-ts`
5. Install Tailwind CSS v4: `npm install tailwindcss @tailwindcss/vite`
6. Write `.pre-commit-config.yaml` (ruff format, ruff lint, detect-secrets, trailing-whitespace)
7. Write `Makefile` with targets: install, lint, format, test, test-lib, test-api, test-web, clean
8. Write `CLAUDE.md` with project conventions
9. Write `VERSION` file with `0.1.0`
10. **Add `metadata/` to `.gitignore`** to prevent proprietary companion guide from being published
11. Create `tests/fixtures/README.md` in both library and API: "All fixtures are synthetic. No real patient data."
12. Write first synthetic fixture: `270_realtime_single.x12`

### Deferred to Phase 8
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- `.github/ISSUE_TEMPLATE/`, `PULL_REQUEST_TEMPLATE.md`
- `.claude/commands/` (bump-version, update-docs, check-coverage)
- `CHANGELOG.md`
- `docs/design-system.md` + `docs/ui-components.md`

### Verification
- `cd packages/x12-edi-tools && pip install -e ".[dev]"` succeeds
- `ruff check packages/ apps/` passes
- `cd apps/web && npm install && npm run dev` starts Vite
- `make lint` runs without config errors
- `git grep -i "proprietary" -- ':!metadata/'` returns nothing in publishable files

### Test Cases
| # | Test | What it validates |
|---|------|------------------|
| 0.1 | `pip install -e ".[dev]"` + `make lint` pass on clean checkout | Repo bootstrap |
| 0.2 | `metadata/` is gitignored from published sdist/wheel | No proprietary leak |
| 0.3 | No PHI in any fixture file | PHI safety |

---

## Phase 1: Library — Pydantic Models + Enums

**Goal**: The segments and loops required for the DC Medicaid v0.1 workflows are represented as typed models, with clean extension points for optional structures.

### Key Design Decisions

**Separate 270 and 271 models**: The 270 and 271 share loop IDs (2000A, 2100C, etc.) but have different allowed segments. For example, 2100C in a 270 has no N3/N4/AAA, but 2100C in a 271 does. Using distinct `Loop2100C_270` vs `Loop2100C_271` classes gives full type safety.

**Declarative element mapping**: Instead of hand-writing `from_elements()` / `to_elements()` on every segment (20+ files of positional mapping boilerplate, prone to off-by-one bugs), each segment declares a class-level `_element_map` that maps X12 element positions to field names:

```python
class NM1Segment(X12Segment):
    segment_id: ClassVar[str] = "NM1"
    _element_map: ClassVar[dict[int, str]] = {
        1: "entity_identifier_code",
        2: "entity_type_qualifier",
        3: "last_name",
        4: "first_name",
        5: "middle_name",
        8: "id_code_qualifier",
        9: "id_code",
    }
    entity_identifier_code: str
    entity_type_qualifier: str | None = None
    last_name: str | None = None
    # ...
```

The `X12Segment` base class provides generic `from_elements()` and `to_elements()` using this map. Special cases (ISA fixed-width, EB13 composite elements) override the base method. This means adding a new segment is mostly a field declaration — no parser/encoder changes needed.

**Fixture-driven completeness**: Start with the segment and loop set exercised by the synthetic DC Medicaid fixtures. Add optional segments only when a new fixture, rule, or payer-specific behavior proves they are needed.

### Critical Models

**Delimiters** (`common/delimiters.py`):
```python
@dataclass(frozen=True)
class Delimiters:
    element: str = "*"       # ISA position 3
    sub_element: str = ":"   # ISA position 104
    segment: str = "~"       # ISA position 105
    repetition: str = "^"    # ISA position 82 (ISA11)
```

**ISA Segment** — 16 fixed-width fields, total 106 characters. Fields are right-padded (spaces) for alpha, left-padded (zeros) for numeric. Pydantic validators enforce widths.

**NM1 Segment** — Entity identifier (NM101: PR=Payer, 1P=Provider, IL=Subscriber), entity type (1=Person, 2=Non-Person), name fields, ID qualifier (PI, XX, MI, SV), ID code.

**EB Segment** (271 only) — Eligibility status (EB01: 1=Active, 6=Inactive, B=Co-Payment, etc.), service type code (EB03), insurance type (EB04: MC=Medicaid), plan description (EB05), monetary amount (EB07 for co-pays).

**AAA Segment** (271 only) — Request validation: Y/N, reject reason code (51=Provider Not on File, 71=DOB Mismatch, 72=Invalid Member ID, 73=Invalid Name, 75=Not Found), follow-up action code.

**Enums** (`common/enums.py`): `EntityIdentifierCode`, `HierarchicalLevelCode`, `EligibilityInfoCode`, `ServiceTypeCode` (1, 30, 33, 35, 47, 48, 50, 86, 88, 98, AL, MH, UC), `GenderCode`, `AAARejectReasonCode`.

### GenericSegment — Unknown Segment Preservation

Well-formed but unsupported segments (e.g., a payer-specific `III` segment in a real 271) must **never be silently dropped** — that could cause data loss in production X12 files. Instead, they are preserved as `GenericSegment` raw tokens:

```python
class GenericSegment(X12Segment):
    """Preserves unknown but well-formed segments as raw element lists.
    Roundtrips through parse/encode without data loss."""
    segment_id: str                     # e.g., "III"
    raw_elements: list[str]             # original element values

    def to_elements(self) -> list[str]:
        return self.raw_elements
```

This ensures:
- Roundtrip fidelity: `encode(parse(raw))` preserves segments the parser doesn't have typed models for
- Production safety: real-world 271 responses routinely contain payer-specific optional segments
- Lenient mode works without data loss (vs. strict mode which rejects unknown segments)

### TransactionParseError — Concrete Shape for `on_error="collect"`

The `on_error="collect"` mode is the most important error mode for production (one bad transaction in a 5000-record 271 shouldn't discard the other 4999). `TransactionParseError` has a concrete, specified shape:

```python
@dataclass
class TransactionParseError:
    transaction_index: int          # 0-based position in the interchange
    st_control_number: str | None   # ST02 if available
    segment_position: int           # character offset in raw input
    segment_id: str | None          # which segment failed
    raw_segment: str                # the raw segment text that caused the error
    error: str                      # machine-readable error code
    message: str                    # human-readable explanation
    suggestion: str | None          # actionable fix
```

Without this concrete shape, the frontend cannot show actionable per-row errors, and agents cannot programmatically fix and resubmit.

### Files to Create
- `common/delimiters.py`, `common/enums.py`, `common/types.py`
- `models/base.py` (includes `GenericSegment`)
- `models/segments/` — start with `isa`, `gs`, `st`, `bht`, `hl`, `nm1`, `ref`, `dmg`, `dtp`, `eq`, `eb`, `aaa`, `se`, `ge`, `iea`; add `trn`, `n3`, `n4`, `per`, `prv`, `ls_le` as fixtures require them
- `models/loops/` — start with `2000a`, `2000b`, `2000c`, `2100a`, `2100b`, `2100c`, `2110c`; add `2115c` and `2120c` when representative 271 fixtures require them
- `models/transactions/` — interchange.py, functional_group.py, transaction_270.py, transaction_271.py
- `exceptions.py` — X12Error, X12ParseError, X12EncodeError, X12ValidationError; includes `TransactionParseError` dataclass
- `convenience.py` — High-level `from_csv()`, `from_excel()`, `build_270()`, `read_271()` (implementation spans Phases 2-5, but the module and type signatures are defined here)

### Test Cases — Phase 1
| # | Test | What it validates |
|---|------|------------------|
| 1.1 | Instantiate ISASegment with all 16 fields | Pydantic model accepts valid data |
| 1.2 | ISASegment rejects field longer than max width | Pydantic validator enforces constraints |
| 1.3 | ISASegment.from_elements() round-trips with to_elements() | Positional mapping is correct |
| 1.4 | NM1Segment with NM101=PR, NM102=2 | Payer entity model works |
| 1.5 | NM1Segment with NM101=IL, NM102=1, full name fields | Subscriber entity model works |
| 1.6 | EBSegment with EB01=1 (Active), EB04=MC | Eligibility active status |
| 1.7 | EBSegment with EB01=B, EB07="5.00" | Co-payment with monetary amount |
| 1.8 | AAASegment with AAA01=N, AAA03=72 | Invalid Member ID rejection |
| 1.9 | Loop2000A_270 nests Loop2000B which nests Loop2000C | Hierarchy instantiation works |
| 1.10 | Transaction270 contains ST, BHT, Loop2000A, SE | Full transaction model |
| 1.11 | Interchange wraps FunctionalGroup wraps Transaction | Full envelope nesting |
| 1.12 | Each ServiceTypeCode enum value matches Appendix A.1 | Enum completeness |
| 1.13 | All segment from_elements() handle trailing empty elements as None | Optional field handling |
| 1.14 | Delimiters dataclass is frozen/immutable | Safety check |
| 1.15 | GenericSegment preserves segment_id and raw_elements | Unknown segment preservation |
| 1.16 | GenericSegment.to_elements() returns raw_elements unchanged | Roundtrip fidelity for unknowns |
| 1.17 | TransactionParseError contains all required fields (transaction_index, st_control_number, segment_position, segment_id, raw_segment, error, message, suggestion) | Error shape completeness |

---

## Phase 2: Library — Parser

**Goal**: `x12_edi_tools.parse(raw_string)` returns a fully-typed `Interchange` model, and the web workflow has a transaction-scoped error collection path for malformed bulk responses.

### Architecture

The parser operates in 4 phases:

**A. Delimiter Detection + ISA Extraction** (`isa_parser.py`):
- ISA is always exactly 106 characters
- Position 3 -> element separator, position 82 -> repetition separator, position 104 -> sub-element separator, position 105 -> segment terminator
- ISA is parsed positionally (NOT by splitting on delimiters, since ISA defines the delimiters)

**B. Tokenization** (`tokenizer.py`):
- Split remaining string on segment terminator
- For each segment, split on element separator -> `SegmentToken(segment_id, elements, position)`
- Strip whitespace/newlines between segments

**C. Segment Parsing** (`segment_parser.py`):
- Registry maps segment_id -> Pydantic model class
- Each model's `from_elements()` handles its own positional mapping
- Unknown segments: raise in strict mode, **preserve as `GenericSegment` in lenient mode** (never silently drop — see Phase 1 for rationale)

**D. Loop/Hierarchy Building** (`loop_builder.py`):
- State machine walks flat segment list, builds nested loop tree
- HL segment's HL02 (parent) + HL03 (level code) define the tree: 20->21->22
- NM1 opens 2100x sub-loops, EQ opens 2110C (270), EB opens 2110C (271), LS/LE bracket 2115C/2120C
- SE closes transaction, GE closes group, IEA closes interchange

**E. Orchestrator** (`x12_parser.py`):
```python
def parse(
    raw: str,
    *,
    strict: bool = True,
    on_error: Literal["raise", "skip", "collect"] = "raise",
) -> ParseResult
```

**`parse()` always returns `ParseResult`** — never a bare `Interchange`. This is the locked contract; all examples, endpoints, and tests must reference `ParseResult` consistently.

```python
@dataclass
class ParseResult:
    interchange: Interchange              # the parsed interchange (may be partial in "collect" mode)
    errors: list[TransactionParseError]   # empty when all transactions parsed successfully
    warnings: list[str]                   # non-fatal issues (e.g., unknown segments preserved as GenericSegment)
```

**All three error modes ship in v1** — they share the same parse pipeline with different error-handling strategies at the orchestrator level; the incremental cost of each mode is minimal:

- `on_error="raise"` (default) — strict mode for library consumers. Any malformed segment/transaction raises `X12ParseError`. `result.errors` is always empty (because an exception was thrown first).
- `on_error="skip"` — return only valid transactions, silently discard malformed ones. Serves a real production need: batch processing where the caller wants only valid transactions and will handle failures out-of-band. `result.errors` is empty (errors were discarded, not collected).
- `on_error="collect"` — parse everything possible, return both valid transactions and a list of `TransactionParseError` objects with location metadata (see Phase 1 for the concrete shape). This is what the web API uses so one bad transaction in a 5000-record 271 doesn't discard the other 4999. `result.errors` contains one entry per failed transaction.

### Files to Create
- `parser/isa_parser.py`, `parser/tokenizer.py`, `parser/segment_parser.py`, `parser/loop_builder.py`, `parser/x12_parser.py`
- `tests/fixtures/` — 8 synthetic fixture files (see scaffolding above)

### Test Cases — Phase 2
| # | Test | What it validates |
|---|------|------------------|
| 2.1 | detect_delimiters() extracts *, ~, :, ^ from standard ISA | Delimiter detection |
| 2.2 | detect_delimiters() on ISA with pipe delimiter | Custom delimiters |
| 2.3 | detect_delimiters() raises on input < 106 chars | Error handling |
| 2.4 | detect_delimiters() raises on input not starting with "ISA" | Error handling |
| 2.5 | tokenize() splits 3-segment string into 3 SegmentTokens | Basic tokenization |
| 2.6 | tokenize() strips newlines between segments | Whitespace handling |
| 2.7 | tokenize() preserves empty trailing elements | Element preservation |
| 2.8 | parse_segment() maps NM1 token to NM1Segment | Registry dispatch |
| 2.9 | parse_segment() raises on unknown segment ID (strict) | Strict mode |
| 2.10 | parse_segment() preserves unknown segment ID as GenericSegment (lenient) | Lenient mode — unknown segments preserved, not dropped |
| 2.11 | parse() on 270_realtime_single.x12 -> correct ISA08="DCMEDICAID" | Full parse |
| 2.12 | parse() on 270_realtime_single.x12 -> subscriber NM1 has correct name | Field access |
| 2.13 | parse() on 270_batch_multi.x12 -> correct transaction count | Batch handling |
| 2.14 | parse() on 271_active_response.x12 -> EB01="1" | Response parsing |
| 2.15 | parse() on 271_rejected_subscriber.x12 -> AAA03="72" | Reject code parsing |
| 2.16 | parse() on 271_multiple_eb_segments.x12 -> multiple EB in loop_2110c list | Repeating loops |
| 2.17 | parse() on 270_custom_delimiters.x12 -> correct field values | Custom delimiter support |
| 2.18 | parse() on completely garbled input -> X12ParseError | Error handling |
| 2.19 | Loop builder builds 3-level HL tree (20->21->22) correctly | Hierarchy building |
| 2.20 | Loop builder handles LS/LE wrapper in 271 2115C/2120C | Bounded loop support |
| 2.21 | parse(on_error="collect") with one malformed transaction preserves valid neighboring transactions and returns error metadata | Partial success |
| 2.22 | parse(on_error="skip") with one malformed transaction returns only valid transactions | Skip mode |
| 2.23 | Multiple transaction sets in one interchange | Multi-ST handling |
| 2.24 | parse() with unknown but well-formed segment in lenient mode -> GenericSegment preserved in output, roundtrips through encode | Unknown segment fidelity |
| 2.25 | parse() returns ParseResult (not bare Interchange) in all error modes | Return contract |
| 2.26 | ParseResult.warnings populated when GenericSegment tokens are created | Warning surfacing |

---

## Phase 3: Library — Encoder

**Goal**: `x12_edi_tools.encode(interchange)` returns a valid X12 ANSI string.

### Architecture

- **segment_encoder.py**: Calls `segment.to_elements()`, joins with element separator, trims trailing empties, appends segment terminator
- **isa_encoder.py**: Special handling — pads each field to fixed width, outputs exactly 106 characters
- **x12_encoder.py**: Walks the Interchange tree depth-first, encodes each segment. Auto-computes SE01 (segment count), GE01 (transaction count), IEA01 (group count).

### Key Design Decisions

**Auto-compute counts during encoding**: If a user builds an Interchange programmatically, they might get SE01/GE01/IEA01 wrong. Computing them during encoding prevents SNIP Level 3 errors. The original parsed values are still on the model for inspection.

**Auto-generate control numbers**: ISA13, GS06, and ST02 are auto-generated as zero-padded sequential integers (`000000001`, `1`, `0001`) per encode call. If the caller provides explicit values via `SubmitterConfig.isa_control_number_start` / `gs_control_number_start` / `st_control_number_start`, those override the auto-generation. This matters for production: clearinghouse deduplication, audit trails, and retry semantics all key on control numbers.

**Split-output semantics**: When a batch exceeds `max_batch_size`, the encoder returns a **list of X12 strings** (one per interchange), not a single concatenated blob. Each interchange gets its own ISA/IEA envelope with unique control numbers. The web API offers a **zip download** containing one `.x12` file per interchange plus a `manifest.json` indicating split count, record ranges per file, and control number mappings. This is the safe default — if Gainwell's MMIS accepts multiple ISA/IEA envelopes in one file, that can be added as an option later, but users must always know exactly which patients are in which file.

```python
def encode(
    interchange: Interchange | list[Interchange],
    *,
    delimiters: Delimiters | None = None,
) -> str | list[str]:
    """Single interchange -> single string. List of interchanges -> list of strings."""
```

### Files to Create
- `encoder/segment_encoder.py`, `encoder/isa_encoder.py`, `encoder/x12_encoder.py`

### Test Cases — Phase 3
| # | Test | What it validates |
|---|------|------------------|
| 3.1 | encode_isa() output is exactly 106 characters | Fixed-width |
| 3.2 | ISA06 is right-padded to 15 characters with spaces | Padding |
| 3.3 | ISA13 is left-padded to 9 digits with zeros | Numeric padding |
| 3.4 | encode_segment() trims trailing empty elements | Clean output |
| 3.5 | encode_segment() handles composite elements (EB13) with sub-element separator | Composite encoding |
| 3.6 | encode() auto-computes SE01 = correct segment count | Count auto-computation |
| 3.7 | encode() auto-computes GE01 = correct transaction count | Count auto-computation |
| 3.8 | encode() auto-computes IEA01 = correct group count | Count auto-computation |
| 3.9 | **Roundtrip**: parse(raw) -> encode -> parse -> models are equal | Identity test |
| 3.10 | **Roundtrip**: encode(model) -> parse -> encode -> strings are equal | Identity test |
| 3.11 | Roundtrip on every fixture file | Comprehensive roundtrip |
| 3.12 | encode() with custom delimiters produces correct output | Delimiter flexibility |
| 3.13 | encode() auto-generates ISA13 as zero-padded 9-digit sequential number | Control number generation |
| 3.14 | encode() with SubmitterConfig control number overrides uses provided values | Control number override |
| 3.15 | encode() with list of interchanges returns list of strings, each with unique ISA13 | Split encoding |
| 3.16 | encode() preserves GenericSegment raw elements in output | Unknown segment roundtrip |

---

## Phase 4: Library — Validator + DC Medicaid Profile Pack

**Goal**: `x12_edi_tools.validate(interchange, profile="dc_medicaid")` returns a `ValidationResult`.

### SNIP Level Implementations (Generic)

| Level | File | What it checks |
|-------|------|----------------|
| 1 | `snip1.py` | ISA is 106 chars; valid segment IDs; ISA/IEA, GS/GE, ST/SE properly nested |
| 2 | `snip2.py` | Required segments present (ISA, GS, ST, BHT, HL, NM1); required elements non-empty; element lengths within bounds; valid code values (BHT02=13/11, GS08=005010X279A1) |
| 3 | `snip3.py` | SE01 matches segment count; GE01 matches transaction count; IEA01 matches group count; control number cross-references (ISA13=IEA02, GS06=GE02, ST02=SE02) |
| 4 | `snip4.py` | HL parent references valid; HL03 sequence (20->21->22); NM101 matches loop context; DTP format matches qualifier |
| 5 | `snip5.py` | Valid US state codes; valid calendar dates; valid gender codes; NPI Luhn check; service type codes |

### Payer Profile Pack Pattern

**Why**: DC Medicaid rules are not hardcoded into the generic SNIP validator, but v1 should keep this seam intentionally thin. A single concrete `dc_medicaid` implementation is enough; avoid designing a broader plugin ecosystem until a second payer exists. This still gives the project:
- Other payers can be added by creating new directories under `payers/`
- The core library stays generic
- Users can write custom profiles

```python
# payers/base.py
class PayerProfile(Protocol):
    name: str
    def validate(self, interchange: Interchange) -> list[ValidationError]: ...
    def get_defaults(self) -> dict: ...  # Default ISA/GS values for generation
```

**DC Medicaid Profile** (`payers/dc_medicaid/profile.py`):
- ISA08=DCMEDICAID (padded to 15); GS03=DCMEDICAID
- NM103 in 2100A = "DC MEDICAID"; NM109 in 2100A = "DCMEDICAID"
- No HL03=23 (no dependents — all enrollees are primary subscribers)
- Real-time: max 1 transaction; Batch: max 5000 transactions
- No future service dates; historical max 13 months
- Service type codes from Appendix A.1 (1, 30, 33, 35, 47, 48, 50, 86, 88, 98, AL, MH, UC)
- Valid search criteria combinations per Section 7.2 of companion guide
- AAA reject code mappings: 51 (provider not on file), 71 (DOB mismatch), 72 (invalid member ID), 73 (invalid name), 75 (subscriber not found)

### Validation Result Shape (normalized)
```python
@dataclass
class ValidationError:
    severity: Literal["error", "warning", "info"]
    level: SnipLevel | str        # "snip1", "snip2", ... or "dc_medicaid"
    code: str                      # Machine-readable code
    message: str                   # Human-readable message
    location: str | None           # e.g., "ISA.08", "Loop2100C.NM1.09"
    segment_id: str | None
    element: str | None
    suggestion: str | None         # Actionable fix suggestion
    profile: str | None            # Which payer profile flagged this
```

### Public API
```python
def validate(
    interchange: Interchange,
    *,
    levels: set[SnipLevel] | None = None,
    profile: str | PayerProfile | None = None,  # "dc_medicaid" or custom
    custom_rules: list[ValidationRule] | None = None,
) -> ValidationResult
```

### Files to Create
- `validator/base.py`, `validator/snip1.py` through `snip5.py`, `validator/x12_validator.py`
- `payers/base.py`, `payers/dc_medicaid/profile.py`, `payers/dc_medicaid/constants.py`, `payers/dc_medicaid/search_criteria.py`

### Test Cases — Phase 4
| # | Test | What it validates |
|---|------|------------------|
| 4.1 | SNIP 1: Missing ISA -> error | Syntax integrity |
| 4.2 | SNIP 1: ISA not 106 chars -> error | Fixed-width enforcement |
| 4.3 | SNIP 1: Mismatched ISA/IEA -> error | Envelope nesting |
| 4.4 | SNIP 2: Missing BHT -> error | Required segment |
| 4.5 | SNIP 2: Empty NM103 in 2100A -> error | Required element |
| 4.6 | SNIP 2: Wrong GS08 version -> error | Version check |
| 4.7 | SNIP 2: Element exceeds max length -> error | Length check |
| 4.8 | SNIP 3: SE01 mismatch -> error | Segment count |
| 4.9 | SNIP 3: ISA13 != IEA02 -> error | Control number |
| 4.10 | SNIP 4: HL02 references nonexistent parent -> error | Hierarchy integrity |
| 4.11 | SNIP 4: NM101=IL in 2100A context -> error (should be PR) | Context validation |
| 4.12 | SNIP 5: Invalid state code "XX" -> error | Code set |
| 4.13 | SNIP 5: Date "20260230" (Feb 30) -> error | Calendar validation |
| 4.14 | SNIP 5: NPI failing Luhn check -> error | NPI validation |
| 4.15 | DC Medicaid: ISA08 != DCMEDICAID -> error | Profile-specific |
| 4.16 | DC Medicaid: >5000 transactions -> error | Batch limit |
| 4.17 | DC Medicaid: Future service date -> error | Date constraint |
| 4.18 | DC Medicaid: Service date >13 months ago -> error | Historical limit |
| 4.19 | DC Medicaid: HL03=23 (dependent loop) -> error | No dependents |
| 4.20 | DC Medicaid: Invalid search criteria combo -> error | Search criteria validation |
| 4.21 | DC Medicaid: Valid AAA reject code mapping -> correct message | AAA mapping |
| 4.22 | Valid 270 fixture -> no errors (generic + dc_medicaid) | Happy path |
| 4.23 | Valid 271 fixture -> no errors | Happy path |
| 4.24 | Validate with no profile -> only SNIP levels run | Profile is optional |

---

## Phase 5: Web Backend — FastAPI API

**Goal**: Versioned API endpoints (`/api/v1/`) that wrap the library with PHI-safe logging, request correlation IDs, and template-based import.

### Endpoints

#### `POST /api/v1/convert` — Template-based Excel/TXT -> JSON
- **Input**: `multipart/form-data` with `file` (.xlsx, .csv, .tsv, .txt)
- **Output**: `{ filename, file_type, record_count, warnings[], corrections[], patients[] }`
- **Logic**: Strictly template-based — requires canonical column headers (defined in `templates/template_spec.md`). Missing required columns produce actionable errors. Extra columns are ignored with a warning.
- **Auto-corrections** (reported in `corrections[]` so the user knows what was fixed):
  - Date normalization: `01/15/1985`, `1/15/85`, `1985-01-15` → `19850115`
  - Name uppercasing: `john smith` → `JOHN SMITH`
  - Whitespace trimming: `  12345678  ` → `12345678`
  - Default injection: missing `service_type_code` → uses value from `SubmitterConfig.default_service_type_code` (default `30`)
- **Validation warnings** (reported in `warnings[]` — require user confirmation, not auto-corrected):
  - Short member IDs: `1234567` → warning: *"Member ID '1234567' appears short — DC Medicaid requires 8 digits. Pad to '12345670'?"* — never silently altered
- **Partial-result semantics**: If row 50 of 200 has an unfixable error (e.g., invalid date that auto-correction can't parse), return the 199 valid rows + an error for row 50 in `errors[]`, not a blanket 400. This matches `on_error="collect"` semantics.

**Canonical Template Columns** (patient data only — provider/payer fields come from Settings):
| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| last_name | Yes | Member last name | SMITH |
| first_name | Yes | Member first name | JOHN |
| date_of_birth | Yes | CCYYMMDD or MM/DD/YYYY | 19850115 |
| gender | Yes | M, F, or U | M |
| member_id | Conditional | DC Medicaid Member ID | 12345678 |
| ssn | Conditional | Social Security Number | 999887777 |
| service_type_code | No (default from Settings) | From Appendix A.1 | 30 |
| service_date | Yes | Date of service CCYYMMDD | 20260406 |
| service_date_end | No | End date for ranges (RD8) | 20260430 |

> **Note**: `provider_npi`, `provider_name`, `provider_entity_type`, and `trading_partner_id` are no longer per-row CSV columns — they are configured once in the Settings panel and sent with the API request via `SubmitterConfig`. See [Configuration System](#configuration-system).

#### `POST /api/v1/generate` — JSON -> X12 270
- **Input**: `application/json` with `{ config: SubmitterConfig, patients[], profile? }` *(JSON body — no file upload needed, data comes from /convert)*
- **Output**: `{ x12_content, transaction_count, segment_count, file_size_bytes, split_count, control_numbers: {isa13, gs06, st02_range} }` (when `split_count > 1`, `x12_content` is null and a zip download URL is returned instead)
- **Logic**: Uses `config` (provider identity, payer identity, envelope settings) to populate ISA/GS/NM1 segments. Builds Interchange -> FunctionalGroup -> Transaction270 per patient -> encode(). No hardcoded values — all submitter/payer fields come from config.
- **Auto-split**: If patients exceed `config.max_batch_size`, automatically splits into multiple interchanges. When `split_count > 1`, returns a zip archive containing one `.x12` file per interchange plus a `manifest.json` (split count, record ranges per file, control number mappings). When `split_count == 1`, returns the raw X12 string directly.
- **Partial-result semantics**: If generation fails mid-batch (e.g., one patient record has invalid data), return partial results + error metadata, not all-or-nothing. The response includes `{ x12_content (for valid records), errors[] (for failed records), partial: true }`.

#### `POST /api/v1/validate` — X12 -> Validation Results
- **Input**: `multipart/form-data` with `file` (.x12, .edi, .txt)
- **Output**: `{ filename, is_valid, error_count, warning_count, issues[] }`
- Each issue: `{ severity, level, code, message, location, segment_id, element, suggestion, profile }`
- **Logic**: parse() -> validate(levels={1,2,3,4,5}, profile="dc_medicaid")

#### `POST /api/v1/parse` — X12 271 -> Eligibility Dashboard Data
- **Input**: `multipart/form-data` with `file` (.x12, .edi, .txt)
- **Output**: `{ filename, transaction_count, summary, payer_name, results[] }`
- Each result: `{ member_name, member_id, overall_status, eligibility_segments[], benefit_entities[], aaa_errors[] }`

#### `POST /api/v1/export/xlsx` — Eligibility Results -> Excel
- **Input**: `application/json` with parsed eligibility results
- **Output**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (streaming download)
- **Logic**: Server-side Excel generation with openpyxl. Provides a clean formatted workbook without introducing a second Excel stack in the browser.

#### `GET /api/v1/templates/{name}` — Download canonical templates
- Returns the import template files (Excel, CSV)

#### `POST /api/v1/pipeline` — Single-call end-to-end (agent-friendly)
- **Input**: `multipart/form-data` with `file` (.xlsx, .csv) + `config` (JSON string of `SubmitterConfig`) + optional `profile` (default: "dc_medicaid"). Also accepts `application/json` with `{ config, patients[], profile }` for agents that have already converted the file via `/convert`.
- **Output**: `{ x12_content, validation_result, transaction_count, segment_count, warnings[] }`
- **Logic**: convert -> validate rows -> build 270 (using config) -> validate X12 -> return everything in one round-trip. This is the "I don't want to think" endpoint for agents and simple integrations.
- If validation fails, returns the errors with suggestions instead of the X12 content.

#### `GET /api/v1/profiles` — List available payer profiles
- **Output**: `{ profiles: [{ name, display_name, description }] }`
- **Logic**: Returns all registered payer profiles (e.g., `dc_medicaid`).

#### `GET /api/v1/profiles/{name}/defaults` — Get payer profile defaults
- **Output**: `{ payer_name, payer_id, interchange_receiver_id, receiver_id_qualifier, default_service_type_code, max_batch_size }`
- **Logic**: Returns the default Group 2-4 settings for a payer profile. The frontend uses this to auto-populate the Settings panel when the user selects a payer profile.

#### `GET /api/v1/health` — Deep Health Check
- Returns `{ "status": "ok"|"degraded", "version": "0.1.0", "checks": { "library_import": true, "parser_smoke": true, "profiles_loaded": ["dc_medicaid"] } }`
- Validates: library importable, parser can handle a minimal smoke-test fixture, profile registry populated
- Returns `"status": "degraded"` with specifics on failure — never just `{"status": "ok"}` without verification

### Endpoint Contract Summary: Multipart vs JSON

| Endpoint | Content-Type | Rationale |
|----------|-------------|-----------|
| `POST /convert` | `multipart/form-data` | File upload required |
| `POST /generate` | `application/json` | Data comes from `/convert`, no file needed |
| `POST /validate` | `multipart/form-data` | X12 file upload required |
| `POST /parse` | `multipart/form-data` | X12 file upload required |
| `POST /pipeline` | `multipart/form-data` OR `application/json` | File upload for UI, JSON for agents with pre-converted data |
| `POST /export/xlsx` | `application/json` | Parsed results, no file upload |
| `GET /templates/{name}` | N/A | File download |
| `GET /profiles` | N/A | JSON response |
| `GET /profiles/{name}/defaults` | N/A | JSON response |
| `GET /health` | N/A | JSON response |

### Middleware
- **Request correlation IDs**: Every request gets a UUID (`X-Correlation-ID` header). Passed through to all log entries.
- **PHI-safe logging**: Structured JSON logging. NEVER logs request/response bodies, file contents, patient names, member IDs, **raw filenames**, or any PHI. Only logs: correlation ID, endpoint, status code, duration, **sanitized file metadata (MIME type, byte size, file hash — never raw filename)**. **Filenames are PHI** — uploaded filenames routinely contain patient names or member IDs (e.g., `smith_john_eligibility.xlsx`). This must be enforced at the middleware level, not left to individual endpoint implementations.
- **Max upload size**: 5MB enforced server-side.

### Input Hardening
- Enforce maximum segment count, maximum elements per segment, and maximum raw payload length before full parse
- Reject non-printable or control-character delimiters outside an allowed safe set
- Enforce request timeouts and upload body size limits at the gateway and application layers
- Do not accept archive formats in v1; only the documented plain file types are supported

### Rate Limiting & Abuse Prevention (Production)
- Per-user request rate limits: 60 requests/minute (enforced via FastAPI middleware or Cloud Run settings)
- Concurrent request limits: 5 simultaneous uploads per user
- Circuit breaker for the parse/validate pipeline: if error rates spike above threshold, return 503 with retry-after header rather than consuming resources on likely-bad input
- For local development, rate limiting is disabled

### Stateless Design
- No database, no sessions, no temp files on disk
- **Temp-file prevention enforcement**: Configure `python-multipart` with `SpooledTemporaryFile` using a memory threshold matching the 5MB upload cap so files stay in memory. For `openpyxl`, use `load_workbook(BytesIO(content))` — never pass file paths. This is an architectural invariant with a test that verifies no temp files are created during request processing.
- File uploads read into memory, processed, response returned
- No raw X12 or PHI retained after request completion
- Prefer synchronous request handling initially, but define latency budgets from benchmarks instead of assuming fixed numbers
- If large batch generation or export breaches the budget, move that path to short-lived async processing with explicit expiry and zero-retention guarantees

### Security Boundary
- Local development can run without auth
- Any deployed environment that can process real PHI must be behind an external identity and network boundary such as Cloud IAP, an OIDC proxy, or a private network gateway
- The application trusts identity headers from that boundary; it does not own user lifecycle or credential storage in v1

### Test Cases — Phase 5
| # | Test | What it validates |
|---|------|------------------|
| 5.1 | POST /api/v1/convert with valid .xlsx matching template -> 200 | Template conversion |
| 5.2 | POST /api/v1/convert with missing required column -> 400 + actionable error | Template enforcement |
| 5.3 | POST /api/v1/convert with extra/unknown columns -> 200 (ignored) + warning | Flexibility |
| 5.4 | POST /api/v1/convert with .csv -> 200 | CSV support |
| 5.5 | POST /api/v1/convert with .pdf -> 400 "Unsupported file type" | Rejection |
| 5.6 | POST /api/v1/convert with empty .xlsx -> 200, record_count=0 | Edge case |
| 5.7 | POST /api/v1/generate with 1 patient -> valid X12 starting with ISA | Single generation |
| 5.8 | POST /api/v1/generate with 3 patients -> transaction_count=3 | Batch generation |
| 5.9 | POST /api/v1/generate with config: ISA06 matches config.trading_partner_id, NM103 in 2100B matches config.organization_name | Config mapping |
| 5.10 | POST /api/v1/generate with 0 patients -> 422 | Validation |
| 5.11 | POST /api/v1/generate with 6000 patients -> 200, split_count=2 | Auto-split at config.max_batch_size |
| 5.12 | POST /api/v1/validate with valid 270 -> is_valid=true | Happy path |
| 5.13 | POST /api/v1/validate with wrong ISA08 -> is_valid=false, 1 error with suggestion | Validation catch |
| 5.14 | POST /api/v1/validate with garbled text -> appropriate error | Error handling |
| 5.15 | POST /api/v1/parse with 271 (3 active) -> summary.active=3 | Parse counting |
| 5.16 | POST /api/v1/parse with 271 mixed statuses -> correct summary | Mixed results |
| 5.17 | POST /api/v1/parse with AAA*N**72 -> overall_status="error" | Error extraction |
| 5.18 | POST /api/v1/parse with 2120C PCP -> benefit_entities populated | Entity extraction |
| 5.19 | POST /api/v1/parse with co-pay EB -> monetary_amount correct | Monetary parsing |
| 5.20 | GET /api/v1/health -> 200 {"status": "ok"} | Health check |
| 5.21 | POST /api/v1/generate -> roundtrip through /api/v1/parse | Integration test |
| 5.22 | Application logs contain NO PHI (check log output in test) | PHI safety |
| 5.23 | Every response includes X-Correlation-ID header | Correlation IDs |
| 5.24 | POST /api/v1/export/xlsx with parsed results -> valid .xlsx bytes | Excel export |
| 5.25 | GET /api/v1/templates/eligibility_template.xlsx -> file download | Template serving |
| 5.26 | Oversized or pathological input is rejected before full parse | Input hardening |
| 5.27 | Deployed mode rejects unauthenticated requests when auth boundary is enabled | Security boundary |
| 5.28 | POST /api/v1/convert auto-corrects "01/15/1985" to "19850115" and reports in corrections[] | Auto-correction |
| 5.29 | POST /api/v1/convert auto-uppercases "john smith" to "JOHN SMITH" | Auto-correction |
| 5.30 | POST /api/v1/convert auto-fills missing service_type_code from config default | Default injection |
| 5.31 | POST /api/v1/pipeline with valid .xlsx + config -> returns x12_content + passing validation | Pipeline happy path |
| 5.32 | POST /api/v1/pipeline with invalid rows -> returns errors with suggestions, no x12_content | Pipeline error path |
| 5.33 | POST /api/v1/generate without config -> 422 with actionable error | Config required |
| 5.34 | POST /api/v1/generate with invalid NPI (fails Luhn) in config -> 422 | Config validation |
| 5.35 | POST /api/v1/generate with config.usage_indicator="P" -> ISA15=P in output | Config propagation |
| 5.36 | GET /api/v1/profiles -> returns list including "dc_medicaid" | Profile listing |
| 5.37 | GET /api/v1/profiles/dc_medicaid/defaults -> returns payer_name="DC MEDICAID", payer_id="DCMEDICAID" | Profile defaults |
| 5.38 | GET /api/v1/profiles/nonexistent/defaults -> 404 | Unknown profile |
| 5.39 | No temp files created on disk during any request processing (verify via tempdir monitoring) | Temp-file prevention |
| 5.40 | Application logs contain NO raw filenames (verify log output contains only MIME type, byte size, hash) | Filename PHI safety |
| 5.41 | POST /api/v1/convert with short member_id -> warning in warnings[], not auto-corrected | Member ID demotion to prompt |
| 5.42 | POST /api/v1/convert with 200 rows, row 50 has unfixable error -> returns 199 valid + 1 error | Partial-result semantics |
| 5.43 | POST /api/v1/generate with 6000 patients -> zip download with 2 files + manifest.json | Split zip output |
| 5.44 | POST /api/v1/generate response includes control_numbers with ISA13, GS06, ST02 range | Control number visibility |
| 5.45 | GET /api/v1/health validates parser smoke test and profile registry, returns "degraded" on failure | Deep health check |
| 5.46 | Rate limiting returns 429 after exceeding 60 requests/minute in production mode | Rate limiting |

---

## Phase 6: Web Frontend — React UI

**Goal**: 7 pages with a centralized but intentionally lean design system. Optimized for a non-technical user doing bulk eligibility workflows. Includes a Settings page for provider/payer configuration that must be completed before 270 generation.

### Design System

**Visual + composition spec**: `docs/design-system.md` — a Meta (Store)-inspired design system adapted for this healthcare workbench. AI agents MUST read `docs/design-system.md` (roles, rules) and `docs/ui-components.md` (primitive API catalog) before writing any UI code.

**Token implementation**: `apps/web/src/styles/tokens.css` using Tailwind v4's `@theme` directive — this file is the sole source of truth for concrete hex values. `docs/design-system.md` describes what each token is *for*; it never restates hex values.

```css
@theme {
  /* Action */
  --color-action-500: #0064E0;
  --color-action-600: #0051B5;
  --color-action-700: #004BB9;
  --color-action-50: #E8F3FF;

  /* Surfaces */
  --color-surface-primary: #FFFFFF;
  --color-surface-secondary: #F1F4F7;
  --color-surface-tertiary: #F7F8FA;
  --color-surface-wash: #F0F2F5;
  --color-surface-dark: #1C1E21;

  /* Text */
  --color-text-primary: #1C2B33;
  --color-text-secondary: #5D6C7B;
  --color-text-tertiary: #65676B;
  --color-text-disabled: #BCC0C4;
  --color-text-inverse: #FFFFFF;

  /* Status: Active */
  --color-active-500: #007D1E;
  --color-active-50: #ECFDF3;
  --color-active-200: #A6F4C5;

  /* Status: Inactive */
  --color-inactive-500: #C80A28;
  --color-inactive-50: #FEF2F2;
  --color-inactive-200: #FECACA;

  /* Status: Warning */
  --color-warning-500: #B45309;
  --color-warning-50: #FFFBEB;
  --color-warning-200: #FDE68A;

  /* Status: Not Found */
  --color-notfound-500: #475569;
  --color-notfound-50: #F1F5F9;
  --color-notfound-200: #CBD5E1;

  /* Border */
  --color-border-default: #DEE3E9;
  --color-border-subtle: #E5E7EB;
  --color-border-strong: #909396;

  /* Fonts */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Cascadia Code', Menlo, Consolas, 'Liberation Mono', monospace;

  /* Radius */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-2xl: 20px;
  --radius-pill: 100px;

  /* Shadows */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.10);
  --shadow-xl: 0 16px 40px rgba(0, 0, 0, 0.14);

  /* Motion */
  --duration-fast: 150ms;
  --duration-normal: 200ms;
  --duration-slow: 300ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}
```

**Rules for agents** (enforced via CLAUDE.md + `docs/design-system.md`):
0. **Read `docs/design-system.md` and `docs/ui-components.md` before writing any UI code.** design-system.md describes the roles and rules; tokens.css is the authoritative source for concrete values. If they conflict, tokens.css wins for values and design-system.md wins for rules — both must be updated together.
1. All colors, spacing, radius, shadows, motion, font stacks, font sizes, and semantic tokens live in `tokens.css` — no inline hex values, no one-off Tailwind values without first promoting them to tokens
2. No inline `style={}` except truly dynamic values
3. All interactive elements use `ui/Button.tsx` — no ad-hoc buttons
4. All data display uses `ui/Table.tsx` — no raw `<table>` elements
5. All file inputs use `ui/FileUpload.tsx`
6. Feature components compose ui/ components — never duplicate primitives
7. Pages compose feature components — pages contain layout, not UI logic
8. Any new visual pattern must update `docs/design-system.md` (rules) and `docs/ui-components.md` (primitive API), plus the relevant primitive test
9. UI copy, workflow changes, and public API changes must also update `README.md`

### UI Screens

**Screen 1: Home Page** — Landing IS the action page (minimal clicks)
```
+------------------------------------------------------------------+
|  [LOGO] DC Medicaid Eligibility Tool  [Templates] [Settings] [?] |
+------------------------------------------------------------------+
|  +--------------------------------------------------------------+ |
|  | Provider: ACME HOME HEALTH | NPI: 1234567890 | DC Medicaid   | |
|  +--------------------------------------------------------------+ |
|           What would you like to do?                               |
|   +------------------+  +------------------+  +------------------+ |
|   |  [ICON]          |  |  [ICON]          |  |  [ICON]          | |
|   |  Generate 270    |  |  Validate 270    |  |  Parse 271       | |
|   |  Upload Excel/CSV|  |  Upload X12 file |  |  Upload X12 file | |
|   |  to create an    |  |  to check for    |  |  to see          | |
|   |  eligibility     |  |  compliance      |  |  eligibility     | |
|   |  inquiry file    |  |  errors          |  |  results         | |
|   | [Select File...] |  | [Select File...] |  | [Select File...] | |
|   +------------------+  +------------------+  +------------------+ |
|   +--- Or drag & drop any file here (.xlsx .csv .x12 .edi) -----+ |
+------------------------------------------------------------------+
|  Open Source | v0.1.0 | github.com/...                             |
+------------------------------------------------------------------+
```

**Screen 2: Preview Page** — Shows parsed file summary before processing
- For Excel/CSV: row count, first 5 rows in a table, warnings about missing fields
- For X12: segment count, ISA metadata, first few subscriber names detected
- Buttons: [Cancel] [Process ->]

**Screen 3: Generate Result** — After 270 generation
- Summary cards: transaction count, segment count, file size, split count (if >5000)
- Raw X12 preview (scrollable monospace)
- Buttons: [Download X12] [Copy to Clipboard]

**Screen 4: Validation Result** — After 270 validation
- Overall status badge (PASS/FAIL)
- Table of issues: severity badge, SNIP level, segment, message, suggestion
- Button: [Download Report (JSON)] [Upload Another]

**Screen 5: Eligibility Dashboard** — After 271 parsing (most complex)
```
+------------------------------------------------------------------+
|  Eligibility Results Dashboard                                     |
|  +----------+  +----------+  +----------+  +----------+           |
|  | [GREEN]  |  | [RED]    |  | [YELLOW] |  | [GRAY]   |           |
|  |   34     |  |    8     |  |    3     |  |    2     |           |
|  |  Active  |  | Inactive |  |  Errors  |  | Not Found|           |
|  +----------+  +----------+  +----------+  +----------+           |
|                                                                    |
|  Filter: [All v]  Search: [___________]   [Export Excel]           |
|                                                                    |
|  +----+--------+----------+--------+--------+--------+------+     |
|  | #  | Name   | MemberID | Status | Plan   | Dates  | [>]  |     |
|  +----+--------+----------+--------+--------+--------+------+     |
|  | 1  | SMITH  | 12345678 | Active | FFS    | 01/01- | [>]  |     |
|  |    |        |          |[green] | RC:01  | 12/31  |      |     |
|  +----+--------+----------+--------+--------+--------+------+     |
|  | 2  | JONES  | 23456789 | Inactv |  --    |  --    | [>]  |     |
|  |    |        |          |[red]   |        |        |      |     |
|  +----+--------+----------+--------+--------+--------+------+     |
|  ... (sortable, filterable, paginated)                             |
|                                                                    |
|  Expanded row detail:                                              |
|  +------------------------------------------------------------+   |
|  | SMITH, JOHN  |  MemberID: 12345678  |  DOB: 01/15/1985     |   |
|  | Address: 123 Main St, Washington, DC 20001                 |   |
|  | Eligibility: Active | Medicaid | FFS|RC:01|CC:A            |   |
|  | PCP: DR. WELLNESS, NPI: 1234567890                         |   |
|  | Plan Sponsor: AMERIHEALTH CARITAS DC                       |   |
|  +------------------------------------------------------------+   |
+------------------------------------------------------------------+
```

**Screen 6: Templates Page** — Download canonical import templates
```
+------------------------------------------------------------------+
|  Import Templates                                                  |
|  +--------------------+  +--------------------+                    |
|  | Excel Template     |  | CSV Template       |                    |
|  | [Download .xlsx]   |  | [Download .csv]    |                    |
|  +--------------------+  +--------------------+                    |
|                                                                    |
|  Required Columns (patient data only):                             |
|  +----------+----------+-------------------+------------------+    |
|  | Column   | Required | Format            | Example          |    |
|  +----------+----------+-------------------+------------------+    |
|  | last_name| Yes      | Text              | SMITH            |    |
|  | first_nm | Yes      | Text              | JOHN             |    |
|  | dob      | Yes      | CCYYMMDD          | 19850115         |    |
|  | ...      |          |                   |                  |    |
|  +----------+----------+-------------------+------------------+    |
|  Note: Provider NPI, name, and Trading Partner ID are              |
|  configured in Settings — not included in the template.            |
|                                                                    |
|  DC Medicaid Rules:                                                |
|  - Member ID + at least one of: name+DOB, name+SSN, SSN+DOB       |
|  - Service date: not future, max 13 months back                    |
|  - Max 5000 per batch (auto-split if larger)                       |
+------------------------------------------------------------------+
```

**Screen 7: Settings Page** — Provider, payer, and envelope configuration
```
+------------------------------------------------------------------+
|  [LOGO] DC Medicaid Eligibility Tool  [Templates] [Settings] [?] |
+------------------------------------------------------------------+
|  Settings                  [Import JSON] [Export JSON] [Save Changes] |
|                                                                    |
|  SUBMITTER / PROVIDER IDENTITY                                     |
|  +------------------------------------------------------------+   |
|  | Organization Name*    [ACME HOME HEALTH____________]        |   |
|  | Provider NPI*         [1234567890] [valid checkmark]        |   |
|  | Provider Entity Type* [Organization (2)        v]           |   |
|  | Trading Partner ID*   [MYTP123456______________]            |   |
|  | Taxonomy Code         [251E00000X______________]  optional  |   |
|  | Contact Name          [JANE DOE________________]  optional  |   |
|  | Contact Phone         [2025551234______________]  optional  |   |
|  | Contact Email         [jane@acme.com___________]  optional  |   |
|  +------------------------------------------------------------+   |
|                                                                    |
|  PAYER / RECEIVER                                                  |
|  +------------------------------------------------------------+   |
|  | Payer Profile*        [DC Medicaid             v]           |   |
|  |   (auto-fills fields below when changed)                    |   |
|  | Payer Name*           [DC MEDICAID_____________]            |   |
|  | Payer ID*             [DCMEDICAID______________]            |   |
|  | Receiver ID (ISA08)*  [DCMEDICAID______________]            |   |
|  | Receiver Qualifier*   [ZZ                      v]           |   |
|  +------------------------------------------------------------+   |
|                                                                    |
|  ENVELOPE DEFAULTS                                                 |
|  +------------------------------------------------------------+   |
|  | Sender ID Qualifier*  [ZZ                      v]           |   |
|  | Usage Indicator*      [Test (T)                v]           |   |
|  | Ack Requested*        [No (0)                  v]           |   |
|  | X12 Version           005010X279A1  (read-only)             |   |
|  +------------------------------------------------------------+   |
|                                                                    |
|  TRANSACTION DEFAULTS                                              |
|  +------------------------------------------------------------+   |
|  | Service Type Code*    [30 - Health Benefit Plan v]          |   |
|  | Default Service Date  [Today's date            v]           |   |
|  | Max Batch Size*       [5000________________________]        |   |
|  +------------------------------------------------------------+   |
|                                                                    |
|  * Required — must be set before generating 270 files              |
+------------------------------------------------------------------+
```

Settings UX notes:
- **ConfigStatusBar** (shown on Home Page): One-line summary of current config — `Provider: ACME HOME HEALTH | NPI: 1234567890 | Payer: DC Medicaid`. Clicking it navigates to Settings.
- **Validation gate**: If required settings are missing, the "Generate 270" action card shows a warning: *"Configure your provider details in Settings first."* File upload is disabled until settings are complete.
- **NPI live validation**: Provider NPI field runs Luhn check on blur/change and shows immediate pass/fail indicator.
- **Payer profile auto-fill**: Selecting a payer profile calls `GET /api/v1/profiles/{name}/defaults` and fills Group 2 + Group 4 fields. User can override individual values after auto-fill.
- **localStorage persistence**: All settings saved to `localStorage` under key `x12_submitter_config`. Survives page refresh and browser restart. No server round-trip.

### Smart File Routing
The home page drop zone auto-detects file type from content, not just extension:
- **Content starts with column headers** (last_name, first_name, etc.) → Generate flow
- **Content starts with `ISA*`** → detect ST01: `270` → Validate flow, `271` → Parse flow
- **Extension fallback**: `.xlsx`/`.csv` → Generate, `.x12`/`.edi` → detect from ST01

User never has to choose which action card to use — just drop the file and the system routes.

### Data Flow (Stateless)
```
Settings:  Settings page -> Configure provider/payer/envelope -> Saved to localStorage
Generate:  Drop .xlsx    -> check settings -> auto-detect -> POST /convert -> Preview -> POST /generate (with config) -> Download X12
Validate:  Drop .x12/270 -> auto-detect   -> Preview     -> POST /validate           -> Show issues
Parse 271: Drop .x12/271 -> auto-detect   -> Preview     -> POST /parse              -> Dashboard -> Export Excel
Templates: Templates page -> Download .xlsx/.csv template -> Fill in -> Drop via Generate flow
```

> **Settings gate**: The Generate flow checks that required settings are configured before allowing file upload. Validate and Parse flows do not require settings (they work on existing X12 files).

### Browser Compatibility Matrix
Production healthcare tool — explicitly tested and supported:
- Last 2 versions of: **Chrome**, **Firefox**, **Edge**, **Safari**
- Test with the browser the colleague actually uses (likely Chrome on Windows)
- Modern CSS features (`:has()`, container queries, `color-mix()`) may be used freely for these targets — no polyfills needed

### Browser-Side PHI Boundary
The frontend must **never persist PHI** to `localStorage`, `sessionStorage`, `IndexedDB`, or any client-side cache. Only `SubmitterConfig` settings (which contain no PHI — just provider/payer identity and envelope settings) are persisted client-side. Parsed eligibility results, patient records, and any data from API responses exist only in React state and are garbage-collected when the user navigates away or closes the tab. Browser devtools/memory may transiently expose PHI — this is acceptable as it matches the user's own machine and session.

### Graceful Degradation for Large Files
For a 5000-row Excel file, `/convert` + `/generate` could take several seconds. The frontend must handle this gracefully:
- **Progress indicator**: At minimum, a spinner with "Processing N records..." (record count from the `/convert` preview step). For `/generate`, show "Generating X12 file for N records..."
- **Timeout handling**: If the request exceeds 30 seconds, show a timeout message with retry option: *"Processing is taking longer than expected. This may happen with very large files. [Retry] [Cancel]"*
- **Partial failure recovery**: If `/convert` returns partial results (199 of 200 rows valid), show the valid rows in preview with a dismissible warning banner: *"1 row had errors and was excluded. [Show details]"*. Let the user proceed with the valid rows or fix the source file and re-upload.

### Key Dependencies
- `react-router-dom` v7 — client-side routing (pass data via Router state, not URL params)
- `@tanstack/react-table` — use only if the dashboard genuinely needs richer table behavior than a simple sortable table
- No client-side Excel library in v1 — export remains server-side via `POST /api/v1/export/xlsx`

### Test Cases — Phase 6
| # | Test | What it validates |
|---|------|------------------|
| 6.1 | Button renders text, fires onClick, applies variant classes | Component |
| 6.2 | FileUpload renders drop zone, fires onFileSelect on drop | Component |
| 6.3 | Table renders headers and rows, sorts on click, paginates | Component |
| 6.4 | Badge renders correct color for each variant | Component |
| 6.5 | HomePage renders 3 action cards + drop zone | Page structure |
| 6.6 | fileDetection.ts: .xlsx -> "excel", .x12 -> "x12", .csv -> "csv" | Utility |
| 6.7 | fileDetection.ts: content starting with ISA* -> "x12" | Content sniffing |
| 6.8 | formatters.ts: "20260406" -> "04/06/2026" | Date formatting |
| 6.9 | EligibilityDashboard with mock data: stat cards show correct counts | Feature |
| 6.10 | EligibilityDashboard filters by status | Feature |
| 6.11 | Export action triggers server-side XLSX download successfully | Excel export |
| 6.12 | HomePage upload navigates to PreviewPage | Navigation |
| 6.13 | useApi hook: returns loading=true initially, then data | Hook |
| 6.14 | useApi hook: returns error on reject | Hook |
| 6.15 | TemplatesPage renders download links for both templates | Templates |
| 6.16 | Keyboard navigation works on all interactive elements | Accessibility |
| 6.17 | Playwright: upload .xlsx -> preview -> generate -> download | E2E flow |
| 6.18 | Drop .xlsx on home page -> auto-routes to Generate preview | Smart file routing |
| 6.19 | Drop .x12 with ST01=270 -> auto-routes to Validate flow | Smart file routing |
| 6.20 | Drop .x12 with ST01=271 -> auto-routes to Parse flow | Smart file routing |
| 6.21 | Validation errors display plain English with fix suggestions, not SNIP codes | Error UX |
| 6.22 | Corrections from auto-correction are shown as dismissible info banners | Auto-correction UX |
| 6.23 | SettingsPage renders all 4 config groups with correct fields | Settings page structure |
| 6.24 | useSettings hook reads/writes localStorage correctly | Settings persistence |
| 6.25 | Changing payer profile auto-fills Group 2 fields from API defaults | Payer auto-fill |
| 6.26 | NPI field shows Luhn validation pass/fail on input | NPI validation UX |
| 6.27 | ConfigStatusBar on Home Page shows provider name, NPI, payer profile | Config status display |
| 6.28 | Generate 270 action card disabled with warning when required settings missing | Settings gate |
| 6.29 | Settings saved to localStorage survive page refresh | Persistence |
| 6.30 | Playwright: configure settings -> upload .xlsx -> generate -> verify config in X12 output | E2E settings flow |
| 6.31 | Settings Export JSON downloads valid JSON matching current settings | Settings export |
| 6.32 | Settings Import JSON populates form correctly from uploaded JSON | Settings import |
| 6.33 | No PHI written to localStorage/sessionStorage/IndexedDB during any workflow | Browser PHI boundary |
| 6.34 | Large file upload (5000 rows) shows progress indicator during processing | Large file UX |
| 6.35 | Request timeout after 30s shows retry/cancel prompt | Timeout handling |
| 6.36 | Partial convert result (199/200 valid) shows warning banner with option to proceed | Partial result UX |
| 6.37 | Short member ID in preview shows confirmation prompt, not silent correction | Member ID confirmation |
| 6.38 | Split-output download (>5000 records) delivers zip with manifest | Split download UX |

---

## Phase 7: Integration + Docker

**Goal**: Full end-to-end flow works locally and in a production-like container.

### Docker Setup

**Single-container option** (recommended for production): `docker/Dockerfile` serves FastAPI API + built React static files on the same origin. No CORS issues, simpler deployment.

```
docker/Dockerfile         # Multi-stage: build frontend, install backend, serve both
docker/Dockerfile.dev     # Dev: hot-reload for both frontend and backend
docker/nginx.conf         # Optional: for split deployment if needed
docker-compose.yml        # Local dev with volume mounts
docker-compose.prod.yml   # Production with health checks
```

### Deployment Options

| Option | When to use | Cost |
|--------|------------|------|
| **docker-compose** (local) | Development, internal single-machine deployment | $0 |
| **Vercel (frontend) + Render (backend)** | Quick start, low-traffic OSS demo | $0/month |
| **Google Cloud Run** | Production with real PHI (HIPAA BAA required) | ~$0-5/month (pay-per-use) |

**Cloud Run note**: For production PHI workloads, Google Cloud Run is HIPAA-eligible under a BAA. Combined with Secret Manager and IAP for auth, this provides a compliant deployment at near-zero cost. The single-container Dockerfile deploys directly to Cloud Run.

**Auth model (v1)**: No custom user database. Trust an external identity layer (Cloud IAP, OIDC reverse proxy, or similar). The app only consumes trusted identity headers.

**Production requirement**: Any deployment that can process real PHI must enable that external identity layer before exposure to users. Anonymous internet-facing deployment is not an acceptable production mode.

**Out of scope for v1**: Direct Gainwell SFTP/SOAP submission. That requires separate credential lifecycle, retry/audit rules, and is a Phase 2+ feature.

### Downstream Submission Workflow (Manual)

The plan correctly defers automated Gainwell submission, but the manual handoff must be documented for production users:

1. **After downloading the .x12 file**: The user submits it to Gainwell Technologies' DC MMIS system via their designated channel (typically Gainwell's web portal or SFTP drop, depending on the trading partner agreement).
2. **Filename conventions**: If Gainwell expects a specific naming pattern (e.g., `<TradingPartnerID>_270_<date>_<controlnumber>.x12`), the download should auto-generate the filename accordingly. Include the ISA13 control number in the filename for audit trail matching.
3. **Batch summary**: The download should include a human-readable batch summary (PDF or text) listing: record count, date range of service dates, control numbers used, and a reminder of the submission channel.
4. **271 Response workflow**: When the 271 response comes back (typically same-day for real-time, 24-48 hours for batch), the user uploads it via the "Parse 271" workflow to view results on the Eligibility Dashboard.
5. **"Copy to clipboard" button**: Included on the Generate Result page — useful for real-time single-transaction submissions via Gainwell's web portal where the user may paste the X12 content directly.

### Test Cases — Phase 7
| # | Test | What it validates |
|---|------|------------------|
| 7.1 | `docker compose up` starts services | Docker build |
| 7.2 | Frontend loads HomePage at localhost | Frontend serving |
| 7.3 | Upload sample .xlsx -> Preview -> Generate -> Download .x12 | Full E2E flow |
| 7.4 | Upload generated .x12 -> Validate -> All pass | Roundtrip validation |
| 7.5 | Upload sample 271 -> Dashboard -> Export Excel | Parse + export flow |
| 7.6 | Backend /api/v1/health returns 200 | Health check |
| 7.7 | Single-container build serves both API and frontend | Container smoke test |

---

## Phase 8: CI/CD + Docs + Hardening + Release

### Deferred from Phase 0 (OSS Ceremony)
These are important for a public release but should not block product development:
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `CHANGELOG.md` with initial `[Unreleased]` section
- `docs/design-system.md` + `docs/ui-components.md` with UI rules and primitive catalog for agents

### Property-Based Testing (Hypothesis)
Deferred from Phases 2-3 to here. Now that parser and encoder are stable, add Hypothesis tests for:
- Delimiter detection and tokenization preserve separators, empty elements, and segment boundaries across arbitrary synthetic payloads
- Valid envelopes preserve delimiter choices and control counts through encode/parse cycles
- `parse(encode(arbitrary_interchange)) == arbitrary_interchange` roundtrip invariant

### Production Observability

Structured logging alone is insufficient for a system processing PHI in production. Phase 8 adds:

**Request-level metrics** (FastAPI + Prometheus middleware):
- Latency percentiles: p50, p95, p99 per endpoint
- Error rates by endpoint and error code
- Request volume and concurrent connection count
- File sizes and record counts (as histogram metrics, not log fields)

**Target latencies** (basis for Cloud Run alerting):
| Endpoint | Target p95 | Notes |
|----------|-----------|-------|
| `POST /convert` | < 2s for 5000 rows | Dominated by Excel parsing |
| `POST /generate` | < 3s for 5000 records | Dominated by encoding |
| `POST /validate` | < 2s for 5000-segment file | Dominated by SNIP checks |
| `POST /parse` | < 3s for 5000-record 271 | Dominated by loop building |
| `POST /pipeline` | < 5s for 5000 rows | Sum of convert + generate + validate |
| `POST /export/xlsx` | < 2s for 5000 rows | Dominated by openpyxl |

**Correlation ID propagation**: The `X-Correlation-ID` flows from middleware → service layer → library calls → structured log entries, so a single request can be traced end-to-end. Library functions accept an optional `correlation_id` parameter for this purpose.

### Data Retention & Cleanup Policy

Even though the system is stateless, production requires a documented policy (added to `SECURITY.md`):
- **Browser `localStorage`**: `SubmitterConfig` settings persist indefinitely (by design). No PHI is ever stored.
- **Server-side**: Zero retention after request completion. No caches, no CDN layers that could retain response data. `SpooledTemporaryFile` objects are garbage-collected immediately after response is sent.
- **Cloud Run logs**: Contain only correlation IDs, endpoints, status codes, durations, and sanitized file metadata. Correlation IDs are linkable to specific requests but contain no PHI. Log retention follows Cloud Logging defaults (30 days) — configurable per deployment.
- **Browser memory**: Parsed eligibility results exist only in React state. Garbage-collected on navigation or tab close. No `IndexedDB`, `sessionStorage`, or `Cache API` usage.

### Production Readiness Gate

Concrete criteria for when the system is deployable with real PHI:
- [ ] All SNIP 1-5 validators passing on synthetic fixtures
- [ ] DC Medicaid profile rules matching companion guide v1.4
- [ ] PHI boundary tests green: no filenames in logs, no temp files on disk, no PHI in client-side storage
- [ ] External identity boundary (Cloud IAP or equivalent) configured and tested
- [ ] Rate limiting and input hardening enabled
- [ ] Deep health check returning "ok" with all sub-checks passing
- [ ] Prometheus metrics endpoint responding
- [ ] SECURITY.md data retention policy reviewed by stakeholder
- [ ] Browser compatibility verified on target browser (Chrome on Windows)
- [ ] Settings export/import working (backup before first production use)
- [ ] Downstream submission workflow documented and tested with Gainwell test environment

### GitHub Actions

**ci.yml** (on PR + push to main):
- Job 1: `lint` — ruff format check + ruff lint
- Job 2: `typecheck` — mypy on library + backend (strict mode)
- Job 3: `test-library` — pytest across Python 3.11/3.12/3.13, coverage >= 90% for v0.1 (raise to 95% post-stabilization), property-based tests
- Job 4: `test-api` — pytest with coverage >= 85% for v0.1
- Job 5: `test-web` — eslint + vitest + build check
- Job 6: `security` — detect-secrets scan, no proprietary content check

**release.yml** (on tag `v*.*.*`):
- Build wheel + sdist
- Publish to PyPI using trusted publishing (OIDC, no API tokens)
- Build + push Docker image to GHCR
- Create GitHub Release with CHANGELOG excerpt

**deploy.yml** (on push to main, paths `apps/**`):
- Deploy single container to Cloud Run / Render (configurable)

### Versioning
- Semantic versioning: MAJOR.MINOR.PATCH
- Initial version: `0.1.0`
- `VERSION` file at repo root is the single source of truth
- Also synced to: `pyproject.toml`, `__about__.py`, README badge
- Conventional commits: `feat(parser):`, `fix(encoder):`, `docs(readme):`
- CHANGELOG.md follows Keep a Changelog format

### Claude Code Custom Commands

**`/bump-version <major|minor|patch|X.Y.Z>`**: Updates VERSION file, pyproject.toml, __about__.py, moves CHANGELOG [Unreleased] entries to new version section, updates README version table, stages + commits + creates annotated git tag.

**`/update-docs`** (alias: `/refresh-docs`): Refreshes public API docs, architecture docs, template docs, and examples so they match shipped behavior. It prioritizes public modules and non-obvious parser/validator logic rather than blanket docstring coverage.

**`/check-coverage <python|web|all>`**: Runs pytest/vitest with coverage, identifies uncovered lines in critical paths, and updates tests to maintain the staged thresholds for the current release phase.

### Documentation Standards

Python documentation should be intentionally scoped:

- Public modules and public API functions use concise Google-style docstrings
- Parser, encoder, and validator code paths with non-obvious invariants get inline documentation or module notes
- Private helpers and straightforward tests are exempt from blanket documentation requirements
- `docs/architecture.md` and `README.md` carry the system-level explanation; code comments explain tricky implementation details, not obvious control flow

JS/TS: ESLint, strict TypeScript, component tests for all shared primitives, concise inline docs only where logic is non-obvious.

### README Structure
- Badges: PyPI version, Python versions, Coverage, CI status, License
- What is X12 EDI? (brief explainer)
- Project structure table (packages/ vs apps/)
- Installation (`pip install x12-edi-tools` + from source)
- Quick start (parse, encode, validate with examples)
- API reference summary table
- Web application usage
- Templates documentation
- Development setup
- Deployment guide (Docker, Vercel+Render, Cloud Run)
- Contributing link
- PHI handling notes
- License

### Test Cases — Phase 8
| # | Test | What it validates |
|---|------|------------------|
| 8.1 | CI workflow passes on a clean main branch | CI works |
| 8.2 | `python -m build` in x12-edi-tools produces wheel + sdist | Package builds |
| 8.3 | `pip install dist/x12_edi_tools-*.whl` installs cleanly | Wheel installs |
| 8.4 | Coverage badge resolves to correct percentage | Badge works |
| 8.5 | `/bump-version patch` updates all version locations + creates tag | Command works |
| 8.6 | Docker image builds and passes smoke test | Container CI |
| 8.7 | No proprietary content in published wheel/sdist | OSS safety |
| 8.8 | Public API docs and architecture docs remain aligned with shipped behavior | Documentation quality |
| 8.9 | **Property-based**: `parse(encode(arbitrary_interchange)) == arbitrary_interchange` | Roundtrip invariant (Hypothesis) |
| 8.10 | **Property-based**: delimiter detection preserves separators across arbitrary payloads | Parser invariant (Hypothesis) |
| 8.11 | **Property-based**: valid envelopes preserve control counts through encode/parse cycles | Encoder invariant (Hypothesis) |

---

## Library Public API

### High-Level Convenience API (agent-friendly)
```python
import x12_edi_tools
from x12_edi_tools.config import SubmitterConfig

# Configure: provider identity + payer settings (no hardcoded values)
config = SubmitterConfig(
    organization_name="ACME HOME HEALTH",
    provider_npi="1234567890",
    trading_partner_id="MYTP123456",
    payer_name="DC MEDICAID",
    payer_id="DCMEDICAID",
    interchange_receiver_id="DCMEDICAID",
)

# Import: auto-detect format, auto-correct dates/names/IDs
patients = x12_edi_tools.from_csv("patients.csv")
patients = x12_edi_tools.from_excel("patients.xlsx")

# Generate: one call, config provides all provider/payer/envelope values
interchange = x12_edi_tools.build_270(patients, config=config, profile="dc_medicaid")

# Validate: plain-English results
result = x12_edi_tools.validate(interchange, profile="dc_medicaid")
print(result.human_readable_summary())

# Encode + write
x12_content = x12_edi_tools.encode(interchange)

# Parse 271 responses: structured eligibility results, not raw X12
eligibility = x12_edi_tools.read_271("response.x12")
df = eligibility.to_dataframe()  # optional pandas integration
```

### Granular API (for developers who need full control)
```python
import x12_edi_tools

# Parse raw X12 into typed models — always returns ParseResult
result = x12_edi_tools.parse(raw_x12_string)          # result.interchange, result.errors, result.warnings
result = x12_edi_tools.parse(raw, on_error="collect")  # partial success — result.errors populated

# Encode typed models back to X12
raw_output = x12_edi_tools.encode(interchange)

# Validate with specific SNIP levels
result = x12_edi_tools.validate(interchange, levels={1, 2, 3})

# Types for inspection
x12_edi_tools.SubmitterConfig         # Provider/payer/envelope configuration
x12_edi_tools.ParseResult             # Always returned by parse() — wraps Interchange + errors + warnings
x12_edi_tools.Interchange
x12_edi_tools.Transaction270
x12_edi_tools.Transaction271
x12_edi_tools.ParseResult
x12_edi_tools.ValidationResult
x12_edi_tools.ValidationError
x12_edi_tools.SnipLevel
x12_edi_tools.Delimiters
x12_edi_tools.X12ParseError
x12_edi_tools.X12EncodeError

# Payer profiles
x12_edi_tools.payers.dc_medicaid.DCMedicaidProfile
```

---

## Critical Files Reference

| File | Why it matters |
|------|---------------|
| `metadata/full_text.txt` | DC Medicaid companion guide — development reference, NEVER published |
| `packages/x12-edi-tools/src/x12_edi_tools/config.py` | SubmitterConfig model — all provider/payer/envelope settings flow through this |
| `packages/x12-edi-tools/src/x12_edi_tools/parser/loop_builder.py` | Most complex: HL-tree state machine |
| `packages/x12-edi-tools/src/x12_edi_tools/models/segments/isa.py` | ISA fixed-width is foundation of roundtrip fidelity |
| `packages/x12-edi-tools/src/x12_edi_tools/models/base.py` | Declarative `_element_map` protocol + generic from_elements/to_elements |
| `packages/x12-edi-tools/src/x12_edi_tools/payers/dc_medicaid/profile.py` | DC Medicaid business rules + `get_defaults()` for config auto-fill |
| `packages/x12-edi-tools/src/x12_edi_tools/payers/dc_medicaid/search_criteria.py` | Valid search combos from Section 7.2 |
| `apps/api/app/schemas/config.py` | API schema for SubmitterConfig — bridges frontend settings to library |
| `apps/api/app/core/logging.py` | PHI-safe logging — must NEVER log patient data |
| `apps/api/templates/template_spec.md` | Canonical import template definition |
| `apps/web/src/styles/tokens.css` | Single design system source of truth |
| `apps/web/src/pages/SettingsPage.tsx` | Provider/payer configuration — must be completed before 270 generation |
| `apps/web/src/hooks/useSettings.ts` | localStorage persistence for SubmitterConfig |
| `apps/web/src/pages/EligibilityDashboardPage.tsx` | Most complex UI page |
| `packages/x12-edi-tools/src/x12_edi_tools/models/base.py:GenericSegment` | Unknown segment preservation — critical for production roundtrip fidelity |
| `packages/x12-edi-tools/src/x12_edi_tools/exceptions.py:TransactionParseError` | Concrete error shape for `on_error="collect"` — critical for frontend error display |
| `SECURITY.md` | Data retention policy, PHI boundary documentation, vulnerability reporting |

---

## Open Source Considerations

1. **Library is independently installable**: `pip install x12-edi-tools` — no web app dependency
2. **Minimal dependencies**: Base install requires only `pydantic>=2.0`. Optional extras: `x12-edi-tools[excel]` (adds `openpyxl`), `x12-edi-tools[pandas]` (adds `pandas`), `x12-edi-tools[all]` (both)
3. **Typed**: `py.typed` marker + strict mypy for IDE autocomplete
4. **Extensible**: Adding new payers = add directory under `payers/`. Adding new transaction types = add segment models + loop models + register in SEGMENT_REGISTRY
5. **No secrets or hardcoded values in code**: No API keys, no SFTP credentials. Provider/payer identity values flow through `SubmitterConfig`, not hardcoded constants
6. **No proprietary content**: `metadata/` is gitignored. All fixtures are synthetic. Payer rules are original abstractions.
7. **PHI safe**: No PHI in logs, fixtures, or published artifacts
8. **MIT License**: Maximum permissiveness for forks
9. **SECURITY.md**: Clear vulnerability reporting process and PHI handling notes
10. **CONTRIBUTING.md + CODE_OF_CONDUCT.md**: Standard OSS governance


