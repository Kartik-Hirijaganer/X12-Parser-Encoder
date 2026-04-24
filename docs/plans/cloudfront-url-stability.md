# CloudFront URL Stability — Production Plan

| | |
|---|---|
| **Status** | Draft, awaiting sign-off |
| **Owner** | Platform / Deploy |
| **Scope** | `scripts/deploy_aws.sh`, `.github/workflows/deploy.yml`, operator documentation |
| **Audience** | Maintainers of this repository and downstream open-source operators forking it for their own AWS accounts |
| **Risk class** | Production-facing (frontend URL users depend on), non-reversible actions (CloudFront distribution creation/deletion) |

---

## 1. Executive Summary

The current AWS deploy path can silently create a new CloudFront distribution on any run, which changes the user-facing `*.cloudfront.net` hostname, orphans the previous distribution, and breaks browser CORS against the legacy managed container service API. The root cause is a fragile origin-string lookup paired with a timestamp-based CloudFront `CallerReference`, so any lookup miss becomes a brand-new distribution instead of a hard failure. This plan (a) fixes the defect in the shell script and workflow (Phases 2–3, the minimum viable fix), (b) migrates provisioning to **Terraform** so the infrastructure becomes declarative, reviewable, and portable for downstream open-source operators (Phase 4), and (c) then applies production-grade security controls and a stable custom domain through Terraform changes rather than ad-hoc CLI calls (Phases 5–6). CloudFormation and CDK are explicitly rejected on open-source vendor-lock-in grounds (§8). The work is sequenced in seven phases with explicit rollback per phase; Phase 2 ships first and stops the bleeding within a day.

---

## 2. Problem Statement

The deployed frontend is expected to live at a stable hostname across releases. A normal deploy should:

1. Build and push the API image to ECR.
2. Update legacy managed container service.
3. Sync the built SPA to S3.
4. Invalidate the existing CloudFront distribution.

It must **not** allocate a new `*.cloudfront.net` distribution domain. In practice, operators observe that the printed `Frontend (CloudFront)` URL changes after deployments, old distributions remain enabled, and downstream consumers (bookmarks, shared links, CORS allowlists) break.

### 2.1 Product policy — the pinned CloudFront URL is a user-visible contract

Until a custom domain ships (Phase 5), the user-facing URL **is** the CloudFront default domain (`https://<distribution-id>.cloudfront.net`). This is an explicit, current-phase product commitment, not an implementation detail:

- The README publishes this URL. End-user bookmarks point at it.
- legacy managed container service's CORS allowlist is pinned to it. Any drift breaks browser API calls.
- Any change to the distribution id is a breaking change to the product's public interface.

Therefore, for the current phase, "the CloudFront distribution id does not change across deploys" is a **product requirement**, not an operational nicety. Phase 5 (custom domain) supersedes this pin by adding a stable hostname in front of the distribution, after which the raw CloudFront URL becomes implementation detail. Until then, this plan's Phase 2–3 are the load-bearing fix.

---

## 3. Root Cause Analysis

### 3.1 Primary defect: non-idempotent `CallerReference`

[scripts/deploy_aws.sh:212](../../scripts/deploy_aws.sh#L212):

```bash
"CallerReference": "${APP_NAME}-$(date +%s)"
```

`CallerReference` is CloudFront's idempotency token: two `CreateDistribution` calls with the same value cannot both succeed. By embedding a wall-clock timestamp, the script guarantees a unique token per invocation, which means **any time the reuse lookup misses for any reason, a duplicate distribution is created silently** instead of being rejected. A stable `CallerReference` (e.g. `${APP_NAME}-${APP_ENV}-${AWS_ACCOUNT_ID}-${AWS_REGION}`) would turn the second attempt into a hard, actionable failure.

### 3.2 Brittle reuse lookup

`ensure_cloudfront_distribution` in [scripts/deploy_aws.sh:188-207](../../scripts/deploy_aws.sh#L188-L207) discovers the existing distribution by exact origin hostname:

```bash
aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?DomainName=='${S3_WEBSITE_HOST}']].Id | [0]" \
  --output text
```

This lookup can miss under realistic, non-malicious conditions:

1. `AWS_REGION`, `AWS_ACCOUNT_ID`, `APP_NAME`, or `S3_BUCKET` changed between deploys (see `vars.S3_BUCKET` in [.github/workflows/deploy.yml:28](../../.github/workflows/deploy.yml#L28), which has no default — sometimes set, sometimes not).
2. The distribution was manually edited to use a different S3 endpoint (e.g. migrated to Origin Access Control against the S3 REST endpoint `bucket.s3.${REGION}.amazonaws.com`).
3. Two deployments run concurrently before either sees the newly created distribution.
4. CloudFront read-after-write consistency lags right after creation.
5. Multiple matching or partially matching distributions exist and `| [0]` picks an arbitrary one.

### 3.3 No authoritative state

There is no external store for the canonical distribution id — no SSM Parameter, no resource tag discriminator, no Terraform state, no CloudFormation stack. The S3 bucket name plus origin-hostname string is treated as state, and it is not a reliable resource identity boundary for CloudFront.

### 3.4 No concurrency control

[.github/workflows/deploy.yml](../../.github/workflows/deploy.yml) has no `concurrency:` group. Two overlapping runs (two fast commits to `main`, or a `push` plus a manual `workflow_dispatch`) both observe "no existing distribution" and both call `CreateDistribution`. Whichever writes last wins; the other distribution is orphaned.

### 3.5 No Infrastructure-as-Code

All provisioning is imperative bash. Every deploy re-derives state from scratch. This is acceptable for a small tool but is the structural reason the class-of-bug exists.

### 3.6 Observed evidence

Live account inspection at the time of writing showed a distribution with comment `x12-parser-encoder web` whose origin is:

```
x12-parser-encoder-web-162599956892-us-east-1.s3-website.us-east-1.amazonaws.com
```

The repository defaults are `AWS_ACCOUNT_ID=306980977180` and `AWS_REGION=us-east-2`. That account/region drift is not proof of a specific production incident, but it is the exact failure mode the origin-based lookup produces: a distribution exists, and the next deploy cannot find it because some input changed.

### 3.7 The `CLOUDFRONT_*` variables are clobbered at script init

[scripts/deploy_aws.sh:26-28](../../scripts/deploy_aws.sh#L26-L28):

```bash
CLOUDFRONT_DISTRIBUTION_ID=""
CLOUDFRONT_DOMAIN=""
CLOUDFRONT_URL=""
```

These are unconditional assignments at the top of the script. Even if an operator (or CI) exports `CLOUDFRONT_DISTRIBUTION_ID=E123...`, it is overwritten to the empty string before `ensure_cloudfront_distribution` runs. This is a distinct bug from §3.1–§3.2: even a perfectly operable reuse-lookup strategy cannot work today, because the variable carrying the operator's intent is discarded. The fix is a one-line change per variable: `VAR="${VAR:-}"`.

Compounding this, [Makefile:103-111](../../Makefile#L103-L111) (`deploy` target) does not forward `CLOUDFRONT_DISTRIBUTION_ID` into the script's environment at all. So `make deploy` cannot pin the distribution even after §3.7 is fixed, unless the Makefile is also updated.

### 3.8 Observed invocation pattern — local operator runs are the likely churn source

[.github/workflows/deploy.yml:62-66](../../.github/workflows/deploy.yml#L62-L66) contains a "Skip AWS deploy when credentials are missing" step:

```yaml
- name: Skip AWS deploy when credentials are missing
  if: ${{ env.AWS_ROLE_TO_ASSUME == '' && (env.AWS_ACCESS_KEY_ID == '' || env.AWS_STATIC_PRIVATE_KEY == '') }}
  run: |
    echo "::notice::AWS deployment skipped because no Actions AWS credentials are configured."
```

If neither an OIDC role nor access keys are configured in the repository's Actions secrets/vars, every CI "Deploy" run is a no-op that still reports success. Evidence from recent workflow runs suggests many CI Deploys have been taking this branch.

This means the observed URL churn almost certainly originates from **operator-local** invocations of `scripts/deploy_aws.sh` or `make deploy` — not from CI. That fact drives two design decisions in this plan:

1. The guardrails (§3.1 idempotent CallerReference, §3.2 discovery strictness, §9 Phase 2 bootstrap gate) must be enforced **inside the script**, not in the workflow. A workflow-only fix leaves the local path broken.
2. The Makefile `deploy` target must forward the new variables (`APP_ENV`, `CLOUDFRONT_DISTRIBUTION_ID`, `CLOUDFRONT_ALLOW_CREATE`) so operators using `make deploy` inherit the same guarantees.

A secondary cleanup: the CI skip-step should emit a **warning annotation** (not a notice) and the job summary should make it obvious the deploy was a no-op. Today it is easy to miss.

---

## 4. Impact

| Area | Failure mode |
|---|---|
| End users | Printed frontend URL changes; bookmarks and shared links break. |
| CORS | legacy managed container service's `X12_API_CORS_ALLOWED_ORIGINS` is generated from the *current* `CLOUDFRONT_URL`; users still visiting the previous URL get CORS-blocked API calls. |
| Cache invalidation | Invalidation targets only the current deploy's distribution; duplicates keep serving stale assets until disabled. |
| Cost | Orphaned distributions continue to bill for data transfer and requests. |
| Operations | Duplicate cleanup is slow (disable → wait ~15 min → delete), destructive, and easy to get wrong. |
| Security | An unowned distribution is a surface that can drift in configuration over time; response-headers and TLS policy are not uniformly applied. |
| OSS operators | Any fork of this project that runs the deploy script inherits the same footgun. |

---

## 5. Goals and Non-Goals

### Goals

1. Two consecutive deploys targeting the same environment print the same CloudFront distribution id and domain.
2. A missing, drifted, or ambiguous distribution fails the deploy with an actionable error — never silently creates a new one.
3. Distribution creation is an explicit, gated bootstrap operation invoked at most once per environment.
4. State that identifies the canonical distribution lives in a durable, auditable store, not in the shell script.
5. The deploy workflow cannot race itself.
6. OSS operators forking the repo can bootstrap a new environment in their own AWS account via a documented procedure, without editing the script.
7. Security posture is explicit: bucket privacy, HTTPS policy, response headers, and IAM scope are documented and enforced in configuration.

### Non-Goals (in this plan)

1. Adopting CloudFormation or CDK. Both are rejected in §8 on open-source vendor-lock-in grounds. **Terraform is the sanctioned IaC path and is a full phase of this plan (§9 Phase 4), not a future concern.**
2. Multi-region active/active frontend. Not required for the URL-stability problem.
3. Introducing a database or server-side state for the app itself. The `CLAUDE.md` statelessness invariant stands.
4. **Replacing legacy managed container service with a portable compute layer.** legacy managed container service is AWS-proprietary, which conflicts with the OSS lock-in principle that motivates the Terraform decision. A full portable story would require moving the API to something like ECS Fargate behind an ALB, EKS, or a generic OCI-compatible runtime (Fly, Render, a self-hosted Kubernetes cluster). That is a significant architectural change — different IAM trust model, different scaling characteristics, different networking, different health-check semantics — and it is **out of scope for this plan** because this plan is specifically about making the CloudFront URL stable and the deploy idempotent. Once Terraform owns the control plane (Phase 4), the legacy managed container service module becomes a swappable unit: a follow-up plan can replace it with `aws_ecs_service` + `aws_lb` or a non-AWS provider without touching the CloudFront, S3, or SSM modules. That portability path is the answer to the lock-in concern; it is tracked as a follow-up initiative, not deferred indefinitely.

---

## 6. Design Principles

1. **Idempotent by construction.** Retrying a deploy must be safe. Stable `CallerReference`, explicit id lookup, hard failure on ambiguity.
2. **Explicit over implicit.** Creation is a bootstrap flag, never a silent fallback. Every resource the script may create or mutate is logged before the action.
3. **Cattle-not-pets, but identify the pet.** In Phase 2–3 the canonical distribution id lives in SSM Parameter Store and is mirrored in a GitHub Actions variable; every run asserts they agree. In Phase 4 Terraform state becomes the authoritative record and SSM is downgraded to a read-only mirror for the deploy script's data-plane steps.
4. **Least privilege.** The deploy role gets only the IAM it needs, scoped to the environment's resources. No `cloudfront:*` wildcards in production.
5. **Ops-legible failure.** Any deploy that cannot locate its canonical distribution prints the four inputs that identify the environment (`APP_NAME`, `APP_ENV`, `AWS_ACCOUNT_ID`, `AWS_REGION`) and the exact follow-up command an operator should run.
6. **OSS-friendly defaults.** A fresh fork with no configuration must produce a sensible, safe bootstrap path — not an accidental production resource.
7. **Minimize vendor lock-in in tooling.** Infrastructure is described in Terraform (open-source HCL, cross-cloud providers), not CloudFormation or CDK (AWS-proprietary output). Runtime dependencies on proprietary AWS services are isolated into swappable Terraform modules so that a future portability plan (see non-goal §5.4) can substitute them without rewriting the whole stack.

---

## 7. Design

### 7.1 Environment identity

Every deployment is keyed on `(APP_NAME, APP_ENV, AWS_ACCOUNT_ID, AWS_REGION)`. `APP_ENV` is new: it distinguishes `production` from `staging` or a fork's own namespace. Default: `production`.

The environment identity drives three derived names:

- S3 bucket: `${APP_NAME}-${APP_ENV}-web-${AWS_ACCOUNT_ID}-${AWS_REGION}`
- legacy managed container service service: `${APP_NAME}-${APP_ENV}-api`
- SSM parameter namespace: `/${APP_NAME}/${APP_ENV}/...`

`production` is the only environment whose bucket name keeps the legacy form (`${APP_NAME}-web-${AWS_ACCOUNT_ID}-${AWS_REGION}`, no `${APP_ENV}` segment) to avoid mass-renaming existing resources. All other environments include `${APP_ENV}`.

### 7.2 Distribution identity

Three pieces of identity, written on creation, checked on every run:

1. **SSM Parameter Store** (authoritative):
   `/${APP_NAME}/${APP_ENV}/cloudfront/distribution-id` (String, tier Standard).
2. **GitHub Actions variable** (convenience, matches SSM):
   `vars.CLOUDFRONT_DISTRIBUTION_ID` per environment.
3. **CloudFront resource tags** (self-describing, recoverable if 1 and 2 are lost):
   - `Application = ${APP_NAME}`
   - `Environment = ${APP_ENV}`
   - `ManagedBy   = deploy_aws.sh`

Creation uses a stable `CallerReference`:

```
${APP_NAME}-${APP_ENV}-${AWS_ACCOUNT_ID}-${AWS_REGION}
```

A second `CreateDistribution` call with the same `CallerReference` is rejected by CloudFront as a duplicate; that rejection is the safety net.

### 7.3 Discovery order

On every deploy, in order:

1. If `CLOUDFRONT_DISTRIBUTION_ID` is set in the environment (from GitHub Actions vars):
   `aws cloudfront get-distribution --id "$CLOUDFRONT_DISTRIBUTION_ID"`.
   Validate that the distribution exists, its tags match `(Application, Environment)`, and its origin resolves to an S3 endpoint for the expected bucket (either `${BUCKET}.s3-website.${REGION}.amazonaws.com` or `${BUCKET}.s3.${REGION}.amazonaws.com`, depending on OAC migration state).
   On success, set `CLOUDFRONT_DOMAIN` and return.
   On mismatch, **fail** with a clear error pointing at the drifted field.
2. Read SSM `/${APP_NAME}/${APP_ENV}/cloudfront/distribution-id`.
   Validate as in step 1.
   On success, also warn if `vars.CLOUDFRONT_DISTRIBUTION_ID` is unset and print the exact GitHub `gh variable set` command.
3. Tag-scoped discovery: `aws resourcegroupstaggingapi get-resources --resource-type-filters cloudfront:distribution --tag-filters Key=Application,Values=${APP_NAME} Key=Environment,Values=${APP_ENV}`.
   Expect exactly one result. Zero → proceed to step 4. More than one → **fail**, require operator to pick.
4. Legacy comment+origin fallback (only during migration window; remove after 30 days):
   match on `Comment == "${APP_NAME} web"` **and** origin DomainName in `(${S3_WEBSITE_HOST}, ${S3_REST_HOST})`.
   Exactly one → adopt it (write SSM, add tags, print a follow-up instruction to set `vars.CLOUDFRONT_DISTRIBUTION_ID`).
   Anything else → **fail**.
5. If all four steps miss: refuse to proceed unless `CLOUDFRONT_ALLOW_CREATE=true` is explicitly set.

### 7.4 Creation, gated

Creation only fires when `CLOUDFRONT_ALLOW_CREATE=true`. This environment variable must be set explicitly — never defaulted in CI — and is intended to be used exactly once per environment, from a human operator's workstation or a dedicated `bootstrap` workflow.

On creation, use `create-distribution-with-tags` so tags are applied atomically:

```bash
aws cloudfront create-distribution-with-tags \
  --distribution-config-with-tags file://"${TEMP_DIR}/cloudfront-config-with-tags.json"
```

Immediately after a successful creation, write SSM. Print the exact `gh variable set CLOUDFRONT_DISTRIBUTION_ID --env "${APP_ENV}" --body "${DISTRIBUTION_ID}"` command so the operator completes the handshake.

### 7.5 Concurrency control

Add to [.github/workflows/deploy.yml](../../.github/workflows/deploy.yml):

```yaml
concurrency:
  group: deploy-${{ vars.APP_ENV || 'production' }}
  cancel-in-progress: false
```

`cancel-in-progress: false` is correct for production: an in-flight deploy must finish cleanly, not be cut off halfway through legacy managed container service's 10-minute rollout.

### 7.6 Preflight contract

Before any mutation, print and assert:

```
AWS account       : <sts account>   (expected ${AWS_ACCOUNT_ID})
AWS region        : <region>
Application       : ${APP_NAME}
Environment       : ${APP_ENV}
S3 bucket         : ${S3_BUCKET}
S3 website origin : ${S3_WEBSITE_HOST}
CloudFront id     : <id or unset>
Allow create      : <true|false>
```

`assert_aws_account` is extended to also print the *actual* vs *expected* account id on failure (currently it only exits 1).

**No credential material in output.** The preflight must never print `AWS_ACCESS_KEY_ID`, the AWS static secret key, `AWS_SESSION_TOKEN`, `AWS_ROLE_TO_ASSUME`, or any other secret. `set -x` is forbidden in this script. The tag-list and distribution-config files written to `${TEMP_DIR}` are cleaned up via the existing `trap` and must not be echoed to logs.

### 7.7 CORS stability

The legacy managed container service `X12_API_CORS_ALLOWED_ORIGINS` list must remain stable across deploys so users on older cached SPAs can still call the API. The list is composed from:

1. The production CloudFront domain (always).
2. The S3 website URL (internal/debug only, behind a flag in production).
3. The custom domain, once §Phase 5 lands.
4. `EXTRA_CORS_ALLOWED_ORIGINS` (operator-set).

Once Phase 5 ships the custom domain, the S3 website URL is removed from the allowlist by default.

### 7.8 Multi-environment support (for OSS operators)

A downstream operator running this project in their own AWS account sets:

```
APP_ENV=production            # or staging, preview, dev, etc.
AWS_ACCOUNT_ID=<their id>
AWS_REGION=<their region>
APP_NAME=x12-parser-encoder   # or their fork's name
```

All resource names, SSM paths, and GitHub variable names are keyed off `(APP_NAME, APP_ENV)`. Two environments in the same account do not collide.

### 7.9 Security baseline (Phase 5, implemented in Terraform)

Implemented as Terraform module changes in Phase 5 (after the import in Phase 4). Applying these in the Terraform module gives us plan/preview, diff-review, and revert-via-git that a shell-script approach does not.

- **Origin Access Control (OAC)** replacing the public S3 website origin. Bucket becomes private; CloudFront signs requests with SigV4 to the S3 REST endpoint. `BlockPublicAcls=true`, `BlockPublicPolicy=true`, `RestrictPublicBuckets=true`. Terraform resources: `aws_cloudfront_origin_access_control`, `aws_s3_bucket_public_access_block`, updated `aws_s3_bucket_policy`.
- **Response Headers Policy**: `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and a CSP matching the SPA's actual asset origins (self + `https://${API_HOST}`). Terraform resource: `aws_cloudfront_response_headers_policy`.
- **Minimum TLS**: `TLSv1.2_2021` for viewer connections.
- **Viewer protocol policy**: `redirect-to-https` (already set).
- **Logging**: standard logs to a dedicated S3 bucket `${APP_NAME}-${APP_ENV}-cflogs-${AWS_ACCOUNT_ID}-${AWS_REGION}` with 90-day lifecycle via `aws_s3_bucket_lifecycle_configuration`.
- **WAFv2 Web ACL** (AWS Managed Rules: CommonRuleSet, KnownBadInputs, AnonymousIpList) in `us-east-1`, attached to the distribution. Rate-limit rule: 2000 req / 5 min per source IP. Terraform resources: `aws_wafv2_web_acl` (with `aws.us_east_1` provider alias), `aws_wafv2_web_acl_association` is not applicable to CloudFront; instead set `web_acl_id` on the distribution.

### 7.10 Custom domain (Phase 6, implemented in Terraform)

A stable public hostname is the only way to guarantee the URL never changes from a user's perspective. Requirements:

- ACM cert in `us-east-1` (CloudFront requires `us-east-1`). Terraform: `aws_acm_certificate` with `aws.us_east_1` provider, `aws_acm_certificate_validation`, Route 53 validation records.
- DNS: Route 53 alias record pointing at the distribution; a `var.dns_provider = "external"` branch emits the CNAME target as a Terraform output for operators using Cloudflare, Fastly DNS, or another provider.
- Add the custom hostname to the distribution's `Aliases`.
- Add the custom hostname to legacy managed container service CORS (Terraform variable threaded through to the legacy managed container service module's `RuntimeEnvironmentVariables`).
- Stop publishing raw CloudFront URLs as user-facing. README and any generated docs switch to the custom hostname.

### 7.11 Terraform architecture (Phase 4)

This subsection specifies the Terraform layout. All paths are repository-relative.

```
infra/
  terraform/
    README.md                    # operator-facing docs: bootstrap, plan, apply, rollback
    versions.tf                  # terraform >= 1.6; aws ~> 5.40 pinned
    providers.tf                 # default aws provider + aliased us_east_1 provider for CF/ACM/WAF
    backend.tf                   # S3 backend, key filled per env via -backend-config
    variables.tf                 # app_name, app_env, aws_account_id, aws_region, api_image_tag, ...
    locals.tf                    # derived names (bucket, service, caller_reference, tags)
    outputs.tf                   # distribution_id, distribution_domain, bucket_name, api_url, ecr_repo_url
    main.tf                      # module composition
    modules/
      s3_web/                    # web assets bucket, policy, encryption, public-access-block
      ecr/                       # API image repo
      iam/                       # legacy managed container service ECR access role, deploy role (optional, chicken/egg — see below)
      app_runner/                # service, instance configuration, env vars
      cloudfront/                # distribution, OAC (Phase 5), response headers policy (Phase 5)
      ssm/                       # /${APP_NAME}/${APP_ENV}/cloudfront/distribution-id mirror
      waf/                       # Phase 5 — WAFv2 WebACL in us-east-1
      logging/                   # Phase 5 — CloudFront logs bucket + lifecycle
      custom_domain/             # Phase 6 — ACM cert in us-east-1, Route 53 or external DNS
    environments/
      production/
        backend.hcl              # bucket, key, region, dynamodb_table for state
        terraform.tfvars         # account id, region, app_env=production, api_image_tag placeholder
      staging/
        backend.hcl
        terraform.tfvars
      example/                   # template for downstream OSS operators
        backend.hcl.example
        terraform.tfvars.example
```

**State backend.** S3 bucket `${APP_NAME}-tfstate-${AWS_ACCOUNT_ID}-${AWS_REGION}` (versioned, encrypted, private) with DynamoDB lock table `${APP_NAME}-tflocks` (PAY_PER_REQUEST, hash key `LockID`). These two resources are bootstrapped out-of-band by a short `scripts/bootstrap_tf_backend.sh` that creates them via the AWS CLI before `terraform init`. This is the one concession to the state-backend chicken-and-egg problem; it runs once per account and is documented in the README.

**Per-environment state isolation.** Each environment has its own `backend.hcl` with a distinct `key` (e.g. `production/terraform.tfstate`), so no workspaces are needed. Simpler for OSS forks to reason about.

**Provider pinning.** `terraform { required_version = ">= 1.6" }` and `aws = { version = "~> 5.40" }`. Updates are explicit PRs. No `> 0` floats.

**Variables (root module).**

| Variable | Type | Default | Notes |
|---|---|---|---|
| `app_name` | string | `x12-parser-encoder` | Namespace. |
| `app_env` | string | — | `production`, `staging`, etc. Required. |
| `aws_account_id` | string | — | Asserted vs caller identity in a `check` block. |
| `aws_region` | string | `us-east-2` | Default AWS provider region. |
| `api_image_tag` | string | — | Current ECR image tag. Threaded into legacy managed container service. Changes on every deploy. |
| `extra_cors_allowed_origins` | list(string) | `[]` | Appended to the legacy managed container service CORS allowlist. |
| `custom_domain` | string | `null` | Phase 6. If set, adds to distribution `Aliases`, provisions ACM cert, updates CORS. |
| `enable_waf` | bool | `false` | Phase 5 gate. |
| `enable_oac` | bool | `false` | Phase 5 gate for OAC migration. Defaults `false` so the initial import matches today's website-origin config exactly. |

**Outputs.** `distribution_id`, `distribution_domain`, `bucket_name`, `ecr_repository_url`, `app_runner_service_url`, `api_base_url`. The deploy script reads these via `terraform output -raw`.

**Import strategy (Phase 4).** Existing resources are adopted, not recreated. Order, leaves first:

```bash
cd infra/terraform/environments/production
terraform init -backend-config=backend.hcl

terraform import module.s3_web.aws_s3_bucket.web \
  x12-parser-encoder-web-306980977180-us-east-2
terraform import module.ecr.aws_ecr_repository.api \
  x12-parser-encoder-api
terraform import module.iam.aws_iam_role.apprunner_ecr_access \
  x12-parser-encoder-apprunner-ecr-access
terraform import module.app_runner.aws_apprunner_service.api \
  arn:aws:apprunner:us-east-2:306980977180:service/x12-parser-encoder-api/<uuid>
terraform import module.cloudfront.aws_cloudfront_distribution.web \
  <CANONICAL_DISTRIBUTION_ID>
terraform import module.ssm.aws_ssm_parameter.distribution_id \
  /x12-parser-encoder/production/cloudfront/distribution-id

terraform plan
# Expected: zero changes, or only additive tagging/tracking.
# Any non-trivial diff must be reconciled by editing the module (not the resource)
# before apply.
```

The `terraform plan` gate is strict: the first apply must be a no-op or a diff that the operator has reviewed and knowingly accepts. Anything else means the module's default arguments drifted from the live resource — fix the module.

**Deploy script, after Phase 4.** [scripts/deploy_aws.sh](../../scripts/deploy_aws.sh) shrinks from ~460 lines to roughly 150, split into two concerns:

1. *Data plane* (stays in script): docker build, docker push, `aws s3 sync`, `aws cloudfront create-invalidation`.
2. *Control plane* (delegated to Terraform): every `ensure_*` function is deleted. The script calls `terraform apply -var "api_image_tag=${API_IMAGE_TAG}" -auto-approve` and then reads outputs:
   ```bash
   DISTRIBUTION_ID="$(terraform output -raw distribution_id)"
   API_BASE_URL="$(terraform output -raw api_base_url)"
   ```

Terraform state becomes authoritative. SSM is downgraded to a read-through mirror that the script can consult when Terraform is unavailable (e.g. during an incident). The three discovery paths in §7.3 are retained but become a defense-in-depth layer, not the primary resolution.

**CI integration.**

A new workflow `.github/workflows/terraform.yml`:

- `terraform fmt -check`, `terraform validate`, `tflint`, and `tfsec` (or `checkov`) run on every PR.
- `terraform plan` runs on PR and posts the plan output as a PR comment.
- `terraform apply` runs on push to `main` with the plan artifact from the PR, gated behind a protected `production` environment that requires human approval.
- The existing `deploy.yml` is modified to `terraform apply -refresh-only` as a sanity check before starting the data-plane steps.

**State security.**

- State bucket: private, SSE-S3 or SSE-KMS, versioning on, access logging to a separate bucket, MFA-delete optional.
- Lock table: minimal IAM, scoped to the deploy role.
- IAM: developers can `terraform plan` (read state, describe resources) but not `apply` without assuming the deploy role. Plans run in CI under an OIDC-assumed read-only role.

**Drift detection.**

A weekly cron workflow `terraform plan` in each environment; non-zero diff opens a GitHub issue tagged `infra-drift`. This directly answers open question §17.3.

**Portable-compute follow-on.** Because the legacy managed container service service lives behind `modules/app_runner/`, a future plan can add `modules/app_runner_ecs/` with the same inputs and outputs, and swap the reference in `main.tf`. The CloudFront, S3, and SSM modules are unaffected. This is how Phase 4 opens the door to addressing the non-goal in §5.4 without pre-committing to it.

---

## 8. Alternatives Considered

The IaC-tool choice is a core decision for an open-source product that third parties will deploy into their own clouds. The table below records the trade-off explicitly.

| Option | Verdict | Rationale |
|---|---|---|
| **Terraform** (chosen, Phase 4) | **Accepted** | Open-source, HCL is simple and widely taught, has a cross-cloud provider ecosystem, and does not force downstream operators to adopt an AWS-proprietary tool. Mature import/state tooling (`terraform import`, `terraform state mv`) lets us adopt existing resources without downtime. State lives in S3+DynamoDB (standard pattern) but can be moved to any S3-compatible object store or Terraform Cloud if an operator prefers. Modules are reusable outside this project. |
| **CloudFormation (incl. SAM)** | **Rejected** | AWS-proprietary by definition. Forces every fork operator to learn AWS-specific IaC even if they already have Terraform or Pulumi workflows. Weaker community/module ecosystem than Terraform. Error messages and drift-detection semantics are inferior. Rejecting CloudFormation is consistent with Design Principle §6.7 (minimize lock-in). |
| **AWS CDK (TypeScript)** | **Rejected** | CDK compiles to CloudFormation, so it inherits every lock-in problem above. Adds a TypeScript build step in the infra pipeline that downstream operators must understand in addition to AWS. The "shares a language with the frontend" argument is weaker than it looks because the infra codebase is small and the audiences are different (operators vs. frontend devs). |
| **Pulumi** | Rejected for this plan | Cross-cloud like Terraform, but has a smaller operator community, and the language-native model (TS/Python/Go) makes state review harder than HCL's declarative form. Not a bad tool; just not the best fit for an OSS project where the audience optimizes for readability and the widest-possible familiarity. |
| **Keep the imperative script as-is, just patch `CallerReference`** | Rejected | Closes the duplicate-creation hole but leaves brittle discovery, no concurrency control, no multi-env story, and no state record for forks. Insufficient for a product used by others. This is what Phase 2 alone would do — which is why Phase 2 is *not* the whole plan. |
| **Store state in a repo-checked-in JSON file** | Rejected | Conflates source with infra state; commits on every deploy; leaks account ids into git history; no record for downstream forks. Phase 2–3 use SSM; Phase 4 onward Terraform state is the primitive. |
| **Deferring IaC indefinitely** | Rejected | The reason this plan exists is that an imperative script has no authoritative state. Kicking IaC to "future work" would repeat the mistake. Phase 4 is a committed phase with a concrete timeline (§18). |

---

## 9. Implementation Phases

Each phase is independently shippable and independently reversible.

### Phase 1 — Containment (manual, before any code change)

Goal: capture the current canonical distribution id in SSM and in GitHub Actions variables so the Phase 2 script has something to find.

1. Inventory distributions in the current account:
   ```bash
   aws cloudfront list-distributions \
     --query "DistributionList.Items[?Comment=='x12-parser-encoder web'].{Id:Id,Domain:DomainName,Origin:Origins.Items[0].DomainName,Enabled:Enabled,Status:Status}" \
     --output table
   ```
2. Identify the distribution currently serving users (check DNS, deployed SPA, operator memory). Call its id `<CANONICAL_ID>`.
3. Write SSM:
   ```bash
   aws ssm put-parameter \
     --name "/x12-parser-encoder/production/cloudfront/distribution-id" \
     --value "<CANONICAL_ID>" \
     --type String --overwrite
   ```
4. Tag the distribution:
   ```bash
   aws cloudfront tag-resource \
     --resource "arn:aws:cloudfront::<ACCOUNT>:distribution/<CANONICAL_ID>" \
     --tags 'Items=[{Key=Application,Value=x12-parser-encoder},{Key=Environment,Value=production},{Key=ManagedBy,Value=deploy_aws.sh}]'
   ```
5. Set GitHub Actions variables on the `production` environment:
   ```bash
   gh variable set CLOUDFRONT_DISTRIBUTION_ID --env production --body "<CANONICAL_ID>"
   gh variable set APP_ENV --env production --body "production"
   gh variable set S3_BUCKET --env production --body "<current bucket>"
   ```
6. Do **not** delete duplicates yet. Phase 6 handles that after the fix is verified in production.

### Phase 2 — Script hardening (MVP fix)

Goal: make `scripts/deploy_aws.sh` refuse to create duplicate distributions.

Changes to [scripts/deploy_aws.sh](../../scripts/deploy_aws.sh):

- **Stop clobbering env-passed state (§3.7).** Replace the three unconditional initializations at [scripts/deploy_aws.sh:26-28](../../scripts/deploy_aws.sh#L26-L28) with the `${VAR:-}` form so values passed in by the environment, the workflow, or the Makefile survive into the discovery step:
  ```bash
  CLOUDFRONT_DISTRIBUTION_ID="${CLOUDFRONT_DISTRIBUTION_ID:-}"
  CLOUDFRONT_DOMAIN="${CLOUDFRONT_DOMAIN:-}"
  CLOUDFRONT_URL="${CLOUDFRONT_URL:-}"
  ```
  This is the single smallest change that unblocks everything else.
- Introduce `APP_ENV` (default `production`), and `CLOUDFRONT_ALLOW_CREATE` (default `false`).
- Derive `CLOUDFRONT_CALLER_REFERENCE = ${APP_NAME}-${APP_ENV}-${AWS_ACCOUNT_ID}-${AWS_REGION}`.
- Add helper: `resolve_cloudfront_distribution` — implements §7.3 discovery order.
- Refactor `ensure_cloudfront_distribution` to call `resolve_cloudfront_distribution` first; only call the creation path when `CLOUDFRONT_ALLOW_CREATE=true`.
- Switch creation to `create-distribution-with-tags`.
- On successful creation, write SSM and print the `gh variable set` handshake command.
- Extend `assert_aws_account` to print expected/actual on mismatch.
- Add preflight logging (§7.6), including the "no credentials in output" rule.

Changes to [Makefile](../../Makefile#L103-L111) (`deploy` target) — required because, per §3.8, `make deploy` is a primary operator-local entry point:

- Forward the new variables into the script's environment:
  ```makefile
  APP_ENV ?= production
  CLOUDFRONT_DISTRIBUTION_ID ?=
  CLOUDFRONT_ALLOW_CREATE ?= false

  deploy:
      AWS_REGION="$(AWS_REGION)" \
      AWS_ACCOUNT_ID="$(AWS_ACCOUNT_ID)" \
      APP_NAME="$(APP_NAME)" \
      APP_ENV="$(APP_ENV)" \
      S3_BUCKET="$(S3_BUCKET)" \
      ECR_REPOSITORY="$(ECR_REPOSITORY)" \
      APP_RUNNER_SERVICE="$(APP_RUNNER_SERVICE)" \
      APP_RUNNER_ECR_ACCESS_ROLE="$(APP_RUNNER_ECR_ACCESS_ROLE)" \
      CLOUDFRONT_DISTRIBUTION_ID="$(CLOUDFRONT_DISTRIBUTION_ID)" \
      CLOUDFRONT_ALLOW_CREATE="$(CLOUDFRONT_ALLOW_CREATE)" \
      bash scripts/deploy_aws.sh
  ```
- Add a separate `deploy-bootstrap` target that sets `CLOUDFRONT_ALLOW_CREATE=true` and prints a red-text warning before running. Operators invoke this **once per environment**, by hand, and never in CI.

Acceptance for Phase 2:
- Two consecutive deploys (either `make deploy` or CI) print the same distribution id.
- Running the script with a typo'd `AWS_ACCOUNT_ID` fails *before* any AWS mutation.
- Running with no SSM / no GH var / no tag match and `CLOUDFRONT_ALLOW_CREATE` unset fails with a single actionable error.
- An operator who exports `CLOUDFRONT_DISTRIBUTION_ID=E123` and runs `make deploy` successfully reuses that distribution. (Today, this silently fails because of the clobber bug.)

### Phase 3 — Workflow hardening

Changes to [.github/workflows/deploy.yml](../../.github/workflows/deploy.yml):

- Add the `concurrency` block (§7.5).
- Wire the new env vars through to the script step:
  ```yaml
  APP_ENV:                       ${{ vars.APP_ENV || 'production' }}
  CLOUDFRONT_DISTRIBUTION_ID:    ${{ vars.CLOUDFRONT_DISTRIBUTION_ID }}
  CLOUDFRONT_ALLOW_CREATE:       'false'
  ```
- Replace the unset `vars.S3_BUCKET` default with a required check: if `S3_BUCKET` resolves to empty after defaulting, fail the job before `bash scripts/deploy_aws.sh`.
- **Make the credentials-skip path loud (§3.8).** Change the "Skip AWS deploy when credentials are missing" step to emit `::warning::` instead of `::notice::`, and to write a conspicuous message into `$GITHUB_STEP_SUMMARY`. Today that step silently reports success; maintainers miss that production deploys have been no-ops for weeks.
- Add a separate manual workflow `deploy-bootstrap.yml`, restricted to a protected environment, that runs with `CLOUDFRONT_ALLOW_CREATE=true`. This is the only entry point that may create a distribution.

### Phase 4 — Terraform migration (§7.11)

Goal: make Terraform state the authoritative record for the web/frontend/API control plane, importing existing resources so there is no downtime and no URL change.

Sub-steps:

4a. **Bootstrap state backend.** Create `${APP_NAME}-tfstate-${AWS_ACCOUNT_ID}-${AWS_REGION}` S3 bucket (versioned, encrypted, private) and `${APP_NAME}-tflocks` DynamoDB table via `scripts/bootstrap_tf_backend.sh`. One-time, per account.
4b. **Author modules** under `infra/terraform/modules/` matching the live configuration verbatim (website-origin S3, no OAC, no WAF, no custom domain — those come in Phase 5/6).
4c. **Import existing resources** in the order in §7.11. Verify `terraform plan` shows zero changes.
4d. **Cut over the deploy script.** Replace `ensure_s3_bucket`, `ensure_ecr_repository`, `ensure_apprunner_access_role`, `ensure_cloudfront_distribution`, and the legacy managed container service create/update logic with a single `terraform apply -var "api_image_tag=${API_IMAGE_TAG}"` followed by reading outputs. The data-plane steps (`docker push`, `aws s3 sync`, `create-invalidation`) remain.
4e. **Wire CI.** Add `.github/workflows/terraform.yml` with `fmt`/`validate`/`tflint`/`tfsec`/`plan` on PR and human-approved `apply` on push. Update `deploy.yml` to depend on a successful Terraform apply.
4f. **Migrate state mirror.** Keep SSM `/${APP_NAME}/${APP_ENV}/cloudfront/distribution-id` as a read-through mirror written by Terraform, but operators are instructed to treat Terraform state as the source of truth.
4g. **Drift detection.** Schedule a weekly `terraform plan` job that files a GitHub issue on non-zero diff.

Acceptance for Phase 4:
- The first `terraform plan` after import shows zero destructive changes.
- `make deploy` runs end-to-end without invoking any `aws ec2|s3api|cloudfront create-*|apprunner create-*|ecr create-*|iam create-*` command — all creates/updates flow through Terraform.
- A follow-up `terraform plan` produces zero diff when nothing has changed.
- The CloudFront distribution id and domain remain identical to pre-import.
- Tearing down a fork's `staging` environment and re-creating it requires only `terraform apply` plus the image-push step, with no manual AWS CLI calls.

### Phase 5 — Security hardening (§7.9, implemented in Terraform)

Now done as Terraform module changes, not shell:

5a. `aws_cloudfront_response_headers_policy` referenced from the default cache behavior.
5b. Raise minimum TLS to `TLSv1.2_2021` via `viewer_certificate.minimum_protocol_version`.
5c. Create the CloudFront logs bucket and attach standard logging (`logging_config` on the distribution).
5d. Create WAFv2 Web ACL in `us-east-1`, set `web_acl_id` on the distribution.
5e. Flip `var.enable_oac = true`: Terraform creates `aws_cloudfront_origin_access_control`, repoints the origin to the S3 REST endpoint, updates the bucket policy for `cloudfront.amazonaws.com` with `aws:SourceArn`, re-blocks all public access, and removes the website config. Rollback: `var.enable_oac = false` and `terraform apply` within the 14-day window.

Each sub-step is a reviewable PR. 5e is the only one with real blast radius and is the last to ship.

### Phase 6 — Custom domain (§7.10, implemented in Terraform)

See §7.10. Set `var.custom_domain = "app.example.com"` and `var.dns_provider`; Terraform provisions ACM + DNS + alias. Purely additive; does not regress the `*.cloudfront.net` URL, which continues to work during migration.

### Phase 7 — Duplicate cleanup

Only after two successful production deploys on the Phase 4 (Terraform-owned) pipeline:

1. List duplicates via tags (`Application=x12-parser-encoder`, `Environment=production`) minus the canonical id.
2. Confirm no DNS record or user-shared link points at any duplicate (grep the repo, check Route 53, ask in the team channel, wait 7 days).
3. Duplicates are **not** under Terraform management by design, so they are deleted via the AWS CLI runbook in §14.3: `update-distribution` with `Enabled: false`, wait for `Deployed` status, `delete-distribution` with the current `ETag`.
4. Also remove any orphaned S3 buckets that match the abandoned origin names, after confirming they are empty.

Runbook in §14.3.

---

## 10. IAM Requirements

The deploy role (OIDC-assumed via `aws-actions/configure-aws-credentials@v4`) needs the following scoped permissions. Resource ARNs should be restricted to the app's environment prefix wherever possible.

```text
Statement 1 — S3 (app's web bucket and CF logs bucket only)
  s3:CreateBucket, s3:PutBucketEncryption, s3:PutBucketPolicy,
  s3:PutBucketWebsite, s3:PutPublicAccessBlock, s3:GetBucketPolicy,
  s3:ListBucket, s3:PutObject, s3:DeleteObject, s3:GetObject
  Resource: arn:aws:s3:::${APP_NAME}-${APP_ENV}-web-*,
            arn:aws:s3:::${APP_NAME}-${APP_ENV}-web-*/*,
            arn:aws:s3:::${APP_NAME}-${APP_ENV}-cflogs-*,
            arn:aws:s3:::${APP_NAME}-${APP_ENV}-cflogs-*/*

Statement 2 — ECR
  ecr:DescribeRepositories, ecr:CreateRepository,
  ecr:GetAuthorizationToken, ecr:BatchCheckLayerAvailability,
  ecr:InitiateLayerUpload, ecr:UploadLayerPart, ecr:CompleteLayerUpload,
  ecr:PutImage
  Resource: arn:aws:ecr:${REGION}:${ACCOUNT}:repository/${APP_NAME}-${APP_ENV}-api

Statement 3 — legacy managed container service
  apprunner:CreateService, apprunner:UpdateService,
  apprunner:DescribeService, apprunner:ListServices,
  iam:PassRole (scoped to the legacy managed container service ECR access role)
  Resource: arn:aws:apprunner:${REGION}:${ACCOUNT}:service/${APP_NAME}-${APP_ENV}-api/*

Statement 4 — CloudFront (distribution-scoped where possible)
  cloudfront:CreateDistributionWithTags, cloudfront:UpdateDistribution,
  cloudfront:GetDistribution, cloudfront:ListDistributions,
  cloudfront:ListTagsForResource, cloudfront:TagResource,
  cloudfront:CreateInvalidation
  Resource: *   (CloudFront does not support resource-level permissions for list/create)

Statement 5 — SSM
  ssm:GetParameter, ssm:PutParameter
  Resource: arn:aws:ssm:${REGION}:${ACCOUNT}:parameter/${APP_NAME}/${APP_ENV}/*

Statement 6 — STS (already implicit via OIDC)
  sts:GetCallerIdentity
  Resource: *

Statement 7 — IAM (bootstrap only, remove after first run)
  iam:GetRole, iam:CreateRole, iam:AttachRolePolicy
  Resource: arn:aws:iam::${ACCOUNT}:role/${APP_NAME}-apprunner-ecr-access

Statement 8 — Terraform state backend (Phase 4+)
  s3:GetObject, s3:PutObject, s3:DeleteObject, s3:ListBucket
  Resource: arn:aws:s3:::${APP_NAME}-tfstate-${ACCOUNT}-${REGION},
            arn:aws:s3:::${APP_NAME}-tfstate-${ACCOUNT}-${REGION}/*
  dynamodb:GetItem, dynamodb:PutItem, dynamodb:DeleteItem
  Resource: arn:aws:dynamodb:${REGION}:${ACCOUNT}:table/${APP_NAME}-tflocks

Statement 9 — WAFv2 (Phase 5, us-east-1)
  wafv2:CreateWebACL, wafv2:UpdateWebACL, wafv2:GetWebACL,
  wafv2:DeleteWebACL, wafv2:ListWebACLs, wafv2:TagResource
  Resource: arn:aws:wafv2:us-east-1:${ACCOUNT}:global/webacl/${APP_NAME}-${APP_ENV}/*

Statement 10 — ACM (Phase 6, us-east-1)
  acm:RequestCertificate, acm:DescribeCertificate, acm:DeleteCertificate,
  acm:ListCertificates, acm:AddTagsToCertificate
  Resource: arn:aws:acm:us-east-1:${ACCOUNT}:certificate/*

Statement 11 — Route 53 (Phase 6, if Route 53 is the DNS provider)
  route53:ChangeResourceRecordSets, route53:GetHostedZone,
  route53:ListResourceRecordSets, route53:GetChange
  Resource: arn:aws:route53:::hostedzone/${HOSTED_ZONE_ID}
```

The OIDC trust policy on the role must pin `token.actions.githubusercontent.com` as the federated provider and require:

- `token.actions.githubusercontent.com:sub = repo:<org>/<repo>:environment:production`
- `token.actions.githubusercontent.com:aud = sts.amazonaws.com`

Access keys (`AWS_ACCESS_KEY_ID` plus the matching static secret key) remain supported for operators who cannot use OIDC, but the README recommends OIDC as the default.

---

## 11. Observability

1. **CloudWatch alarms** (created out of band, not by the deploy script):
   - `5xxErrorRate` > 1% over 5 min on the distribution.
   - `OriginLatency` p95 > 2000 ms over 5 min.
   - `CacheHitRate` < 50% over 30 min (tuning signal, warning severity).
2. **Deploy log signal**: grep `scripts/deploy_aws.sh` output for the string `Creating CloudFront distribution`. Any occurrence after Phase 1 is complete is an incident.
3. **Cost guardrail**: a monthly AWS Budgets alarm at the account level catches orphaned distributions regardless of this plan.
4. **CloudFront standard logs** (Phase 4c) retained 90 days; operators responsible for ensuring logs contain no viewer PII per their own compliance regime.

---

## 12. Testing Strategy

### 12.1 Static

- `bash -n scripts/deploy_aws.sh` in CI.
- `shellcheck scripts/deploy_aws.sh` in CI with explicit allowlist for any warnings we accept.

### 12.2 Unit (stubbed AWS CLI)

Add `scripts/hooks/tests/test_deploy_aws.sh` (or equivalent bats file) that shims `aws` as a function returning canned JSON and asserts the script's branching:

1. `CLOUDFRONT_DISTRIBUTION_ID` set, distribution exists, tags match → reuse, no `create-distribution*` call.
2. `CLOUDFRONT_DISTRIBUTION_ID` set, distribution exists, tags don't match → exit non-zero, specific error message.
3. `CLOUDFRONT_DISTRIBUTION_ID` unset, SSM returns canonical id → reuse, print handshake hint.
4. All discovery misses, `CLOUDFRONT_ALLOW_CREATE` unset → exit non-zero, actionable error.
5. All discovery misses, `CLOUDFRONT_ALLOW_CREATE=true` → `create-distribution-with-tags` called exactly once; `put-parameter` called exactly once.
6. Two simulated concurrent runs with the same `CallerReference` → second run receives `DistributionAlreadyExists`, exits non-zero, does not retry.

### 12.3 Integration (optional)

LocalStack Community supports CloudFront in a limited form. An optional `make test-deploy-localstack` target that runs the script against LocalStack is nice-to-have but not required for Phase 2 sign-off.

### 12.4 Manual acceptance

On a dedicated `staging` environment in the maintainers' AWS account:

1. Phase 1 containment performed.
2. Run the hardened deploy twice back-to-back. Assert the printed `CloudFront distribution:` line is identical.
3. Run with a deliberately wrong `AWS_ACCOUNT_ID`. Assert fail-before-mutation.
4. Run with `CLOUDFRONT_DISTRIBUTION_ID` pointing at a distribution in a different account. Assert fail with tag-mismatch error.
5. Run the bootstrap workflow in a brand-new environment. Assert exactly one distribution is created, SSM is populated, tags are applied.

---

## 13. Rollback Plan

Each phase has a specific rollback.

- **Phase 2 (script)**: revert the commit; the pre-existing `ensure_cloudfront_distribution` path runs. No AWS-side changes to undo.
- **Phase 3 (workflow)**: revert the commit. Concurrency group is a workflow-scoped property; removing it has no durable state.
- **Phase 4 (Terraform migration)**: two levels of rollback.
  - *Per-change rollback*: `git revert` the offending Terraform PR and `terraform apply`. Because imports preserve the existing resources verbatim, reverting module changes reverts to the previously applied state without touching CloudFront identity.
  - *Full abandonment*: if the Terraform approach must be scrapped, run `terraform state rm <address>` for every resource and re-enable the old `ensure_*` functions in `scripts/deploy_aws.sh` (keep them on a `legacy-deploy-script` branch for 30 days after Phase 4d ships). Resources are not destroyed; they just stop being tracked by Terraform and the shell script resumes managing them. This is the escape hatch that makes Phase 4 a low-risk migration.
  - The state backend bucket and lock table can be emptied and deleted if the decision is made to fully abandon Terraform, but that is irreversible and should be a deliberate decision, not a reflex.
- **Phase 5a–5d (headers, TLS, logs, WAF)**: each is a Terraform PR revert. `terraform apply` restores the prior config. ETags are managed by Terraform internally.
- **Phase 5e (OAC migration)**: the riskiest step. Rollback window 14 days:
  1. `var.enable_oac = false` in the env's `terraform.tfvars`.
  2. `terraform apply` — Terraform re-enables website hosting, restores the public bucket policy (from module code, not git-stored secrets), repoints the origin to the website endpoint, disassociates and destroys the OAC.
  3. Verify the site loads over HTTPS via the CloudFront URL.
  Because Terraform captures both states declaratively, the rollback is a single variable flip rather than a five-step CLI dance.
- **Phase 6 (custom domain)**: set `var.custom_domain = null` and apply. Terraform removes the alias, DNS record, and ACM cert. Users fall back to `*.cloudfront.net`.
- **Phase 7 (duplicate cleanup)**: deletion is irreversible, but recreatable. CloudFront distributions can be re-provisioned via `var.enable_create = true` equivalent in the bootstrap workflow if a wrong one was deleted. Keep a 7-day delay between disable and delete to allow recovery.

---

## 14. Runbooks

### 14.1 Bootstrapping a new environment (new account or OSS fork)

Prerequisites:
- AWS account with the IAM role from §10 configured.
- `APP_NAME`, `APP_ENV`, `AWS_ACCOUNT_ID`, `AWS_REGION` decided.
- Local AWS credentials for that account with the bootstrap-only IAM (Statement 7) attached.

Steps:

1. `export APP_NAME=x12-parser-encoder APP_ENV=staging AWS_ACCOUNT_ID=… AWS_REGION=… CLOUDFRONT_ALLOW_CREATE=true`
2. `bash scripts/deploy_aws.sh` — runs end-to-end, creates S3 bucket, ECR repo, legacy managed container service role, legacy managed container service service, and CloudFront distribution. Logs the new distribution id and the handshake command.
3. Run the printed `gh variable set CLOUDFRONT_DISTRIBUTION_ID --env "${APP_ENV}" --body "…"` command (requires repo push access).
4. Unset `CLOUDFRONT_ALLOW_CREATE`. All subsequent deploys must refuse to create.
5. Optional: configure the custom domain per §7.10.

### 14.2 Recovering from a lost distribution id (SSM wiped, GH var cleared)

1. Run `aws resourcegroupstaggingapi get-resources --resource-type-filters cloudfront:distribution --tag-filters Key=Application,Values=${APP_NAME} Key=Environment,Values=${APP_ENV}` to recover the id from tags.
2. If tags are also lost: `aws cloudfront list-distributions` and manual identification via DNS / deployed SPA source hash.
3. Re-populate SSM and the GH variable.

### 14.3 Deleting duplicate distributions (Phase 6)

1. List candidates:
   ```bash
   aws cloudfront list-distributions \
     --query "DistributionList.Items[?Comment=='x12-parser-encoder web'].{Id:Id,Domain:DomainName,Enabled:Enabled,Status:Status}" \
     --output table
   ```
2. Exclude the canonical id from SSM.
3. For each remaining id:
   - `aws cloudfront get-distribution-config --id <id>` → capture `ETag` and config JSON.
   - Edit config: `Enabled = false`. `update-distribution` with the ETag.
   - Poll `get-distribution --id <id> --query 'Distribution.Status'` until `Deployed` (~15 min).
   - `get-distribution --id <id> --query 'ETag' --output text` → fresh ETag.
   - `delete-distribution --id <id> --if-match <etag>`.
4. Log each deletion in the release notes.

### 14.4 Incident: a new CloudFront URL appeared after a deploy

1. Immediately check which workflow run created it (`aws cloudfront list-distributions --query "DistributionList.Items[?contains(Tags.Items[?Key=='ManagedBy'].Value|[0],'deploy_aws.sh')].[Id,DomainName,LastModifiedTime]" --output table`).
2. Confirm the canonical id in SSM.
3. If the canonical id still exists and serves traffic: the new distribution is the duplicate. Disable it per §14.3.
4. If the canonical id is gone: restore from §14.2, then treat the new one as the duplicate.
5. File a post-incident review asking *how* the lookup missed — this is the signal that Phase 2's guards are incomplete.

---

## 15. Documentation Updates

Part of Phase 2's PR, not a follow-up:

- [README.md](../../README.md): deployment section documents `APP_ENV`, `CLOUDFRONT_DISTRIBUTION_ID`, `CLOUDFRONT_ALLOW_CREATE`, states the **pinned CloudFront URL product policy** (§2.1), and links to this plan's §14.1 bootstrap runbook. After Phase 4, adds a pointer to `infra/terraform/README.md` as the canonical infra doc. The current published CloudFront URL is the user contract; any change requires a deliberate, communicated event.
- [Makefile](../../Makefile): `deploy` and new `deploy-bootstrap` targets document the supported variables in a header comment. After Phase 4, adds `tf-plan`, `tf-apply`, and `tf-destroy-staging` targets that wrap the Terraform workflow. (Code changes already specified in §9 Phase 2 and Phase 4d.)
- `infra/terraform/README.md`: **new file**, authored in Phase 4. Covers: backend bootstrap, per-environment init, plan/apply workflow, import runbook, drift response, and the escape-hatch rollback from §13.
- Per-module `README.md` files under `infra/terraform/modules/*/`: variables, outputs, and example usage. Generated with `terraform-docs` in CI.
- [CLAUDE.md](../../CLAUDE.md): add "Terraform state lives in `infra/terraform/`; never hand-edit AWS resources managed by Terraform — propose a module change instead." Reference this plan under "Commands → Release & hygiene".
- [SECURITY.md](../../SECURITY.md): document the OAC + HSTS posture once Phase 5 ships.
- [CONTRIBUTING.md](../../CONTRIBUTING.md): add a sentence that infra changes require a plan in `docs/plans/`, a `terraform plan` run, and a bootstrap-run verification.
- Version bump: none required for Phase 2–3 (pure infra hygiene). Phase 4 itself does not require a bump because user-visible behavior is unchanged. Phase 5–6 may warrant a minor bump if user-visible behavior changes (e.g., custom domain rollout, tightened CSP affecting embeds).

---

## 16. Acceptance Criteria

### Phase 2–3 (script + workflow hardening)

1. Two consecutive production deploys print the same CloudFront distribution id and domain.
2. The deploy script does not call any `create-distribution*` API during normal CI runs.
3. A missing, mismatched, or ambiguous distribution fails the deploy with a single actionable error that names the next command to run.
4. Concurrent pushes to `main` (or a push plus a `workflow_dispatch`) never run two deploy jobs at once for the same environment.
5. An SSM parameter at `/${APP_NAME}/${APP_ENV}/cloudfront/distribution-id` is the authoritative record; deleting it and rerunning the deploy recovers from tags.
6. The CloudFront distribution carries `Application`, `Environment`, and `ManagedBy` tags.
7. The IAM role used by the deploy workflow is scoped per §10; no wildcard `cloudfront:*` in production.
8. A new maintainer, following the README, can set up a working deployment in their own AWS account in under 30 minutes, without editing `scripts/deploy_aws.sh`.

### Phase 4 (Terraform migration)

9. After import, `terraform plan` on `production` reports zero destructive changes and the CloudFront distribution id is unchanged.
10. The deploy script no longer calls `aws s3api create-bucket`, `aws ecr create-repository`, `aws iam create-role`, `aws apprunner create-service|update-service`, or any `aws cloudfront create-distribution*` — all creates/updates route through `terraform apply`.
11. `infra/terraform/modules/*` each pass `terraform validate`, `tflint`, and `tfsec` in CI with zero findings (or explicitly suppressed findings with justification).
12. A weekly drift-detection run exists and demonstrably files a GitHub issue when a resource is tampered with in the console (verified once at go-live with an intentional drift).
13. A downstream OSS operator can clone the repo, run `scripts/bootstrap_tf_backend.sh` + `terraform init` + `terraform apply` in their own AWS account, and end up with a working deployment using only documentation in `infra/terraform/README.md`.

### Phase 5 (security hardening)

14. The web bucket has `BlockPublicAcls=true`, `BlockPublicPolicy=true`, `RestrictPublicBuckets=true`, and an empty public-access principal list once OAC is on.
15. `curl -I` against the distribution returns `Strict-Transport-Security`, `X-Content-Type-Options`, and `Referrer-Policy` headers matching §7.9.
16. WAFv2 is attached and blocks known-bad-inputs test traffic (verified with a deliberate probe).

### Phase 6–7

17. The custom domain resolves, presents a valid ACM cert, and is in the distribution `Aliases`.
18. Duplicate distributions from the pre-fix era are disabled and deleted, with the action logged in the release notes.

---

## 17. Open Questions

1. Does the project have an existing custom domain, or will operators be expected to bring one? (Affects Phase 6 timing.)
2. Should the `bootstrap` workflow be a separate repo workflow, or a documented local-only script? (Trade-off: discoverability vs. blast radius if someone triggers it accidentally.) — tentative answer: local-only script for now; re-evaluate after Phase 4.
3. Drift detection is resolved by Phase 4g (weekly `terraform plan`); remove once Phase 4 ships.
4. Should the Terraform backend state bucket live in the same account as the workloads, or a separate "management" account? For this project's size and audience, same-account is fine; a fork with a hub-and-spoke multi-account setup can override via `backend.hcl`.
5. Follow-on initiative (separate plan, not this one): "Portable compute layer." Replace `modules/app_runner/` with `modules/ecs_service/` (ECS Fargate behind an ALB) so the stack has no AWS-only runtime services. Target audience: OSS operators running on non-AWS clouds or hybrid.

---

## 18. Timeline and Sequencing

| Phase | Est. effort | Blocking | Owner |
|---|---|---|---|
| 1. Containment | 30 min | None | Human operator |
| 2. Script hardening | 1 day incl. tests | Phase 1 | Platform |
| 3. Workflow hardening | 2 hours | Phase 2 merged | Platform |
| 4. Terraform migration | 3–5 days | Phase 3 stable in prod | Platform |
| 5a–5d. Response headers, TLS, logs, WAF (in Terraform) | 1 day | Phase 4 complete | Platform + Security |
| 5e. OAC migration (in Terraform) | 0.5 day incl. 14-day rollback window | Phase 5a–5d shipped | Platform |
| 6. Custom domain (in Terraform) | 0.5 day + DNS TTL | Operator decision | Platform |
| 7. Duplicate cleanup | 1 hour (spread over ~2 weeks of verification) | Two successful prod deploys post-Phase 4 | Platform |

Phase 2 ships the moment containment is verified — it stops the bleeding. Phase 3 follows within hours. Phase 4 is the larger investment but is the foundation for everything after; Phase 5 onward assumes Terraform ownership and does not duplicate work in the shell script.

---

## 19. Appendix: Environment variable reference

| Variable | Source | Default | Purpose |
|---|---|---|---|
| `APP_NAME` | script / workflow | `x12-parser-encoder` | Application namespace for resource names and tags. |
| `APP_ENV` | workflow var | `production` | Environment namespace. Distinguishes staging / forks. |
| `AWS_ACCOUNT_ID` | workflow var | repo default | Target account. Asserted via STS. |
| `AWS_REGION` | workflow var | `us-east-2` | Target region for S3, ECR, legacy managed container service. CloudFront is global. |
| `S3_BUCKET` | workflow var | derived (see §7.1) | Web assets bucket. Must not change between deploys for a given env. |
| `ECR_REPOSITORY` | workflow var | `${APP_NAME}-${APP_ENV}-api` | API image repo. |
| `APP_RUNNER_SERVICE` | workflow var | `${APP_NAME}-${APP_ENV}-api` | Service name. |
| `APP_RUNNER_ECR_ACCESS_ROLE` | workflow var | `${APP_NAME}-apprunner-ecr-access` | IAM role legacy managed container service uses to pull from ECR. |
| `CLOUDFRONT_DISTRIBUTION_ID` | workflow var (per env) | unset | **New in Phase 2.** Canonical distribution id. Written after bootstrap. After Phase 4, this is read from Terraform output and the env var becomes a defense-in-depth mirror. |
| `CLOUDFRONT_ALLOW_CREATE` | workflow input | `false` | **New in Phase 2.** Gate on the create path in the shell script. Becomes unused after Phase 4 (Terraform owns creation). |
| `EXTRA_CORS_ALLOWED_ORIGINS` | workflow var | empty | Comma-separated additional origins for the legacy managed container service CORS allowlist. |
| `RATE_LIMIT_ENABLED`, `REQUESTS_PER_MINUTE`, `CONCURRENT_UPLOAD_LIMIT`, `AUTH_BOUNDARY_ENABLED` | workflow var | existing defaults | API runtime env — unchanged by this plan. |

### 19.1 Terraform variables (Phase 4+)

Terraform variables are passed via `terraform.tfvars`, `-var`, or `TF_VAR_*` environment variables. The root module variables are specified in §7.11; the CI entry points that set them:

| Variable | Source | Default | Notes |
|---|---|---|---|
| `TF_VAR_app_name` | workflow env | `x12-parser-encoder` | Mirrors `APP_NAME`. |
| `TF_VAR_app_env` | workflow env | `production` | Mirrors `APP_ENV`. |
| `TF_VAR_aws_account_id` | workflow var | repo default | Asserted vs caller identity by a `check` block. |
| `TF_VAR_aws_region` | workflow var | `us-east-2` | |
| `TF_VAR_api_image_tag` | derived | `main-${{ github.sha }}` | Passed on every deploy; drives legacy managed container service service update. |
| `TF_VAR_extra_cors_allowed_origins` | workflow var | `[]` | Mirrors `EXTRA_CORS_ALLOWED_ORIGINS`, parsed to a list in Terraform. |
| `TF_VAR_custom_domain` | workflow var | `null` | Phase 6. |
| `TF_VAR_enable_waf` | workflow var | `false` | Phase 5. |
| `TF_VAR_enable_oac` | workflow var | `false` | Phase 5. Flipping this is a real infra change; expect a 5–10 min apply.
 |

Backend configuration (`-backend-config` via `backend.hcl`, not a `TF_VAR_*`):

| Key | Value |
|---|---|
| `bucket` | `${APP_NAME}-tfstate-${AWS_ACCOUNT_ID}-${AWS_REGION}` |
| `key` | `${APP_ENV}/terraform.tfstate` |
| `region` | `${AWS_REGION}` |
| `encrypt` | `true` |
| `dynamodb_table` | `${APP_NAME}-tflocks` |
