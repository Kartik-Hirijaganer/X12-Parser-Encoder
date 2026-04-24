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

## Configure Staging

```bash
cp infra/terraform/environments/staging/terraform.tfvars.example infra/terraform/environments/staging/terraform.tfvars
${EDITOR:-vi} infra/terraform/environments/staging/terraform.tfvars
```

Set app name, region, alerting, WAF, and origin-secret values for your account. Keep real PHI out of tfvars files committed to Git.

## Deploy

```bash
make deploy ENV=staging
```

For GitHub Actions, add:

- Repository variable `AWS_ACCOUNT_ID`.
- Optional repository variables `AWS_REGION`, `APP_NAME`, `LAMBDA_ARCHITECTURE`.
- Environment secret `TERRAFORM_TFVARS` for each deploy environment.

Run the `Deploy` workflow with `workflow_dispatch` for production.

## Verify

```bash
cd infra/terraform/environments/staging
export BASE_URL="$(terraform output -raw cloudfront_url)"
curl -fsS "${BASE_URL}/api/v1/health"
```

Open the CloudFront URL and run the generate, validate, parse, dashboard, and export workflow with synthetic fixtures only.
