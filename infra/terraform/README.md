# Terraform Infrastructure

This tree provisions the Phase 2 serverless foundation: a private S3 SPA bucket, a Lambda API with a public Function URL, one CloudFront distribution, optional WAF/custom-domain stubs, and CloudWatch observability.

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

## Example Environment

The example environment is the fork-operator starting point. It uses safe Phase 2 defaults and a placeholder Lambda zip so `terraform plan` can run before Phase 3 produces `build/lambda.zip`.

```bash
cd infra/terraform/environments/example
cp terraform.tfvars.example terraform.tfvars
terraform init -backend=false
terraform validate
terraform plan -var-file=terraform.tfvars
```

The checked-in `placeholder-lambda.zip` is intentionally not deployable. It exists only to let Terraform calculate a local zip hash during Phase 2 planning.

## State Path

Root state keys must use:

```hcl
key = "<APP_ENV>/terraform.tfstate"
```

For example:

```hcl
key = "staging/terraform.tfstate"
```
