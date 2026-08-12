# Terraform Infrastructure

This tree provisions the production serverless foundation: a private S3 SPA bucket, a Lambda API with a public Function URL, one CloudFront distribution, optional custom-domain support, CloudFront WAF, CloudWatch observability, and a GitHub OIDC deploy role.

## Bootstrap State

Run the bootstrap root module once per AWS account and region before using a remote backend:

```bash
cd infra/terraform/bootstrap
terraform init
terraform apply -var app_name=x12-parser-encoder -var aws_region=us-east-2
```

The bootstrap module creates:

- `x12-parser-encoder-tfstate-<account-id>-<region>` with versioning, encryption, and public access blocked.
- `x12-parser-encoder-tflocks` for DynamoDB state locking.

Copy `infra/terraform/backend.hcl.example` to a local backend file, replace the account/region placeholders, and set `key` to `${APP_ENV}/terraform.tfstate`.

The idempotent wrapper runs the same bootstrap module:

```bash
APP_NAME=x12-parser-encoder AWS_REGION=us-east-2 scripts/bootstrap_tf_backend.sh
```

## Example Environment

The example environment is the fork-operator starting point. It uses safe defaults and a placeholder Lambda zip so `terraform plan` can run before a deploy produces `build/lambda.zip`.

```bash
cd infra/terraform/environments/example
cp terraform.tfvars.example terraform.tfvars
terraform init -backend=false
terraform validate
terraform plan -var-file=terraform.tfvars
```

The checked-in `placeholder-lambda.zip` is intentionally not deployable. It exists only to let Terraform calculate a local zip hash during Phase 2 planning.

## Production

`environments/production` is the only deployed root used by `make deploy` and GitHub Actions. `environments/example` remains local-only for validation and fork operators.

For local use:

```bash
cd infra/terraform/environments/production
cp terraform.tfvars.example terraform.tfvars
cp ../../backend.hcl.example backend.hcl
# Replace bucket/account/key placeholders and origin_verify_header_value.
terraform init -backend-config=backend.hcl
```

For GitHub Actions, create a protected environment named `production` with a `TERRAFORM_TFVARS` secret containing the full contents of `production/terraform.tfvars`. Set repository variables `AWS_ACCOUNT_ID=970385384114` and `LAMBDA_VERSION_KEEP_COUNT=1`. The workflow writes `backend.hcl` at runtime from `AWS_ACCOUNT_ID`, `AWS_REGION`, and `APP_NAME`.

The deploy role names are:

```text
x12-parser-encoder-deploy-production
```

Production owns the account-level GitHub OIDC provider and deploy role through its Terraform state. Production defaults enable WAF, set Lambda reserved concurrency to `50`, and enable SnapStart for the default `us-east-2` Python 3.12 deployment.

## Custom Domain

Phase 5 custom domains are optional. To use Route 53 DNS, set these values in the environment `terraform.tfvars`:

```hcl
custom_domain = "app.example.com"
dns_provider  = "route53"
hosted_zone_id = "Z1234567890"
```

Terraform creates the `us-east-1` ACM certificate and DNS validation records before CloudFront consumes the certificate. The environment root then creates the Route 53 `A` ALIAS record to CloudFront. The raw `*.cloudfront.net` hostname remains available.

For non-Route-53 DNS, set `dns_provider = "external"` and read `custom_domain_validation_records` plus `custom_domain_cname_record` from Terraform outputs. Add those records at the external provider, then re-apply after ACM has issued the certificate.

## State Path

Root state keys must use:

```hcl
key = "<APP_ENV>/terraform.tfstate"
```

For production:

```hcl
key = "production/terraform.tfstate"
```
