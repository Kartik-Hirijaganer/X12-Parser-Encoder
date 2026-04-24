# ADR-001: Serverless API and Frontend Hosting

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-04-24 |
| **Source plan** | [serverless-terraform-architecture-restructure.md](serverless-terraform-architecture-restructure.md) |

## Context

The hosted application needs a stable public endpoint, same-origin browser-to-API traffic, low idle cost, and a service set that can be covered by an AWS Business Associate Addendum. The API is Python/FastAPI, the frontend is a static React bundle, and the runtime must process uploads in memory without adding a database, queue, or persistent file store.

## Decision

Use an AWS serverless stack:

- CloudFront as the single public endpoint.
- Private S3 for the SPA, accessed by CloudFront origin access control with SigV4.
- One Python 3.12 Lambda behind a Lambda Function URL for `/api/*`.
- A CloudFront-injected `X-Origin-Verify` header checked by FastAPI middleware for the Lambda origin.
- CloudWatch Logs plus Embedded Metric Format for Lambda metrics.
- Terraform as the source of truth for environments and modules.

## Seven Architecture Decisions

1. **Bundle the library into the Lambda zip.** Do not introduce a Lambda Layer for the single-function deployment. The `x12-edi-tools` wheel ships inside the function artifact unless package size or native dependency constraints force a container image.
2. **Use a CloudFront origin-secret header for Lambda Function URL access in v1.** CloudFront injects `X-Origin-Verify`; the FastAPI app rejects missing or mismatched secrets in Lambda mode. The Function URL uses `AuthType=NONE`; Lambda OAC and SigV4 are deferred because multipart browser uploads make payload hashing a poor fit.
3. **Remove process-local API rate limiting before Lambda cutover.** The in-memory limiter is invalid under Lambda concurrency. Use AWS WAF rate-based rules plus Lambda reserved concurrency as the enforcement boundary.
4. **Default to Lambda Function URLs, with API Gateway as an operator swap path.** Terraform defaults `api_origin` to `function_url`. API Gateway remains a future module path for operators that need per-route auth or usage plans.
5. **Amend, not replace, the design-system feedback rule.** Toasts are allowed for transient success and low-urgency information. Actionable errors still require persistent banners or equivalent non-transient surfaces.
6. **Land prerelease support before the first release candidate.** Phase 0.5 makes `1.0.0-rc.N` versioning, release validation, and prerelease GitHub Releases work before any release-candidate tag.
7. **Build Lambda artifacts for the selected runtime architecture.** Default to `x86_64` for the first zip deployment. If operators choose `arm64`, the package builder must target an AL2023 Lambda-compatible arm64 environment.

## Netlify Rejection Rationale

You raised Netlify as a possible alternative. I considered it and am still recommending AWS, because the "cheap" constraint and the "deals with patient data" constraint collide on every non-AWS platform we'd realistically pick:

| Platform | BAA availability | Minimum cost with BAA | Python backend story | Same-origin with our SPA? |
|---|---|---|---|---|
| **AWS** (this plan) | Free, signed at account creation | ~$1-8/mo at demo scale | Lambda runs Python 3.12 natively | Yes - CloudFront is one origin |
| **Netlify** | Enterprise only | **~$1,500/mo+** | JS-only functions; Python means separate cloud anyway | No - SPA on Netlify, API elsewhere |
| **Vercel** | Enterprise only | **~$1,500/mo+** | Python runtime is beta / limited | No - same split |
| **Cloudflare Pages + Workers** | Enterprise | ~$200/mo | Python via Pyodide is preview, not prod | Possible via Workers, but Python story is thin |

Compliance basis for this call:
- [HHS OCR cloud computing guidance](https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html) - a cloud provider that creates, receives, maintains, or transmits ePHI is a Business Associate and requires a BAA.
- [AWS HIPAA Eligible Services](https://aws.amazon.com/compliance/hipaa-eligible-services-reference/) - every service in this plan (Lambda, CloudFront, S3, CloudWatch Logs, KMS, ACM, Route 53, WAF) is covered.
- [Netlify HIPAA announcement](https://www.netlify.com/blog/netlify-launches-a-hipaa-compliant-service-offering) - HIPAA offering is enterprise-only.

**The honest framing of this trade-off:**

- If the deployed instance **never** touches real PHI - i.e. it is a portfolio demo hosted under your name against synthetic fixtures and you will never put it in front of a real submitter - Netlify is fine, free, and the SPA deploys with `git push`. You would then host the API on AWS Lambda anyway (Python FastAPI has no first-class home on Netlify), so you end up with a two-cloud setup, a CORS configuration, and you still need the AWS BAA for the API. Net: you save nothing and add complexity.
- If the deployed instance **might** touch real PHI - i.e. a fork operator configures their real clearinghouse credentials, or you demo to a prospective customer and they upload a live 270 - every byte has to traverse a BAA-covered path. Netlify's free and Pro tiers explicitly disclaim PHI in their terms. Using Netlify here would be a compliance incident waiting for a screenshot.
- The repo's `CLAUDE.md` says "Treat all fixture data as synthetic only. Never add real patient data." That's the right policy for commits. It does not bind what a running deployed instance will receive from users pasting files into a drop zone. A hosting layer that forbids PHI is the wrong match for software that accepts 270/271/837 uploads.

**Decision.** AWS-first, via a single CloudFront distribution with S3 + Lambda origins. This is the only option that is both cheap (~$1-8/mo) and HIPAA-compatible (free BAA) at this scale. The **product requirement is a stable public endpoint**, not literally the `*.cloudfront.net` hostname - a custom domain on the same distribution satisfies the contract equally well and is promoted from "optional Phase 5" to "day-1 recommended" for operators who control a DNS zone.

**Escape hatch for pure-demo operators.** The SPA is a framework-agnostic static bundle - nothing in Phases 6-8 ties it to S3. An operator who (a) will never process real PHI and (b) wants zero AWS touch on the frontend can run `npm run build` and deploy `apps/web/dist` to Netlify/Vercel/Cloudflare Pages with a `netlify.toml` or `vercel.json`, set `VITE_API_BASE_URL` to the CloudFront API URL (`https://<distribution>/api/v1` or the custom-domain equivalent), and accept that CORS re-enters the picture. Do **not** point this path at the raw Lambda Function URL while origin-secret middleware is enabled; the browser cannot supply the CloudFront-only origin header. This path is documented in [alternative-spa-hosting.md](../runbooks/alternative-spa-hosting.md), but it is **not** the default path and it is **not supported for PHI workloads**.

**Why not full Cloudflare Pages + Workers.** Cloudflare is the only non-AWS option with a reasonable BAA price. But Workers is V8-only; Python via Pyodide cold-starts at 200+ MB of WASM and is marked preview. Migrating `x12-edi-tools` to run under Pyodide would take weeks and the library would still fail for any dependency that isn't pure Python. Not worth the investment for a ~$150/mo saving that we don't need.

## Consequences

- Operators get one low-cost default deploy path with same-origin browser traffic.
- The raw Lambda Function URL remains internet reachable, but missing-origin-secret requests return cheap 403 responses before application work.
- Terraform state contains sensitive origin-secret material and must be protected accordingly.
- API Gateway remains available as a future swap path, but it is not part of the default stack.
- Alternate frontend hosts are documented only for no-PHI demo forks.
