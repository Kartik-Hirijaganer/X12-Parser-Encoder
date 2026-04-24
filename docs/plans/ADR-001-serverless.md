# ADR-001: Serverless API and Frontend Hosting

| | |
|---|---|
| **Status** | Draft |
| **Date** | 2026-04-24 |
| **Source plan** | [serverless-terraform-architecture-restructure.md](serverless-terraform-architecture-restructure.md) |

## Context

The current deployment runs the API on AWS App Runner behind a CloudFront and S3 single-page app. The serverless migration replaces App Runner with one Python Lambda Function URL behind the existing CloudFront distribution while keeping the SPA on private S3.

## Decisions

1. **Bundle the library into the Lambda zip.** Do not introduce a Lambda Layer for the single-function deployment. The `x12-edi-tools` wheel ships inside the function artifact unless package size or native dependency constraints force a container image.
2. **Use a CloudFront origin-secret header for Lambda Function URL access in v1.** CloudFront injects `X-Origin-Verify`; the FastAPI app rejects missing or mismatched secrets in Lambda mode. The Function URL uses `AuthType=NONE`; Lambda OAC and SigV4 are deferred because multipart browser uploads make payload hashing a poor fit.
3. **Remove process-local API rate limiting before Lambda cutover.** The in-memory limiter is invalid under Lambda concurrency. Use AWS WAF rate-based rules plus Lambda reserved concurrency as the enforcement boundary.
4. **Default to Lambda Function URLs, with API Gateway as an operator swap path.** Terraform defaults `api_origin` to `function_url`. API Gateway remains a future module path for operators that need per-route auth or usage plans.
5. **Amend, not replace, the design-system feedback rule.** Toasts are allowed for transient success and low-urgency information. Actionable errors still require persistent banners or equivalent non-transient surfaces.
6. **Land prerelease support before the first release candidate.** Phase 0.5 must make `1.0.0-rc.N` versioning, release validation, and prerelease GitHub Releases work before Phase 3 tags `v1.0.0-rc.1`.
7. **Build Lambda artifacts for the selected runtime architecture.** Default to `x86_64` for the first zip deployment. If operators choose `arm64`, the package builder must target an AL2023 Lambda-compatible arm64 environment.

## Consequences

The migration keeps one AWS-hosted, same-origin public endpoint, preserves a low-cost HIPAA-eligible service set, and gives Phase 1 and Phase 2 a shared contract for names and environment variables via `infra/shared/names.json`. Phase 9 will formalize this ADR with the full hosting rationale and compliance links from the source plan.
