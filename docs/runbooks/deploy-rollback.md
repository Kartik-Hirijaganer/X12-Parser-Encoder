# Deploy Rollback

You should be done in < 5 min once Terraform state is reachable.

Use this when the latest deploy is unhealthy and you need to roll production forward from the previous known-good artifact and SPA source. Production retains one published Lambda version, so recovery creates a new version rather than swinging `live` to an older retained version.

## Preconditions

- The explicit AWS profile resolves to account `970385384114`.
- The previous Lambda artifact key and web artifact source are in the deploy summary, GitHub Actions log, or release notes.
- AWS credentials can assume the deploy role for that environment.

## Roll Back Lambda

```bash
export AWS_PROFILE=<explicit-profile>
export ENV=production
export AWS_REGION=us-east-2
export TF_DIR="infra/terraform/environments/${ENV}"
export PREVIOUS_KEY="lambda-artifacts/${ENV}/<previous-git-sha>.zip"
export TFSTATE_BUCKET="$(terraform -chdir="${TF_DIR}" output -raw terraform_state_bucket 2>/dev/null || echo "<tfstate-bucket>")"

terraform -chdir="${TF_DIR}" init -backend-config=backend.hcl
test "$(aws sts get-caller-identity --query Account --output text)" = "970385384114"
terraform -chdir="${TF_DIR}" apply \
  -var "lambda_zip_s3_bucket=${TFSTATE_BUCKET}" \
  -var "lambda_zip_s3_key=${PREVIOUS_KEY}" \
  -var-file=terraform.tfvars
bash scripts/prune_lambda_versions.sh x12-parser-encoder-api-production
```

If `terraform_state_bucket` is not an output in your environment, set `TFSTATE_BUCKET` to the bootstrap bucket name: `<app-name>-tfstate-<account-id>-<region>`.

## Roll Back SPA

```bash
export SPA_BUCKET="$(terraform -chdir="${TF_DIR}" output -raw spa_bucket_name)"
# From a clean checkout of the last good Git SHA:
(cd apps/web && npm ci && npm run build)
aws s3 sync apps/web/dist/ "s3://${SPA_BUCKET}/" --delete

export DISTRIBUTION_ID="$(terraform -chdir="${TF_DIR}" output -raw cloudfront_distribution_id)"
aws cloudfront create-invalidation --distribution-id "${DISTRIBUTION_ID}" --paths "/*"
```

## Verify

```bash
export BASE_URL="$(terraform -chdir="${TF_DIR}" output -raw cloudfront_url)"
curl -fsS "${BASE_URL}/api/v1/health"
```

Record the rollback Git SHA, Lambda version, CloudFront invalidation id, and reason in the incident notes.
