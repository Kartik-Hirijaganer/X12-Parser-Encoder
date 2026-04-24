# Serverless Migration + Frontend Design Platform — Implementation Plan

| | |
|---|---|
| **Status** | Draft, awaiting sign-off |
| **Owner** | Platform + Frontend |
| **Source of truth** | `docs/plans/serverless-terraform-architecture-restructure.md` |
| **Supersedes** | Phase 4+ of [docs/plans/cloudfront-url-stability.md](cloudfront-url-stability.md). Phases 1–3 of that plan (shell-script containment) still ship first and are load-bearing. |
| **Risk class** | Production-facing; cuts over the hosted API; touches every frontend page |

---

## 1. Executive Summary

### Why

The current deploy pipeline runs the API on **AWS legacy managed container service** behind a **CloudFront+S3** SPA. That costs ~$25–40/mo idle, has a churning CloudFront URL (an existing bug tracked by the `cloudfront-url-stability` plan), and forces OSS operators to navigate ECR + legacy managed container service trust roles before they can fork. On top of that, the frontend has an excellent token system but no enforcement, no transient-feedback primitives (toast, modal, error boundary), and no animation layer — the UX is crisp visually but cognitively heavier than it needs to be.

### What

Two mostly-independent tracks, delivered across **ten delivery phases** (five infra + three frontend + docs + release hardening), plus Phase 0 shared contracts and Phase 0.5 release baseline presteps. Three tracks can run in parallel with minimal coordination, so multiple agents can work without interfering:

- **Track A — Serverless migration** (Phases 1–5). Replace legacy managed container service with a single Lambda Function URL behind the existing CloudFront distribution, provisioned entirely via Terraform. Keep the SPA on S3. No VPC, no ALB, no ECS, no ECR unless the Lambda artifact approaches the 250 MB unzipped zip-package ceiling or native dependency packaging forces a container image.
- **Track B — Frontend design platform** (Phases 6–8). Consolidate the design spec into a single enforceable document, add the missing primitives (Toast, Modal, Drawer, Tooltip, Skeleton, ProgressBar, EmptyState, ErrorBoundary, ConfirmationDialog), add an animation layer (Framer Motion with motion tokens), and lint the whole thing so agents can't drift.
- **Track C — Documentation consolidation** (Phase 9). Rewrite `docs/architecture.md`, regenerate `docs/api/openapi.yaml` from FastAPI, add Mermaid diagrams to the README, and write an ADR for the serverless decision.

### Where my recommendation differs from your brief

Seven substantive points — five disagreements, two amendments — all integrated below rather than argued separately:

1. **Library mount point — zip-bundle, not Lambda Layer.** You asked where the library should live; a Lambda Layer is the wrong answer for a single-function deployment. Layers add separate versioning, a 5-layer cap per function, and a second CI pipeline. Bundling the `x12-edi-tools` wheel into the function zip keeps one artifact, one version, one deploy. Layers pay off when many functions share a heavy runtime; we have one function. AWS allows larger zipped artifacts when deployed from S3, but the hard ceiling is 250 MB unzipped across the function package and layers. Fall back to a container image only if the unzipped artifact approaches that ceiling or native wheel packaging becomes unreliable.
2. **CloudFront → Lambda Function URL uses an origin-secret header, not SigV4 OAC, in v1.** AWS supports CloudFront OAC for Lambda Function URLs, but OAC requires `AuthType=AWS_IAM`, and AWS documents a material caveat for `POST`/`PUT`: browser clients must provide an `x-amz-content-sha256` payload hash because Lambda Function URLs do not support unsigned payloads. That is a poor fit for this multipart-upload SPA. v1 is therefore: Lambda Function URL `AuthType=NONE`; CloudFront injects `X-Origin-Verify: <shared-secret>`; FastAPI middleware rejects production requests missing or mismatching the secret with 403. This means the Function URL remains a public internet endpoint and direct unauthenticated calls still reach Lambda, but they receive 403 before app work. We cap blast radius with reserved concurrency, short timeouts, PHI-safe logs, and alarms on direct-origin 403 volume. Secret rotation is dual-key (`current` + `previous`) to survive CloudFront propagation.
3. **Keep in-memory rate limiting removal as a precondition.** Your brief treats cold-start mitigation and rate-limiting as independent concerns. They're not: `_rate_limit_lock` and `_in_flight_uploads` in [apps/api/app/core/middleware.py:29-32](apps/api/app/core/middleware.py#L29-L32) are process-local, so in Lambda every invocation sees an empty window — the limiter would silently stop working. Remove the app-level limiter entirely; rely on **AWS WAF rate-based rules** (Phase 4) plus **Lambda reserved concurrency** as the hard ceiling.
4. **Function URL over API Gateway, agreed — but make it a Terraform variable.** Default `var.api_origin = "function_url"`. Keep the `api_gateway` path as a swap-in module for operators who need per-route auth or usage plans later.
5. **Amend the design system, don't override it.** Your brief asks for toasts; the current `docs/design-system.md` forbids toasts for important outcomes (section 7). That rule exists for a reason — users miss transient messages. Instead of replacing it, amend: **toasts are permitted for transient success confirmations and low-urgency info; banners remain mandatory for any error the user must act on.** This preserves the reason behind the old rule while closing the feedback gap.
6. **Release baseline moves before the first RC.** The current `bump_version.py` and `release.yml` cannot correctly cut `1.0.0-rc.N` releases. A new Phase 0.5 adds prerelease SemVer parsing, prerelease GitHub Release flags, and release validation before Phase 3 tags `v1.0.0-rc.1`. Phase 10 remains, but it becomes release hardening rather than the first time RC support appears.
7. **Build Lambda artifacts for the runtime architecture.** Default the first zip deployment to `x86_64` because GitHub-hosted runners and native wheels match that path cleanly. Keep `var.lambda_architecture` operator-tunable. If we switch to `arm64`, the package step must run inside an AL2023 Lambda-compatible arm64 build container or use explicit cross-platform wheel installation; otherwise `pydantic-core` and similar native wheels can be built for the wrong architecture.

### 1.1 Hosting choice — why AWS and not Netlify / Vercel / Cloudflare

You raised Netlify as a possible alternative. I considered it and am still recommending AWS, because the "cheap" constraint and the "deals with patient data" constraint collide on every non-AWS platform we'd realistically pick:

| Platform | BAA availability | Minimum cost with BAA | Python backend story | Same-origin with our SPA? |
|---|---|---|---|---|
| **AWS** (this plan) | Free, signed at account creation | ~$1–8/mo at demo scale | Lambda runs Python 3.12 natively | Yes — CloudFront is one origin |
| **Netlify** | Enterprise only | **~$1,500/mo+** | JS-only functions; Python means separate cloud anyway | No — SPA on Netlify, API elsewhere |
| **Vercel** | Enterprise only | **~$1,500/mo+** | Python runtime is beta / limited | No — same split |
| **Cloudflare Pages + Workers** | Enterprise | ~$200/mo | Python via Pyodide is preview, not prod | Possible via Workers, but Python story is thin |

Compliance basis for this call:
- [HHS OCR cloud computing guidance](https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html) — a cloud provider that creates, receives, maintains, or transmits ePHI is a Business Associate and requires a BAA.
- [AWS HIPAA Eligible Services](https://aws.amazon.com/compliance/hipaa-eligible-services-reference/) — every service in this plan (Lambda, CloudFront, S3, CloudWatch Logs, KMS, ACM, Route 53, WAF) is covered.
- [Netlify HIPAA announcement](https://www.netlify.com/blog/netlify-launches-a-hipaa-compliant-service-offering) — HIPAA offering is enterprise-only.

**The honest framing of this trade-off:**

- If the deployed instance **never** touches real PHI — i.e. it is a portfolio demo hosted under your name against synthetic fixtures and you will never put it in front of a real submitter — Netlify is fine, free, and the SPA deploys with `git push`. You would then host the API on AWS Lambda anyway (Python FastAPI has no first-class home on Netlify), so you end up with a two-cloud setup, a CORS configuration, and you still need the AWS BAA for the API. Net: you save nothing and add complexity.
- If the deployed instance **might** touch real PHI — i.e. a fork operator configures their real clearinghouse credentials, or you demo to a prospective customer and they upload a live 270 — every byte has to traverse a BAA-covered path. Netlify's free and Pro tiers explicitly disclaim PHI in their terms. Using Netlify here would be a compliance incident waiting for a screenshot.
- The repo's `CLAUDE.md` says "Treat all fixture data as synthetic only. Never add real patient data." That's the right policy for commits. It does not bind what a running deployed instance will receive from users pasting files into a drop zone. A hosting layer that forbids PHI is the wrong match for software that accepts 270/271/837 uploads.

**Decision.** AWS-first, via a single CloudFront distribution with S3 + Lambda origins. This is the only option that is both cheap (~$1–8/mo) and HIPAA-compatible (free BAA) at this scale. The **product requirement is a stable public endpoint**, not literally the `*.cloudfront.net` hostname — a custom domain on the same distribution satisfies the contract equally well and is promoted from "optional Phase 5" to "day-1 recommended" for operators who control a DNS zone.

**Escape hatch for pure-demo operators.** The SPA is a framework-agnostic static bundle — nothing in Phases 6–8 ties it to S3. An operator who (a) will never process real PHI and (b) wants zero AWS touch on the frontend can run `npm run build` and deploy `apps/web/dist` to Netlify/Vercel/Cloudflare Pages with a `netlify.toml` or `vercel.json`, set `VITE_API_BASE_URL` to the CloudFront API URL (`https://<distribution>/api/v1` or the custom-domain equivalent), and accept that CORS re-enters the picture. Do **not** point this path at the raw Lambda Function URL while origin-secret middleware is enabled; the browser cannot supply the CloudFront-only origin header. I'll document this in `docs/runbooks/alternative-spa-hosting.md` (Phase 9) but it is **not** the default path and it is **not supported for PHI workloads**.

**Why not full Cloudflare Pages + Workers.** Cloudflare is the only non-AWS option with a reasonable BAA price. But Workers is V8-only; Python via Pyodide cold-starts at 200+ MB of WASM and is marked preview. Migrating `x12-edi-tools` to run under Pyodide would take weeks and the library would still fail for any dependency that isn't pure Python. Not worth the investment for a ~$150/mo saving that we don't need.

### 1.2 Cost (fork operator, post-free-tier)

| Service | Cost |
|---|---|
| Lambda (1M req/mo + 400k GB-s free forever) | $0 |
| Lambda Function URL | $0 |
| CloudFront (SPA + API; 1 TB egress free year 1) | ~$0.50/mo for a demo |
| S3 (SPA bucket, a few MB) | ~$0.10/mo |
| CloudWatch Logs | ~$0.10/mo |
| Route 53 (optional, Phase 5) | $0.50/mo per hosted zone |
| ACM | $0 |
| WAF (optional, Phase 4) | ~$6/mo if enabled — gated behind `var.enable_waf` |
| **Total, minimal demo** | **~$1/mo** |
| **Total, production-hardened with WAF + custom domain** | **~$8/mo** |

Compare: Netlify Enterprise (to get the BAA) is ~$18,000/yr minimum. Vercel Enterprise is similar. legacy managed container service (our current state) is ~$25–40/mo idle. The serverless-on-AWS path is roughly 20–2000× cheaper than any BAA-eligible alternative.

### 1.3 Versioning & release trajectory

Current version: `0.1.1`. This migration ships as **`1.0.0`** — the major bump is driven by a breaking **deployment contract** (legacy managed container service → Lambda, `make deploy` semantics change, `rate_limit_enabled` env var goes inert, `/metrics` endpoint disabled under Lambda), not by a library API break. The PyPI library `x12-edi-tools` has zero public-API changes in this migration; we accept the monorepo-wide bump per the existing "three artifacts, one release train" philosophy in [CLAUDE.md](../../CLAUDE.md). The release notes must state this explicitly so downstream library consumers (if they ever appear) aren't misled.

Tagging cadence during the migration:

```
0.1.1           current
1.0.0-rc.1      end of Phase 3  (first working serverless staging)
1.0.0-rc.2      end of Phase 4  (hardening + SnapStart validated)
1.0.0-rc.3      end of Phase 7  (frontend primitives landed)
1.0.0           end of Phase 8  (production cutover, legacy managed container service deleted)
1.0.1           after Phase 9   (docs + auto-regen, patch-only release)

Going forward:
  1.0.x → patches
  1.x.0 → additive (new endpoints, new primitives, new library functions)
  2.0.0 → next architectural migration OR genuine library-API break
```

Each `rc.N` tag triggers the Phase 0.5 release workflow and publishes a GitHub **pre-release** (not marked "Latest"). Fork operators can pin to any RC for staged rollout. The `1.0.0` tag at Phase 8 is the first release marked "Latest" in the v1 line. Phase 10 adds release hardening: Lambda zip as release artifact, Terraform module tarball, tag protection, and release-drafter.

### Demo cadence

Every phase below ends in a demo the user can click through. No phase is only internal plumbing.

---

## 2. Architecture (target state)

```
Browser
  │  HTTPS (stable URL — raw *.cloudfront.net OR custom domain)
  ▼
CloudFront distribution (single, stable ID, Terraform-owned)
  │   custom origin header: X-Origin-Verify: <secret value>
  ├── default behavior     ──►  S3 bucket (SPA, versioned, private via OAC + SigV4)
  └── "/api/*" behavior    ──►  Lambda Function URL (AuthType=NONE; public
                                 internet endpoint; app middleware rejects any
                                 production request missing X-Origin-Verify)
                                 │
                                 ▼
                            Lambda (Python 3.12, x86_64 default, optional arm64
                                 when the package builder targets arm64;
                                 SnapStart on supported regions via published
                                 versions routed by "live" alias)
                            ├── Mangum adapter
                            ├── FastAPI app (apps/api/app) — request/response adapter only
                            └── x12-edi-tools wheel (all X12 core logic; bundled in zip)
                                      │
                                      ▼
                                CloudWatch Logs + CloudWatch EMF metrics (PHI-safe)
```

Notes:
- S3→CloudFront uses SigV4 OAC (that's what OAC for S3 is designed for; no body caveats).
- CloudFront→Lambda does **not** use Lambda OAC in v1. It uses a custom origin header and FastAPI middleware. The raw Lambda Function URL remains publicly reachable and must be treated as an internet-exposed origin that should only return cheap 403 responses without the secret.
- The `live` alias points at a published Lambda version so SnapStart can apply in regions/runtimes that support Python SnapStart. Old versions are cleaned up each deploy (default keep count = 3).

- **Single CloudFront distribution.** The hostname is stable because Terraform owns it; CloudFront URL stability (the existing plan) becomes automatic.
- **Same-origin frontend↔API.** Browser never leaves `*.cloudfront.net` (or the custom domain). Zero CORS surface, one TLS handshake.
- **Stateless.** No DynamoDB, no Redis, no RDS. Uploads stream into memory, are processed, and are discarded. The only persistent state is the Terraform state bucket itself.
- **HIPAA-eligible services only.** Lambda, Function URLs, CloudFront, S3, CloudWatch Logs, KMS, ACM, Route 53, WAF. Existing BAA covers all of them.

---

## 3. Phase Dependency Graph

```
Phase 0.5 (release baseline) ────────────────┐
Phase 1 (backend code) ──┐                   ├──► Phase 3 (deploy pipeline)  ──► Phase 4 (hardening)  ──► Phase 5 (custom domain) ──┐
                         ├───────────────────┘                    │                      │                                          │
Phase 2 (terraform) ─────┘                                  tag 1.0.0-rc.1         tag 1.0.0-rc.2                                   │
                                                                                                                ▼
Phase 6 (design enforcement) ──► Phase 7 (primitives) ──► Phase 8 (UX polish, cutover) ──► Phase 9 (docs) ──► Phase 10 (release hardening)
                                           │                          │                         │                     │
                                    tag 1.0.0-rc.3              tag 1.0.0                  tag 1.0.1           infra/policy for tags
```

**Parallelization.** Phases 0.5 / 1 / 2 / 6 can run concurrently the moment Phase 0 lands. Phase 3 blocks on 0.5+1+2, Phase 7 blocks on 6, Phase 8 blocks on 7. Phase 9 sweeps docs. Phase 10 lands last and hardens the release process that Phase 0.5 made minimally usable.

**Shared constants file** (Phase 0, trivial): create `infra/shared/constants.tf.json` and `apps/api/app/core/lambda_config.py` up front so Phase 1 and Phase 2 agree on function name, env-var names, and log group name without coordination.

### 3.1 Execution Strategy Table

| Order | Run | Strategy | Start after | Why / output |
|---|---|---|---|---|
| 1 | **Phase 0 — Shared contracts** | Run first, alone | Plan approval | Creates shared names and the ADR stub so backend and Terraform agents do not drift. |
| 2 | **Phases 0.5, 1, 2, and 6** | Run in parallel | Phase 0 | Release baseline, Lambda app adaptation, Terraform modules, and design linting do not overlap much. |
| 3 | **Phase 3 — Deploy pipeline** | Run in sequence | Phases 0.5 + 1 + 2 | First real serverless staging deploy; proves Lambda, Terraform, and release tagging work together. |
| 4 | **Phase 4 — Hardening** | Run in sequence | Phase 3 | Adds WAF, SnapStart where supported, alarms, and stricter headers after staging works. |
| 5 | **Phase 5 — Custom domain** | Optional sequence | Phase 4 | Adds branded DNS/certificate support; can be skipped for raw CloudFront-only deployments. |
| 6 | **Phase 7 — UX primitives** | Run in parallel with infra sequence | Phase 6 | Can proceed while Phases 3-5 continue; adds the missing UI primitives. |
| 7 | **Phase 8 — UX polish + production cutover** | Run in sequence | Phase 7 + production infra readiness | Applies page-level UX improvements, retires legacy managed container service, and cuts `1.0.0`. |
| 8 | **Phase 9 — Docs consolidation** | Run in sequence | Phase 8 | Rewrites architecture docs, runbooks, OpenAPI generation, and drift checks for the final architecture. |
| 9 | **Phase 10 — Release hardening** | Run last | Phase 9 | Adds release-drafter, tag protection docs, artifact polish, and final release process checks. |

---

## 4. Phase 0 — Shared contracts (30 min, blocks nothing)

Not really a phase; a five-minute pre-step to prevent merge conflicts between Phase 1 and Phase 2 agents.

**Deliverables:**
- `infra/shared/names.json` — one dict containing `app_name`, `function_name_prefix`, `log_group_prefix`, `api_prefix`, `env_var_names` (as a list of strings). Both Phase 1 (reads it in tests) and Phase 2 (reads it via Terraform `jsondecode(file(...))`) consume this as a single source of truth.
- `docs/plans/ADR-001-serverless.md` — short ADR capturing the seven decisions in §1.

**Validation:**
- `make check-version-sync` still passes.
- `terraform fmt -check` passes on the JSON (N/A but confirms no syntax breakage for Phase 2).

---

## 4a. Phase 0.5 — Release baseline (0.5 day, blocks Phase 3 tagging)

**Goal.** Make the first `1.0.0-rc.1` tag valid before the deploy pipeline needs it. This is the minimum release engineering needed early; Phase 10 still handles draft automation, tag protection, and release polish.

**Scope:**
- `scripts/bump_version.py` — accept SemVer prerelease versions such as `1.0.0-rc.1`, plus helper modes:
  ```bash
  python scripts/bump_version.py rc
  python scripts/bump_version.py final
  ```
- `scripts/check_version_sync.py` — validate prerelease versions consistently across `VERSION`, package metadata, README, and lockfiles.
- `.github/workflows/release.yml` — mark `v*-rc.*`, `v*-alpha.*`, `v*-beta.*`, and `v*-dev.*` tags as `prerelease: true` and `make_latest: false`. Final tags remain latest.
- `.github/workflows/release-validate.yml` or an equivalent first job inside `release.yml` — fail before publishing if the pushed tag and `VERSION` disagree or the changelog has no section for the version.

**Validation:**
- `python scripts/bump_version.py 1.0.0-rc.1 && make check-version-sync` passes.
- Pushing a dry-run `v1.0.0-rc.99` tag creates a prerelease, not a latest release.
- Pushing a tag that does not match `VERSION` fails before any artifact is published.

---

## 5. Phase 1 — FastAPI Lambda adaptation (backend code, ~1 day)

**Goal.** Make `apps/api/app` boot correctly under Mangum on Lambda while still running under `uvicorn` locally in `docker-compose`. No infra changes in this phase.

**Library boundary reaffirmed.** The `packages/x12-edi-tools` library stays framework-agnostic and owns all X12 parse / encode / validate logic. The API (`apps/api/app`) does request/response adaptation only: input validation, multipart upload handling, correlation IDs, error shaping, CloudWatch emission. Any business logic that sneaks into a router during this phase must be moved down into the library before Phase 1 closes.

### Scope — files touched

- [apps/api/app/main.py](apps/api/app/main.py) — keep the existing top-level `/healthz` for local/container use, add the Mangum handler in a separate module, and skip the static-frontend mount when `X12_API_DEPLOYMENT_TARGET=lambda`.
- [apps/api/app/core/middleware.py](apps/api/app/core/middleware.py) — (a) delete `_rate_limit_lock`, `_request_windows`, `_in_flight_lock`, `_in_flight_uploads`, and the two helper functions; collapse to correlation-id, size check, auth-boundary, logging (CORS block stays as inert defense-in-depth). (b) Add a new `OriginSecretMiddleware` that runs when `deployment_target == "lambda"` and `origin_secret_enabled == True`, rejecting any request whose `X-Origin-Verify` header does not match `settings.origin_secret` or `settings.origin_secret_previous` with a 403 and a structured log line (no secret in the log). Dev/local bypass via config flag. Secret values are supplied via Lambda environment variables; Terraform state is therefore sensitive even if Secrets Manager is used as the source of truth.
- [apps/api/app/core/config.py](apps/api/app/core/config.py) — add `deployment_target: Literal["lambda","container","local"] = "local"` and origin-secret settings under the existing `X12_API_` prefix, including deployment target, enabled flag, current value, and previous value. Deprecate `rate_limit_enabled` (log a warning if set true under `lambda`).
- [apps/api/app/core/metrics.py](apps/api/app/core/metrics.py) — emit CloudWatch EMF ([Embedded Metric Format](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html)) log lines when `deployment_target=lambda`. EMF is parsed by CloudWatch automatically — no SDK calls, no cold-start hit. Keep the Prometheus endpoint for the container/local path.
- [apps/api/pyproject.toml](apps/api/pyproject.toml) — add `mangum>=0.18,<1.0` as an extra `[project.optional-dependencies].lambda = ["mangum>=0.18,<1.0"]`.
- `apps/api/app/lambda_handler.py` (new, ~10 lines) — `from mangum import Mangum; from app.main import app; handler = Mangum(app, lifespan="off")`.
- `apps/api/tests/test_lambda_handler.py` (new) — unit tests for: (a) handler import and `/api/v1/health` round-trip, (b) upload round-trip with base64 body, (c) origin-secret middleware rejects a request without the header in `lambda` mode, (d) origin-secret middleware accepts a request with either current or previous header value, (e) PHI-safe logging — no X12 body content, filename, or member ID appears in captured log records.

### Detailed tasks (in order)

1. **Delete state.** Remove the four module-level dicts/locks from [middleware.py:29-32](apps/api/app/core/middleware.py#L29-L32) and the `_check_rate_limit`, `_acquire_upload_slot`, `_release_upload_slot` functions. Update the middleware to skip the rate-limit and slot-acquisition blocks. Keep the size check and correlation-id logic verbatim.
2. **Add Lambda handler.** Write `apps/api/app/lambda_handler.py`:
   ```python
   from mangum import Mangum
   from app.main import app
   handler = Mangum(app, lifespan="off")
   ```
   Do not set `api_gateway_base_path`: CloudFront forwards `/api/v1/...` unchanged to the Function URL, and the FastAPI router is already mounted at `/api/v1`.
3. **Gate the static mount.** In [main.py:43-80](apps/api/app/main.py#L43-L80), wrap `_register_frontend(app)` in `if settings.deployment_target != "lambda":`. Under Lambda, CloudFront serves the SPA from S3 directly; the Lambda never needs to serve static files, and shipping them in the zip wastes 2–3 MB.
4. **Add CloudWatch EMF emitter.** In `core/metrics.py`, add a `_emit_emf(metric_name, value, unit, dimensions)` function that writes a single-line JSON log in the EMF schema. Wire it into `record_request` behind `if settings.deployment_target == "lambda": _emit_emf(...)`. Keep the Prometheus path untouched.
5. **Add deployment_target to config.** In `core/config.py`, read from `X12_API_DEPLOYMENT_TARGET`, default `"local"`, pydantic-Literal-typed. Add origin-secret settings with the same prefix.
6. **Write the Lambda unit test.** Load a real Function URL / APIGW-v2-style event JSON from `apps/api/tests/fixtures/function_url_health.json` (new fixture), invoke `handler(event, None)`, assert `statusCode == 200` for `/api/v1/health`. Do the same for one upload endpoint with a base64-encoded small file — this validates Mangum's binary body handling.
7. **Local smoke.** `uvicorn app.main:app` must still work with `X12_API_DEPLOYMENT_TARGET=local`. Pre-existing tests stay green.

### Validation — Phase 1 done when

- `cd apps/api && pytest` is green, including the two new Lambda tests.
- `cd apps/api && pytest tests/test_lambda_handler.py -v` shows Mangum handling upload + health.
- `grep -r "_rate_limit_lock\|_in_flight_uploads" apps/api` returns zero matches.
- `mypy --strict apps/api/app` is clean.
- `uvicorn app.main:app --host 0.0.0.0 --port 8000` boots and serves `/healthz`, `/api/v1/health`, and the SPA.
- `make lint typecheck test-api` green.

### Demo

- Developer runs `pytest tests/test_lambda_handler.py -v` — sees a synthetic API-Gateway-v2 upload round-trip through Mangum.
- `curl http://localhost:8000/healthz` and `curl http://localhost:8000/api/v1/health` both return OK under uvicorn.

---

## 6. Phase 2 — Terraform foundation + modules (infra, ~2 days, parallel to Phase 1)

**Goal.** Stand up a clean Terraform repo tree that provisions the full stack. No deploy yet — Phase 3 wires it into CI.

### Scope — new files

```
infra/
├── terraform/
│   ├── backend.hcl.example          # S3+DDB backend config, operator copies and fills
│   ├── bootstrap/
│   │   └── main.tf                  # creates the tfstate bucket + lock table (run once per account)
│   ├── environments/
│   │   ├── example/                 # fork-operator starting point
│   │   │   ├── main.tf              # wires root modules with safe defaults
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── terraform.tfvars.example
│   │   ├── staging/
│   │   └── production/
│   └── modules/
│       ├── lambda_api/              # Lambda + public Function URL + origin-secret env
│       ├── s3_spa/                  # Private SPA bucket + OAC
│       ├── cloudfront_distribution/ # Distribution with SPA default + /api/* behaviors
│       ├── waf/                     # Optional — gated by var.enable_waf
│       ├── custom_domain/           # Optional — Phase 5
│       └── observability/           # CloudWatch log groups + metric filters + alarms
```

### Module contracts (spec-level, sufficient for the Phase 2 agent to implement)

**`modules/lambda_api`**
- Inputs: `function_name`, `zip_path` or `s3_bucket + s3_key` (or `image_uri` for fallback), `environment_vars` (map), `memory_mb` (default 1024), `timeout_s` (default 30), `lambda_architecture` (default `x86_64`), `enable_snapstart` (default false until Phase 4), `reserved_concurrency` (default 10, operator-tunable), `log_retention_days` (default 14).
- Resources: `aws_lambda_function` (runtime `python3.12`, architecture from `lambda_architecture`), `aws_lambda_alias.live`, `aws_lambda_function_url` attached to the alias with `AuthType = NONE`, the required public `aws_lambda_permission` for Function URL invocation (`principal = "*"`, constrained by `function_url_auth_type = "NONE"`), and `aws_cloudwatch_log_group` named `/aws/lambda/${function_name}` with retention. No Lambda OAC and no CloudFront-scoped Lambda URL permission in v1.
- Outputs: `function_url_domain`, `function_arn`, `invoke_arn`, `log_group_name`.

**`modules/s3_spa`**
- Inputs: `bucket_name`.
- Resources: private bucket (BlockPublicAcls, ObjectOwnership BucketOwnerEnforced), server-side encryption (SSE-S3; bump to SSE-KMS if `var.kms_key_arn != null`). The bucket policy that grants CloudFront OAC access is attached in the environment root after the CloudFront distribution ARN exists, avoiding a module-level dependency cycle.
- Outputs: `bucket_regional_domain_name`, `bucket_arn`.

**`modules/cloudfront_distribution`**
- Inputs: `spa_bucket_regional_domain`, `lambda_function_url_domain`, `origin_verify_header_value` (sensitive), `price_class` (default `PriceClass_100`), `enable_waf` (bool), `waf_web_acl_arn` (optional), `response_headers_policy_id` (created here).
- Resources: `aws_cloudfront_origin_access_control` for S3 only, `aws_cloudfront_distribution` with two origins + two behaviors:
  - Default → S3 origin, `CachingOptimized` policy, `Redirect-to-HTTPS`.
  - `/api/*` → Lambda Function URL origin, `CachingDisabled` policy, `AllViewerExceptHostHeader` origin-request policy, allowed methods `GET HEAD OPTIONS PUT POST PATCH DELETE`, and `custom_header { name = "X-Origin-Verify", value = var.origin_verify_header_value }`.
  - SPA fallback is implemented with a CloudFront Function viewer-request rewrite for non-file, non-`/api/` paths to `/index.html`. Do not use global 403/404 custom error responses, because they can mask API errors as HTML.
  - `aws_cloudfront_response_headers_policy` with HSTS (1 year, preload), X-Content-Type-Options, Referrer-Policy `strict-origin-when-cross-origin`, Content-Security-Policy (start permissive; tighten in Phase 4).
  - `viewer_certificate.minimum_protocol_version = "TLSv1.2_2021"`.
- Outputs: `distribution_id`, `domain_name`, `distribution_arn`.

**`modules/waf`** — Phase 4; stub out in Phase 2 with `count = var.enable_waf ? 1 : 0`.

**`modules/custom_domain`** — Phase 5; stub out.

**`modules/observability`**
- Inputs: `function_name`, `alarm_sns_topic_arn` (optional).
- Resources: CloudWatch metric filters on the Lambda log group for `X-Correlation-ID` extraction and `error_code` counts; alarms for 5xx rate, throttles, high latency p95, cold-start frequency (via SnapStart `InitDuration` filter).

### Backend & state

- `bootstrap/main.tf` creates `${var.app_name}-tfstate-${data.aws_caller_identity.current.account_id}-${var.aws_region}` (versioned, encrypted, PublicAccessBlock) and `${var.app_name}-tflocks` DynamoDB table. Run manually once per account.
- Root state path is `${APP_ENV}/terraform.tfstate`.

### Detailed tasks (in order)

1. Write `bootstrap/main.tf` and document the bootstrap runbook in `infra/terraform/README.md` (new).
2. Write each module in isolation with its own `variables.tf`, `main.tf`, `outputs.tf`, `versions.tf` (pin `aws` ~> 5.60, `hashicorp/tls`).
3. Write the `environments/example/` wiring — the only "integration" file. Set defaults that produce a runnable plan:
   - `enable_waf = false`
   - `enable_snapstart = false`
   - `lambda_architecture = "x86_64"`
   - `price_class = "PriceClass_100"`
   - `memory_mb = 1024`
4. For each module, add a module-level README with inputs, outputs, and one usage example. This is the agent-readable contract for downstream changes.
5. In `environments/example/`, add a dummy `zip_path` (a 10-byte placeholder) so `terraform plan` can run before Phase 3 produces the real zip. The plan agent will document this explicitly.
6. Add `.terraform.lock.hcl` committed (lockfile) and `.gitignore` entries for `terraform.tfstate*`, `*.tfvars` (except `.example`), `.terraform/`.

### Validation — Phase 2 done when

- `cd infra/terraform/environments/example && terraform init -backend=false && terraform validate` passes.
- `terraform fmt -check -recursive infra/terraform` passes.
- `tflint` and `tfsec` (both added to Phase 3's CI) pass locally with zero critical findings.
- Each module README documents every input and output.
- `terraform plan` against the `example` environment with a placeholder zip produces a creation plan of the expected shape (1 Lambda, 1 alias, 1 Function URL with `AuthType=NONE`, 1 public Function URL permission, 1 S3 OAC, 1 distribution, 1 SPA bucket, 1 log group, policies).
- No module references another module's resources directly — all cross-module wiring happens in `environments/*/main.tf`.

### Demo

- `terraform plan` against a real AWS sandbox account shows a clean green creation plan for a fork operator.

---

## 7. Phase 3 — Deploy pipeline + staging cutover (~2 days, depends on 0.5+1+2)

**Goal.** Ship the Lambda to a real staging environment and route real traffic through it. First end-to-end demo.

### Scope — files touched

- `.github/workflows/deploy.yml` — replace the legacy managed container service/ECR flow and change the trigger semantics:
  - **Staging** — triggered automatically on `push` to `main` (path-filtered to code that affects the deploy: `apps/**`, `packages/**`, `infra/terraform/**`, `scripts/package_lambda.sh`, `VERSION`). No manual action required; every merge hits staging.
  - **Production** — **manual only**, via `workflow_dispatch` with an `environment` input whose allowed values are `staging` and `production`. Production deploys require clicking "Run workflow" in the Actions UI and selecting `production`. Wire to a GitHub protected environment so production also requires a reviewer approval if you configure one in repo settings.
  - `concurrency: deploy-${{ inputs.environment || 'staging' }}` with `cancel-in-progress: false`, so S3 sync, Terraform apply, and CloudFront invalidation cannot overlap for the same environment.
  - Single workflow file (not one-per-environment); the environment input drives the `-var-file` Terraform picks (`environments/staging/terraform.tfvars` vs `environments/production/terraform.tfvars`) and the OIDC role assumed.
  - Pipeline steps (same for both environments):
    1. Build web (`npm run build`).
    2. Package Lambda zip via `scripts/package_lambda.sh` (new) — builds inside an AL2023 Lambda-compatible Python 3.12 environment for the selected architecture, installs prod deps into a clean dir, wheels the `x12-edi-tools` library, adds `apps/api/app`, zips everything. Output: `build/lambda.zip`.
    3. Upload the zip to `s3://${tfstate_bucket}/lambda-artifacts/${environment}/${git_sha}.zip`.
    4. `terraform init -backend-config=environments/${environment}/backend.hcl && terraform apply -auto-approve -var "lambda_zip_s3_key=..." -var-file=environments/${environment}/terraform.tfvars`.
    5. Sync the SPA to the S3 bucket (output from Terraform).
    6. CloudFront invalidate `/*`.
    7. Post a summary to `$GITHUB_STEP_SUMMARY` with: environment, git SHA, CloudFront URL, Lambda version, Terraform plan hash.
- `scripts/package_lambda.sh` (new).
- `scripts/bootstrap_tf_backend.sh` (new) — idempotent bootstrap runner.
- `Makefile` — **cut over `make deploy` to the serverless path immediately**. Changes:
  - Rename the existing legacy managed container service target `deploy` → `deploy-apprunner-legacy` (kept through Phase 8 as a break-glass, removed in Phase 8's cleanup).
  - New `make deploy` target = the serverless pipeline. Requires `ENV=staging` or `ENV=production`. Refuses to run without `ENV` set (no default — a missing env is a bug, not a default). Defends against the old muscle memory by `@echo "make deploy now deploys via Lambda+CloudFront. ENV=$(ENV). Ctrl-C to abort."; sleep 3` in the first line.
  - Add supporting targets: `make lambda-package`, `make terraform-plan ENV=...`, `make terraform-apply ENV=...`, `make deploy-invalidate ENV=...`.
  - Both local `make deploy ENV=production` and the GitHub Actions manual run end up in the same Terraform state and produce identical artifacts.
- `.github/workflows/terraform-plan.yml` (new) — on PR, runs `fmt`, `validate`, `tflint`, `tfsec`, `plan` with no `apply`. Posts the plan as a PR comment.
- `.github/workflows/terraform-drift.yml` (new, scheduled weekly) — runs `plan`, opens a GitHub issue on any non-zero diff.
- `apps/api/pyproject.toml` — ensure `lambda` optional-dep group includes only `mangum`; move `uvicorn[standard]` out of base dependencies into a local/server extra so the Lambda zip does not carry ASGI server dependencies it never uses.
- `packages/x12-edi-tools/pyproject.toml` — no change.
- `README.md` deploy section — update to reference the new pipeline; document `make deploy ENV=staging|production` and the workflow-dispatch path.

### Detailed tasks (in order)

1. **Write `scripts/package_lambda.sh`.** Must be deterministic: build wheels for `packages/x12-edi-tools` and `apps/api`, install `apps/api[lambda]` into `build/lambda/` in a Lambda-compatible Python 3.12 environment for `var.lambda_architecture`, strip `__pycache__`, strip `.dist-info/RECORD`, zip with `-X` (no extra attributes) for reproducible hashes. Default architecture is `x86_64`; if `arm64` is selected, the builder must explicitly target arm64.
2. **Add package-size gates** as script steps:
   - warn when zipped artifact exceeds 50 MB (it must be uploaded through S3, which this pipeline already does);
   - warn at 200 MB unzipped;
   - fail at 240 MB unzipped, leaving headroom under Lambda's 250 MB unzipped package limit;
   - fallback decision at failure: switch to container image (add `docker/lambda.Dockerfile`, reuse/create ECR repo).
3. **Wire GitHub OIDC** to a new deploy role `${app_name}-deploy-${app_env}` (Terraform-managed in `environments/*/main.tf`). Scope to the exact state bucket/table, artifact prefix, SPA bucket, Lambda function/alias, and CloudFront distribution. Avoid `terraform:*`; grant the AWS API actions Terraform actually needs for this stack.
4. **Staging cutover.** First deploy to `staging` environment. Verify:
   - `curl https://<staging-cf-domain>/api/v1/health` returns 200 via Lambda.
   - Browser loads the SPA, drag-and-drops a fixture file, sees the Preview + Result pages work.
   - CloudWatch Logs show structured JSON with correlation IDs.
5. **Production serverless readiness gate.** After 48 hours of staging soak with fixture traffic, production may be deployed behind the serverless stack for final verification, but legacy managed container service is not retired until Phase 8.
6. **Legacy path stays intact.** Keep `make deploy-apprunner-legacy` through Phase 8 as break-glass. Do not move/delete legacy managed container service artifacts in Phase 3.
7. **Cold-start measurement.** Before enabling SnapStart (Phase 4), record baseline p50 / p95 cold-start InitDuration from a 50-request sample with 15-min idle gaps between calls. This is the data we compare against in Phase 4 acceptance.

### Validation — Phase 3 done when

- A push to `main` with a trivial change triggers the pipeline, which completes in < 5 min and updates the Lambda + SPA without changing the CloudFront distribution ID.
- `terraform state list` shows every new serverless AWS resource under Terraform management. Legacy legacy managed container service resources may remain outside this state until Phase 8 deletion/import cleanup.
- Two consecutive deploys output the identical CloudFront domain and distribution ID.
- The staging URL loads the app and all existing pages work end-to-end.
- `make test` green.
- Rollback drill: `terraform apply -var "lambda_zip_s3_key=lambda-artifacts/<previous_sha>.zip"` restores the previous version in under 2 minutes.

### Demo

- Developer merges a PR that changes a UI string.
- CI runs in ~4 min.
- Browser reload shows the change.
- Same CloudFront URL as before.

### Release tag at the end of this phase

- `python scripts/bump_version.py 1.0.0-rc.1` → commit → `git tag v1.0.0-rc.1 && git push --tags`.
- Phase 0.5 release plumbing fires, publishes a **pre-release** GitHub Release. If `scripts/package_lambda.sh` is available in this phase, attach the Lambda zip and SHA256; otherwise attach it in the next release after packaging lands.

---

## 8. Phase 4 — Security, performance, observability hardening (~2 days, depends on 3)

**Goal.** Turn on the "production" knobs that are trivial in Terraform but meaningful for security and UX: SnapStart, WAF, response-headers policy, CloudWatch alarms.

### Scope

- **SnapStart + live alias + version cleanup.** Flip `enable_snapstart = true` only in regions/runtimes where Python SnapStart is supported. SnapStart only accelerates *published* versions, not `$LATEST`. Terraform publishes via `aws_lambda_function.publish = true` and points an `aws_lambda_alias` named `live` at the new version; Function URL is attached to the alias, not `$LATEST`. Add a deploy-time cleanup step (`scripts/prune_lambda_versions.sh`) that keeps the N most recent published versions (default N=3) and deletes the rest; without this, published versions accumulate and each stores a full SnapStart snapshot.
- **Reserved concurrency.** Set `reserved_concurrency = 50` in production; `10` in staging. Prevents runaway spend under abuse.
- **AWS WAF.** Set `enable_waf = true` in production. Module adds:
  - `AWSManagedRulesCommonRuleSet` (ACL rules)
  - `AWSManagedRulesKnownBadInputsRuleSet`
  - Rate-based rule: 2000 requests / 5 min / IP
  - Size-restriction rule: reject request bodies above the app contract before Lambda. Default to 6 MB at the edge, while the application keeps its 5 MB upload limit for a clear API error below Lambda's synchronous payload ceiling.
  - Optional: geo-match allow-list (default: no geo filter).
- **Response headers policy.** Tighten from Phase 2 defaults:
  - CSP: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'`
  - HSTS: `max-age=63072000; includeSubDomains; preload`
  - Permissions-Policy: minimal (block microphone, camera, geolocation, payment).
- **CloudWatch alarms.** Via `modules/observability`:
  - 5xx rate > 1% of invocations / 5 min → SNS.
  - Throttles > 0 / 5 min → SNS.
  - Duration p95 > 3s → SNS (catches cold-start regression).
  - Lambda errors > 5 / 5 min → SNS.
- **SnapStart cold-start verification.** Run the same 50-request sample from Phase 3 in a SnapStart-supported region and assert p50 InitDuration materially improves. Keep a numeric target only after baseline measurement; do not hard-code a 300 ms SLO before data.

### Detailed tasks

1. Set `enable_snapstart = true` in production environment config only when the selected AWS region supports Python SnapStart. Keep the module default false for fork-operator portability.
2. Implement the `waf` module with the four rules above. Wire into `cloudfront_distribution` via `web_acl_id`.
3. Implement the response-headers policy resource inside `cloudfront_distribution`.
4. Implement the four alarms in `modules/observability`. The SNS topic + subscription is operator-supplied (variable) — defaults to `null` (no alerting), but the alarms exist and fire if wired up.
5. Write `docs/runbooks/lambda-cold-start.md` and `docs/runbooks/waf-ip-unblock.md` (short, 1 page each).

### Validation — Phase 4 done when

- `securityheaders.com` scores the production CloudFront URL A or A+.
- SnapStart-enabled cold-start p50 improves materially versus the Phase 3 baseline in supported regions, or SnapStart is disabled with a documented region/runtime reason.
- WAF blocks a synthetic `curl` burst of 2100 requests from one IP (rate rule fires; confirm via 403 responses plus WAF sampled requests/logs).
- Browser DevTools → Security tab shows HSTS, CSP, X-Content-Type-Options all present.
- CloudWatch Alarms page shows all four alarms in `OK` state.
- Synthetic chaos test: inject a 500 in one endpoint, confirm the alarm fires within 5 min.

### Demo

- Run a Locust / `hey` burst against the production URL — WAF blocks after the rate limit, and the dashboard in CloudWatch shows the rule hit.
- Click Network tab in DevTools → see HSTS + CSP headers.

### Release tag at the end of this phase

- `python scripts/bump_version.py 1.0.0-rc.2` → tag `v1.0.0-rc.2`. Pre-release on GitHub.

---

## 9. Phase 5 — Custom domain (optional, ~0.5 day + DNS TTL, depends on 4)

**Goal.** Operator flips `var.custom_domain = "app.example.com"` and `var.dns_provider = "route53"` and gets a stable branded URL.

### Scope

- `modules/custom_domain/`:
  - `aws_acm_certificate` in `us-east-1` with DNS validation.
  - Route 53 ALIAS record (if `dns_provider = "route53"` and `var.hosted_zone_id` supplied).
  - CloudFront distribution `aliases = [var.custom_domain]`, `viewer_certificate.acm_certificate_arn = aws_acm_certificate.this.arn`.
- For non-Route-53 operators, the module outputs the required CNAME / validation records; the operator adds them to their provider manually.

### Validation

- `dig app.example.com` resolves to CloudFront.
- `curl https://app.example.com/api/v1/health` returns 200.
- The original `*.cloudfront.net` URL continues to work (no regression).
- Certificate auto-renews at year minus one day (ACM default).

### Demo

- Browser navigates to `https://app.example.com`.

---

## 10. Phase 6 — Design system centralization + enforcement (frontend, ~1.5 days, parallel to 1–5)

**Goal.** One file that agents read before writing UI code, and an ESLint rule set that fails the build when they don't.

### Scope — files touched / created

- `docs/design-spec.md` (new, ~300 lines) — the single-entry-point design manifesto. Imports-by-reference the two detailed docs (keep them as appendices); adds the **amended toast policy** (§1.5); adds an **Agent Contract** section at the top with the five hard rules:
  1. Read `docs/design-spec.md` before any UI change.
  2. Never hardcode hex, px, ms — use `tokens.css` tokens.
  3. Never hand-roll `<button>`, `<input type=file>`, `<table>` — use primitives.
  4. Every new visual pattern is a triplet PR: spec + primitive + test.
  5. Running `make design-lint` must pass locally before commit.
- `docs/design-system.md` and `docs/ui-components.md` — prepend a notice pointing agents at `design-spec.md`; otherwise unchanged.
- `apps/web/src/styles/tokens.css` — audit, fill gaps (add `--spacing-*` tokens explicitly so spacing has token coverage, not just Tailwind's scale).
- `apps/web/eslint.config.mjs` — enable the new local plugin using ESLint v9 flat-config syntax.
- `apps/web/.eslint-plugin-design-system/` (new local ESLint plugin, ~200 lines) with these rules:
  - `design-system/no-raw-color` — fails on `#[0-9a-fA-F]{3,8}` in JSX className strings and style objects, except in `tokens.css`.
  - `design-system/no-arbitrary-tw` — fails on Tailwind arbitrary values like `p-[13px]`, `bg-[#abc]`, `rounded-[7px]` except when the argument is `var(--...)`.
  - `design-system/primitive-required` — fails on raw `<button>`, `<input type="file">`, `<table>` in files under `components/features/**` and `pages/**`; primitives in `components/ui/` are allowed to use native elements.
  - `design-system/no-inline-animation` — fails on raw `transition:`, `animation:` in inline styles; require use of motion tokens.
- `apps/web/package.json` — add `"lint:design": "eslint src --config eslint.config.mjs"` after wiring the local design-system plugin into the flat config. Do not use legacy `--rulesdir` / `--no-eslintrc`; this repo is on ESLint v9 flat config.
- `Makefile` — add `design-lint: cd apps/web && npm run lint:design` target.
- `.pre-commit-config.yaml` — leave unchanged by default. The existing hooks plan centralizes repo-specific guards behind `make check-guards`; design lint is enforced through Makefile + CI, with an optional pre-commit hook documented but not required.
- `.github/workflows/ci.yml` — add `design-lint` job, fail the build on rule violations.
- [CLAUDE.md](../../CLAUDE.md) — under the `### Frontend` section, replace the "Before writing any UI code, read..." bullet with a pointer to the single `docs/design-spec.md` file.

### Detailed tasks

1. Draft `docs/design-spec.md` in three parts: Agent Contract (top), Visual Theme (condensed from `design-system.md`), Primitive Catalog (condensed from `ui-components.md`, linking to them for details).
2. Add spacing tokens to `tokens.css` (`--space-1` through `--space-12`, 4 px scale). Audit the tree for any `p-[Npx]` or `m-[Npx]` and replace with named tokens.
3. Write the ESLint plugin. Use AST-level rules (`no-restricted-syntax` patterns) rather than regex where possible. Provide auto-fixes where safe (e.g., `bg-[#ffffff]` → `bg-[var(--color-surface-primary)]`).
4. Wire the CI + Makefile steps. If a pre-commit hook is desired later, add it as a separate policy change rather than burying it in this migration.
5. Run the linter across the existing tree, fix all violations.

### Validation — Phase 6 done when

- `make design-lint` returns exit 0 on a clean tree.
- Introducing `className="text-[#ff0000]"` in a test file causes `make design-lint` to fail.
- Introducing a raw `<button>` in `apps/web/src/pages/HomePage.tsx` causes `make design-lint` to fail.
- `CLAUDE.md` points at one file (`docs/design-spec.md`) instead of two.
- CI job `design-lint` is green on `main`.

### Demo

- Create a PR that violates one rule; watch CI fail with a pointer to the right doc section.
- Create a compliant PR; watch it pass.

---

## 11. Phase 7 — Missing UX primitives + error handling (frontend, ~2 days, depends on 6)

**Goal.** Add the primitives that are missing today, so Phase 8 can compose them.

### Scope — new primitives under `apps/web/src/components/ui/`

- `Toast.tsx` — headless toast pipeline using `sonner` (lightweight, no render-root churn). Wrap `sonner` to force variant-only use (`toast.success`, `toast.info`). Banner is still the way to show actionable errors.
- `Modal.tsx` — Radix `@radix-ui/react-dialog` wrapped for tokens, with focus trap, ESC handling, overlay animation.
- `Drawer.tsx` — Radix dialog with side-slide animation.
- `Tooltip.tsx` — Radix tooltip, 300ms open delay (matches `--duration-slow`).
- `Skeleton.tsx` — pulsing surface primitive; accepts `width`, `height`, `radius` as props or token names.
- `ProgressBar.tsx` — determinate + indeterminate variants.
- `EmptyState.tsx` — icon + headline + copy + optional CTA.
- `ErrorBoundary.tsx` — React error boundary that renders a friendly fallback using `EmptyState` + an action that reloads the route.
- `ConfirmationDialog.tsx` — composed from `Modal`, opinionated prop API (`destructive?: boolean`, `onConfirm`, `onCancel`).

Global wiring:
- `apps/web/src/main.tsx` or `App.tsx` — wrap the route tree in `<ErrorBoundary>` and mount `<Toaster />` at the top level.
- `apps/web/src/services/api.ts` — extend `buildApiError` to also `toast.error` for 5xx that the user cannot act on, while still returning the `ApiError` so pages can render banners for 4xx actionables.

### Detailed tasks

1. Install deps: `sonner`, `@radix-ui/react-dialog`, `@radix-ui/react-tooltip`, `framer-motion` (Phase 8 uses this too — install once). No others.
2. Build each primitive with (a) vitest test, (b) Storybook-free gallery route at `/__ui` gated behind a dev-only flag (`import.meta.env.DEV`), (c) one documented usage example pasted into `docs/ui-components.md`.
3. Write the `ErrorBoundary` and wire it at the router level — errors inside one route do not blow away the rest of the app.
4. Migrate the existing "copy to clipboard success" interaction on the Generate Result page from the current silent clipboard write to a `toast.success("Copied X12 to clipboard")`.

### Validation — Phase 7 done when

- `cd apps/web && npm run test` green.
- All 9 new primitives are exported from `components/ui/index.ts`.
- `docs/design-spec.md` primitive catalog updated (and `docs/ui-components.md` appendix).
- `ErrorBoundary` catches a deliberately-thrown error in a test route and renders the fallback.
- `toast.success` fires and auto-dismisses on copy-to-clipboard.
- ESLint `design-system/primitive-required` passes.

### Demo

- Dev loads `/__ui` gallery, clicks through every primitive.
- Deliberately triggers a React error in a child route — sees the graceful fallback, not a white screen.

### Release tag at the end of this phase

- `python scripts/bump_version.py 1.0.0-rc.3` → tag `v1.0.0-rc.3`. Pre-release on GitHub. This RC is the "frontend-ready" milestone for any fork operator who wants the primitives but not the full cutover.

---

## 12. Phase 8 — UX polish, animation, low-cognitive-load pass + production cutover (frontend, ~2 days, depends on 7)

**Goal.** Every user flow feels smooth, progressive, and obvious. Fewer clicks, more visual cues, less text.

### Scope — changes to existing pages

- **Home page** — reinforce drag-and-drop affordance: dashed-border file drop zone pulses subtly when a file is being dragged over the window (Framer Motion on dragstart listener). Replace the three text action cards with icon-heavy cards: each card has a 48 px icon, one-line label, one-sentence description. Keep the descriptions — they prevent the "what does this button do" dead-end.
- **Preview page** — add a `ProgressBar` while the file is processing (currently shows a spinner only). Show the file name + size + row count as soon as parsing completes. Add a `Skeleton` for the table while rows are being parsed.
- **Generate Result page** — replace silent clipboard copy with `toast.success`. Add a "show 10 first segments" expand affordance so the user doesn't stare at a wall of X12 unless they ask.
- **Validate Result page** — if pass, render a success banner + auto-scroll to the Export button. If fail, lead with a one-sentence summary ("3 critical issues, 8 warnings"), collapse the details table, let the user expand if they want.
- **Dashboard page** — reorder stat cards by status priority (errors first), color-code obviously, make each card clickable to filter the table. Add an `EmptyState` when the table has zero rows instead of "no data" text.
- **Settings page** — add inline validation hints with green check icons for each validated field. Replace "save" with an auto-save-on-blur + toast confirmation.
- **Global**
  - Add Framer Motion route transitions (200 ms fade+slide) via `<AnimatePresence>` in the router outlet.
  - **Respect `prefers-reduced-motion`.** Wrap the animation layer in a `useReducedMotion()` hook that short-circuits to instant transitions when the OS setting is on. Applies to route transitions, toast entry, modal entry, drawer slide, skeleton pulse, and the drop-zone drag pulse. This is accessibility, not polish — audit every `motion.*` component for it.
  - Add keyboard shortcuts (`?` opens a shortcuts dialog; `Esc` closes modals; `g` then `d` → Dashboard, à la Linear). Use a minimal in-house shortcut map, not a library.
  - Audit every `setError(...)` path — decide banner vs toast based on actionability. Actionable (field-level, user can retry) → banner; non-actionable (5xx, timeout) → toast + banner, with different wording.

### Detailed tasks

1. Write `apps/web/src/hooks/useFileDropAffordance.ts` and apply it to the Home drop zone.
2. Rewrite each page per the above, shipping one PR per page so reviews stay tight.
3. Add `apps/web/src/components/KeyboardShortcuts.tsx` (help dialog) and `apps/web/src/hooks/useKeyboardShortcut.ts`.
4. Update `docs/design-spec.md` "Motion" chapter with the route-transition pattern.

### Validation — Phase 8 done when

- Click-through demo: a non-technical user completes Generate, Validate, and Parse flows without reading any paragraph of copy.
- Every success case that completes without navigating shows a toast.
- Every actionable error shows a banner with a next-action button.
- Every table with zero rows shows an `EmptyState`.
- Lighthouse accessibility score ≥ 95 on all routes.
- Lighthouse best-practices score ≥ 95.
- Manual timing: dashboard paint-to-interactive < 500 ms on a cold load against a 100-row dataset.
- With OS-level "Reduce motion" enabled, all transitions become instant; no entrance animations play; no skeleton pulses. Vitest covers at least one primitive to prove the branch is wired.

### Demo

- Screen-share of a new user completing the full spreadsheet → X12 → validated flow in under 60 seconds without asking what to click.

### Production cutover + release tag at the end of this phase

This is the phase that **retires legacy managed container service**. Tasks specific to cutover:
1. Delete `scripts/deploy_aws.sh` and `make deploy-apprunner-legacy`.
2. Delete the legacy managed container service service + ECR repo via Terraform (or via a documented AWS CLI runbook if they were never imported into Terraform).
3. Remove all legacy managed container service/ECR references from README, CLAUDE.md, and docs (the Phase 9 grep gate catches residuals).
4. Update the version table, bump: `python scripts/bump_version.py 1.0.0` → tag `v1.0.0` → push.
5. `release.yml` fires, publishes a GitHub Release marked **"Latest"** (not pre-release), attaches Lambda zip + Docker image + PyPI wheel + Terraform modules tarball. This is the first v1 "stable" release.

---

## 13. Phase 9 — Documentation consolidation + auto-regeneration (~2 days, depends on 8)

**Goal.** Docs are correct, diagrammed, scannable — and the parts that can be derived from code stay current automatically with CI-enforced drift detection.

### 13.1 Initial consolidation (one-time)

- `docs/architecture.md` — rewrite with:
  - A Mermaid diagram of the target state (from §2 above).
  - A sequence diagram of one request (browser → CloudFront → Lambda).
  - A clear "why serverless" paragraph pointing at `ADR-001-serverless.md`.
  - Explicit statelessness contract (no DB, no queue, uploads in-memory).
- `docs/api/openapi.yaml` — switch from hand-written to generated. Add `scripts/generate_openapi.py` that does `from app.main import app; json.dumps(app.openapi())`. Wire into `make docs`.
- `docs/diagrams/` (new) — Mermaid source for every diagram, rendered to SVG via `mmdc` (optional) in `make docs`. Split into `docs/diagrams/authored/` (human-owned) and `docs/diagrams/generated/` (script-owned, never hand-edited).
- `README.md` — add the Mermaid architecture diagram (top), update the deploy section to point at the new pipeline (`make deploy ENV=…` + workflow_dispatch), update the version table, add a "Fork this repo and deploy to your own AWS account" quickstart.
- `docs/runbooks/` — `deploy-rollback.md`, `lambda-cold-start.md`, `waf-ip-unblock.md`, `custom-domain.md`, `open-source-fork.md` (the quickstart), `self-hosted-docker-compose.md` (non-AWS path; not PHI-supported; operator owns their own BAA).
- `docs/plans/ADR-001-serverless.md` — formalized from Phase 0 stub. Must include the Netlify rejection rationale verbatim from §1.1 and links to [HHS OCR cloud guidance](https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html), [AWS HIPAA Eligible Services](https://aws.amazon.com/compliance/hipaa-eligible-services-reference/), [Netlify HIPAA announcement](https://www.netlify.com/blog/netlify-launches-a-hipaa-compliant-service-offering).
- `scripts/check_version_sync.py` — extend to validate `infra/terraform/modules/*/versions.tf` provider-pin annotation carries the repo version (soft check).

### 13.2 Auto-regeneration system (what keeps it current)

**Philosophy.** Only artifacts that are mechanically derivable from code get auto-regenerated. Prose, rationale, and the top-of-README architecture diagram stay human-authored — auto-rewriting those with LLMs invites hallucination and churn. What's auto-regenerated is inert: tables, schemas, and dependency graphs.

**Auto-regenerated artifacts and their sources of truth:**

| Artifact | Source | Generator |
|---|---|---|
| `docs/api/openapi.yaml` | FastAPI `app.openapi()` | `scripts/generate_openapi.py` |
| README "API endpoint" table | generated OpenAPI | `scripts/update_readme.py` (marker block) |
| README "Project structure" table | `git ls-tree` + directory metadata | same script, different marker |
| README "Version" table | `VERSION` file | already handled by `bump_version.py` |
| `docs/api-routes.mmd` (Mermaid) | FastAPI route inspection | `scripts/generate_route_diagram.py` |
| `docs/erd.svg` | Pydantic models in library | already wired via `eralchemy` in `make docs` |
| `docs/diagrams/generated/module-deps.svg` | Python AST import graph | `scripts/generate_module_graph.py` (uses `pydeps`) |

**Artifacts that stay human-owned (never auto-regenerated):**

- The top-of-README architecture diagram — it's *about* the design, not derived from the code. A new router doesn't change whether the architecture is "Browser → CloudFront → Lambda."
- All prose in README, `architecture.md`, ADRs, runbooks.
- `docs/design-spec.md` and `docs/ui-components.md` — human-authored design contracts.

**Marker-block system.** Each auto-regenerated region in a prose document is bracketed with HTML comments the generator looks for:

```markdown
<!-- autogen:api-endpoints:start -->
(generator replaces everything between these markers)
<!-- autogen:api-endpoints:end -->
```

The generator only touches content inside matching markers. A missing start tag aborts with a clear error; prose outside markers is never modified; conflicts surface as PR diffs, not silent rewrites.

### 13.3 Orchestrator + Make target

- `scripts/docs_regenerate.py` (new) — single entry point that runs all generators in order: OpenAPI → route diagram → module graph → ERD → README block replacements. Idempotent: running twice produces identical output. Exits non-zero on any generator failure with an actionable message.
- `Makefile` — add `make docs-regenerate` (runs the orchestrator) and `make docs-check` (runs the orchestrator against a tempdir, diffs, fails on drift). Existing `make docs` still validates OpenAPI and renders diagrams; `docs-regenerate` is the authoritative write path.

### 13.4 CI drift gate

- `.github/workflows/docs-drift.yml` (new):
  - Trigger: `pull_request` with path-filter on `apps/api/app/routers/**`, `apps/api/app/schemas/**`, `packages/x12-edi-tools/src/**`, `infra/terraform/**`, `VERSION`. Editing only `docs/` or `apps/web/**` does NOT trigger the check (saves CI minutes).
  - Steps: checkout → `pip install -e` the library + API → run `make docs-regenerate` → `git diff --exit-code` on `docs/` and `README.md`. Non-zero exit fails the PR.
  - On failure: workflow posts a PR comment with the diff and a one-line fix instruction (`run \`make docs-regenerate\` and commit the result`).

### 13.5 Bot auto-commit on merge (optional, gated)

- `.github/workflows/docs-autocommit.yml` (new, can be disabled by repo setting):
  - Trigger: `push` to `main` with the same path-filter as 13.4.
  - Uses a GitHub App installation token (not a PAT) so the commit is attributable to a bot identity, not a person.
  - Runs `make docs-regenerate`, `git add`, commits with message `chore(docs): autoregen [skip ci]`.
  - The `[skip ci]` prevents recursion — the CI drift gate does not re-run on the bot commit.
  - If you want to own every commit manually instead, delete this workflow; the drift gate alone prevents drift by failing any PR that merges with stale generated docs.

### 13.6 Architecture-diagram review nudge (soft check, not auto-regen)

- `.github/workflows/architecture-review-nudge.yml` (new):
  - Trigger: `pull_request` touching `infra/terraform/modules/**` or `apps/api/app/main.py`.
  - Posts a PR comment: "You changed infrastructure or the app entrypoint. Please confirm `docs/architecture.md` and the README Mermaid diagram still reflect the target state, or update them in this PR."
  - Not a blocker — human judgment call whether the diagram needs an update. This is the escape valve for the "can't auto-regen architecture prose" constraint.

### Detailed tasks (in order)

1. Write `scripts/generate_openapi.py`. Replace `docs/api/openapi.yaml` with the generated output. Diff and ensure no schema regressions against the current hand-written spec.
2. Write `scripts/generate_route_diagram.py` (introspects `app.routes` and emits Mermaid) and `scripts/generate_module_graph.py` (uses `pydeps`).
3. Write `scripts/update_readme.py` with the marker-block substitution engine. Add the marker blocks to `README.md` and `docs/architecture.md`.
4. Write `scripts/docs_regenerate.py` orchestrator.
5. Wire `make docs-regenerate` and `make docs-check`.
6. Write `.github/workflows/docs-drift.yml`; dry-run on a PR that deliberately mutates a router to confirm the gate catches drift.
7. (Optional) Write `.github/workflows/docs-autocommit.yml` and configure the GitHub App credentials in repo secrets.
8. Write `.github/workflows/architecture-review-nudge.yml`.
9. Write the six runbooks as short (< 1 page) command-forward docs.
10. Render all Mermaid diagrams and embed in README + architecture.md.
11. Update `CLAUDE.md` sections that reference legacy managed container service, ECR, or the old deploy script — retire those paragraphs.
12. Run `make docs-regenerate` on `main` so the initial committed state is clean.

### Validation — Phase 9 done when

- `make docs` passes (validates OpenAPI, renders diagrams).
- `make docs-regenerate` is idempotent: running it twice produces identical output (no diff on second run).
- `make docs-check` on a clean tree passes; on a tree where someone edited a router without regenerating, fails with a clear diff.
- PR simulation: a branch that adds a new FastAPI endpoint without running `make docs-regenerate` is blocked by the CI drift gate.
- PR simulation: a branch that edits `infra/terraform/modules/lambda_api/main.tf` gets the architecture-review-nudge comment but is not blocked.
- `README.md` renders the architecture Mermaid diagram correctly on GitHub.
- All six runbooks have a "you should be done in < 5 min" at the top.
- `rg "legacy managed container service" README.md CLAUDE.md docs --glob '!docs/plans/**'` returns zero matches; archived plans under `docs/plans/` are retained as historical decision records and are intentionally excluded.
- `rg "ECR" README.md CLAUDE.md docs --glob '!docs/plans/**'` returns only current container-image fallback references; archived plans under `docs/plans/` are intentionally excluded.
- The hand-written sections of README and `architecture.md` are byte-identical before and after `make docs-regenerate` (the marker-block system never touches prose).

### Demo

- Push the README change; verify diagrams render on the GitHub PR page.

### Release tag at the end of this phase

- `python scripts/bump_version.py 1.0.1` → tag `v1.0.1`. First post-v1 patch release. Docs-only. GitHub Release marked "Latest" in the v1 line.

---

## 13a. Phase 10 — Release hardening (~1 day, depends on 9)

**Goal.** Harden the release process after Phase 0.5 made RC tags minimally correct. Make future releases correct by construction, not by discipline.

### Scope — files touched / created

- `.github/workflows/release.yml` — extend the existing workflow:
  - **Pre-release detection audit.** Confirm the Phase 0.5 implementation still marks `v*-rc.*`, `v*-dev*`, `v*-alpha*`, and `v*-beta*` releases as `prerelease: true` and `make_latest: false`. This repo uses `softprops/action-gh-release`, not `actions/create-release`.
  - **Lambda zip artifact.** Add a job step that runs `scripts/package_lambda.sh`, attaches `lambda-${VERSION}-py312-${LAMBDA_ARCHITECTURE}.zip` as a release asset, and publishes the SHA256 next to it. Fork operators grab this for Terraform deploys without rebuilding.
  - **Terraform modules tarball.** `tar czf terraform-modules-${VERSION}.tar.gz -C infra/terraform modules/`. Attach as a release asset. Version-locked modules for operators who pin.
  - **Release notes validation audit.** Keep the Phase 0.5 validation in the same workflow job chain as publishing, or make `release.yml` depend on a reusable validation job. Do not rely on an independent workflow ordering guarantee between two separate tag-triggered workflows.
- `.github/workflows/release-drafter.yml` (new) + `.github/release-drafter.yml` config — auto-drafts the next release's notes from merged PR titles as PRs land, grouping by label (`feat`, `fix`, `breaking`, `chore`, `docs`). The draft lives as an unpublished "Draft" release on GitHub; cutting a version = tagging + the draft flips to published. Removes hand-maintenance of CHANGELOG for most entries.
- `.github/workflows/release-validate.yml` or a reusable `validate` job in `release.yml` — already introduced in Phase 0.5; harden it here:
  - Verifies `VERSION` file matches the tag.
  - Verifies `bump_version.py` ran on the files it's supposed to touch (re-runs `check_version_sync.py`).
  - Verifies a CHANGELOG entry exists for this version.
  - Fails fast if any check misses — the broken release never publishes.
- `scripts/bump_version.py` — already accepts RC / pre-release suffixes from Phase 0.5; add tests and polish helper behavior:
  ```bash
  python scripts/bump_version.py 1.0.0-rc.1   # already works (explicit X.Y.Z form)
  python scripts/bump_version.py rc           # new: bump the rc number of current pre-release
  python scripts/bump_version.py final        # new: strip pre-release suffix (1.0.0-rc.3 → 1.0.0)
  ```
- **GitHub repo settings (documented, not code):**
  - Add a **tag protection rule** for `v*.*.*` tags: only the release workflow's GitHub App identity can create them. Prevents a developer accidentally pushing a tag from their laptop.
  - Add a **branch protection rule** on `main` that requires `release-validate` and `docs-drift` checks before merge.
  - Configure the protected `production` GitHub environment to require a reviewer approval for `workflow_dispatch` on the production deploy.
- `docs/runbooks/cutting-a-release.md` (new) — short operator-facing runbook:
  1. Decide the version (rc bump? final? patch?).
  2. Run `python scripts/bump_version.py <target>`.
  3. Verify `git diff` shows only version-bearing files.
  4. Commit, push, tag `vX.Y.Z`.
  5. Workflow takes over. Watch it publish.
  6. Rollback: `git revert` the bump commit and delete the tag + release (documented commands).

### Detailed tasks (in order)

1. Audit Phase 0.5 prerelease detection and validation; keep validation in the release workflow's dependency chain so a race cannot publish a bad release.
2. Extend `release.yml` with Lambda zip asset, Terraform tarball asset, and SHA256 publication. Dry-run by creating a tag on a throwaway branch.
3. Write `release-drafter.yml` + config. Merge two labeled PRs and verify the draft release body populates correctly.
4. Add/extend unit tests for `bump_version.py` prerelease suffix parsing and `rc` / `final` helper modes.
5. Configure tag protection and branch protection via repo settings (documented; GitHub CLI commands noted in the runbook).
6. Write `docs/runbooks/cutting-a-release.md`.
7. Update `README.md` "Releases" section (marker block from Phase 9) to point at GitHub Releases as the canonical distribution channel.
8. Final dry-run: cut `v1.0.1` (the Phase 9 patch release) through the new pipeline end-to-end — validates the whole system works on a real release.

### Validation — Phase 10 done when

- Tagging `v1.0.1-rc.99` on a test branch still creates a GitHub Release marked **pre-release**. Tagging `v1.0.1` creates one marked **Latest**. Confirmed by inspection of the Releases page.
- Tagging `v999.999.999` without running `bump_version.py` fails `release-validate` before `release.yml` starts — no half-published artifacts.
- Merging a PR labeled `feat:` adds a bullet to the Draft release body automatically.
- The `v1.0.1` GitHub Release (Phase 9's patch) has the Lambda zip + Terraform modules tarball + Docker image + PyPI wheel attached.
- `python scripts/bump_version.py rc` on current `1.0.0-rc.2` produces `1.0.0-rc.3` (and passes `check_version_sync`).
- `python scripts/bump_version.py final` on current `1.0.0-rc.3` produces `1.0.0`.
- Tag protection blocks a local `git push origin v1.0.2` (confirmed by attempt and expected rejection).
- `docs/runbooks/cutting-a-release.md` walk-through takes a second person (not the author) under 5 minutes end-to-end.

### Demo

- Cut `v1.0.1` live on screen: bump, commit, tag, push, watch the three workflows chain (validate → release-drafter finalize → release publish), browse the published Release page with all artifacts attached.

---

## 14. Cross-cutting concerns

### Version sync

[scripts/bump_version.py](../../scripts/bump_version.py) currently touches eight files. New files to include in `check_version_sync.py`:
- `apps/api/app/lambda_handler.py` — no version string (exclude).
- `infra/terraform/modules/lambda_api/variables.tf` — optional: pin the app version as a default `var.app_version` for observability tagging. If we do, register it.
- `infra/terraform/environments/*/terraform.tfvars.example` — same.

Safer default: do **not** pin the app version in Terraform variables; pass it at `terraform apply` time from the pipeline via `-var "app_version=$(cat VERSION)"`. This removes the version-sync burden entirely.

Phase 0.5 extends `bump_version.py` with `rc` and `final` helper modes for the RC workflow; Phase 10 adds tests and release hardening.

### Secrets hygiene

- No AWS credentials in Terraform state (use IAM roles).
- The CloudFront origin-secret header value will be present in Terraform state because CloudFront custom origin headers are stateful configuration. Treat the backend bucket, DynamoDB lock table, CI logs, and local plan files as sensitive. Use S3 backend encryption, bucket policy least privilege, versioning, and short-lived OIDC roles.
- Origin-secret rotation uses two accepted values in the app (`current` and `previous`): deploy Lambda accepting both, update CloudFront to send the new value, wait for distribution deployment, then remove the previous value.
- No `.env` files committed.
- `detect-secrets` pre-commit hook already runs; no changes needed.

### PHI / HIPAA

Nothing in this plan introduces a PHI storage path. Continue to:
- Never log raw X12 payloads, names, or member IDs.
- Never persist uploads anywhere (Lambda `/tmp` is scratch only).
- Keep browser storage limited to non-PHI settings; never store uploaded files, generated X12, parsed patient data, names, member IDs, or payer responses in localStorage/sessionStorage.

### Rollback playbook per phase

- Phase 1: `git revert`; API reverts to pre-Mangum. No infra impact.
- Phase 2: delete the `infra/terraform` tree. No live infra yet.
- Phase 3: Terraform `apply` with the previous zip S3 key (< 2 min). If terraform state corrupts, `terraform state rm` + `terraform import` the live resources back into state — documented in `docs/runbooks/terraform-recover.md`.
- Phase 4: set `enable_waf=false`, `enable_snapstart=false`, re-apply.
- Phase 5: remove the `aliases` block from the distribution; DNS still resolves (TTL permitting).
- Phases 6–8: git revert. Design-lint failures are the CI gate; no production impact.
- Phase 9: docs-only, revert.

### Observability — end-to-end correlation

Existing correlation-id flow ([apps/api/app/core/middleware.py:55](apps/api/app/core/middleware.py#L55)) works as-is under Lambda. Add:
- Lambda emits the correlation ID as a CloudWatch Log field (already does, JSON formatter).
- Enable CloudFront standard logs or real-time logs for production if incident reconstruction is required. CloudWatch metric filters cannot join CloudFront and Lambda logs; correlation is by Lambda `X-Correlation-ID`, CloudFront `x-edge-request-id`, timestamp, path, and viewer IP during investigations.
- X-Ray tracing: enable via `aws_lambda_function.tracing_config.mode = "Active"` if the operator sets `var.enable_xray = true`. Off by default (costs per span).

---

## 15. Parallelization guide for agents

Three agents can start immediately:

| Agent | Phase | Touches | Doesn't touch |
|---|---|---|---|
| **A** | Phase 1 | `apps/api/app/**`, `apps/api/tests/**`, `apps/api/pyproject.toml` | `infra/`, `apps/web/` |
| **B** | Phase 2 | `infra/terraform/**`, `scripts/bootstrap_tf_backend.sh`, `infra/shared/names.json` | `apps/api/`, `apps/web/` (except reading the config) |
| **C** | Phase 6 | `docs/design-spec.md`, `apps/web/eslint.config.mjs`, `apps/web/.eslint-plugin-design-system/`, `apps/web/src/styles/tokens.css`, `Makefile` (design-lint target only), `CLAUDE.md` | `apps/api/`, `infra/` |

Merge conflicts avoided by:
- Each agent only touches the Makefile in its own dedicated target (B adds `terraform-*`, A adds nothing, C adds `design-lint`).
- `.github/workflows/ci.yml` changes are isolated to Phase 3 and Phase 6 — both agents edit non-overlapping jobs.
- The shared contract file `infra/shared/names.json` is Phase 0 (a 5-min pre-step).

Once Phase 0.5 and agents A/B/C land, Phase 3 (needs 0.5 + A + B) and Phase 7 (needs C) can start in parallel. Phase 4/5 are serial after 3. Phase 8 is serial after 7. Phase 9 waits on all.

---

## 16. Critical files to read before starting implementation

- [apps/api/app/main.py](apps/api/app/main.py) — the FastAPI entry point. Five-line Mangum change goes here.
- [apps/api/app/core/middleware.py](apps/api/app/core/middleware.py) — the stateful counters to remove live here.
- [apps/api/app/core/config.py](apps/api/app/core/config.py) — where `deployment_target` is added.
- [apps/api/app/core/metrics.py](apps/api/app/core/metrics.py) — add the EMF emitter here.
- [apps/api/pyproject.toml](apps/api/pyproject.toml) — add the `lambda` extra here.
- [packages/x12-edi-tools/pyproject.toml](../../packages/x12-edi-tools/pyproject.toml) — confirm pandas stays an optional extra.
- [scripts/deploy_aws.sh](../../scripts/deploy_aws.sh) — the shell script we are retiring.
- [.github/workflows/deploy.yml](../../.github/workflows/deploy.yml) — the workflow we are replacing.
- [apps/web/src/styles/tokens.css](../../apps/web/src/styles/tokens.css) — the token source of truth.
- [apps/web/eslint.config.mjs](../../apps/web/eslint.config.mjs) — add the design-system plugin here.
- [docs/design-system.md](../design-system.md) and [docs/ui-components.md](../ui-components.md) — the source material for `docs/design-spec.md`.
- [docs/plans/cloudfront-url-stability.md](cloudfront-url-stability.md) — the existing plan; Phases 1–3 are still load-bearing.

---

## 17. End-to-end verification (entire plan)

After Phases 0.5–10 ship, run this full-system regression from a fresh fork:

1. `git clone` → `cd X12-Parser-Encoder` → `make install` → `make test` green locally.
2. `bash scripts/bootstrap_tf_backend.sh` once against a clean AWS account.
3. `cd infra/terraform/environments/example && cp terraform.tfvars.example terraform.tfvars && <edit>` → `terraform apply`.
4. `make deploy ENV=example` → pipeline completes, prints the CloudFront URL.
5. Open the URL in a browser → upload the fixture spreadsheet at `apps/web/public/templates/sample-eligibility.xlsx` → Generate → download X12 → Parse → Dashboard → Export workbook.
6. DevTools Network tab shows all requests are `*.cloudfront.net` (no CORS calls).
7. DevTools Security tab shows HSTS, CSP, TLS 1.2+.
8. CloudWatch Logs has JSON entries with correlation IDs matching `X-Correlation-ID` response headers.
9. Push a trivial UI change → pipeline redeploys in < 5 min → CloudFront URL unchanged.
10. Run `k6 run scripts/load/health.js` against `/api/v1/health` with 5 RPS for 60 s → zero errors, WAF does not block (below rate limit). Add this script in Phase 4 if it does not already exist.
11. Run a burst of 2100 requests in 5 min from one IP → WAF blocks with 403 + `X-Amzn-WAF-...` header.
12. `make design-lint` → passes. Introduce a hex violation → fails. Revert → passes.
13. Navigate every page with only the keyboard → no dead ends, focus rings visible, Lighthouse accessibility ≥ 95.
14. On GitHub, confirm the `v1.0.0` Release is marked "Latest" and has the Lambda zip, Terraform modules tarball, Docker image reference, and PyPI wheel attached. Confirm earlier `v1.0.0-rc.*` releases are still listed as **pre-releases**. Confirm the Draft release for the next version is auto-populating from merged PRs.

If every step passes, the plan is fully delivered.

---

## 18. Open questions for the user

1. **Staging account**: is there a separate AWS account for staging, or do we carve a `staging` namespace inside the production account? (Affects Terraform `environments/` layout.)
2. **WAF geo filter**: do we want to allow only US+Canada, or global? (I'll default to global unless told otherwise.)
3. **Custom domain**: is there a zone we should reserve (`app.example.com`) or is Phase 5 pure optionality for fork operators?
4. **SNS alert destination**: email? PagerDuty? Slack via EventBridge? (Defaults to `null` — operator wires it up.)
5. **Container-image fallback threshold**: are we OK switching to a container image if the unzipped Lambda artifact approaches 240 MB or native dependency packaging becomes unreliable? A zipped artifact over 50 MB is not itself a blocker because the pipeline deploys through S3. (My recommendation: stay zip until the 240 MB unzipped gate fails, then accept the container image.)
6. **Hosting destination confirmation**: are we OK committing to AWS-only for the default path, with Netlify documented purely as an escape hatch for pure-demo forks with no PHI exposure? (My recommendation: yes — see §1.1 for the full reasoning. If you want Netlify as a first-class path, we'd need to either (a) accept PHI cannot be processed ever, with prominent disclaimers, or (b) budget ~$1,500/mo for Netlify Enterprise.)

I'll default to the bracketed choices above if no answer lands before Phase 3 kickoff.
