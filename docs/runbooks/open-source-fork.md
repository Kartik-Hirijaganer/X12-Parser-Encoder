# Open-Source Fork Deploy

You should be done in < 5 min after AWS account prerequisites exist.

Use this as the fork-operator path for deploying the default AWS serverless stack.

## Local Bootstrap

```bash
git clone https://github.com/<you>/X12-Parser-Encoder.git
cd X12-Parser-Encoder
make install
make test
bash scripts/bootstrap_tf_backend.sh
```

## Configure Production

```bash
cp infra/terraform/environments/production/terraform.tfvars.example infra/terraform/environments/production/terraform.tfvars
${EDITOR:-vi} infra/terraform/environments/production/terraform.tfvars
```

Set app name, region, alerting, WAF, and origin-secret values for your account. Keep real PHI out of tfvars files committed to Git.

## Deploy

```bash
make deploy AWS_PROFILE=<explicit-profile>
```

For GitHub Actions, add:

- Repository variable `AWS_ACCOUNT_ID=970385384114`.
- Repository variable `LAMBDA_VERSION_KEEP_COUNT=1`.
- Optional repository variables `AWS_REGION`, `APP_NAME`, `LAMBDA_ARCHITECTURE`.
- Protected `production` environment secret `TERRAFORM_TFVARS`.

Run the `Deploy` workflow with `workflow_dispatch` for production.

## Verify

```bash
cd infra/terraform/environments/production
export BASE_URL="$(terraform output -raw cloudfront_url)"
curl -fsS "${BASE_URL}/api/v1/health"
```

Open the CloudFront URL and run the generate, validate, parse, dashboard, and export workflow with synthetic fixtures only.
