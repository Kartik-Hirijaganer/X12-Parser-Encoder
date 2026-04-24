# Custom Domain

You should be done in < 5 min after DNS prerequisites are ready.

Use this when mapping an operator-owned hostname to the existing CloudFront distribution.

## Preconditions

- The Route 53 hosted zone already exists in the AWS account.
- The hostname is dedicated to this app, for example `x12.example.com`.
- You have decided whether this is `staging` or `production`.

## Configure Terraform

```bash
cd infra/terraform/environments/production
cp terraform.tfvars.example terraform.tfvars
```

Set or update these values:

```hcl
custom_domain_name = "x12.example.com"
hosted_zone_id     = "Z1234567890"
enable_waf         = true
```

Then apply:

```bash
terraform init -backend-config=backend.hcl
terraform apply -var-file=terraform.tfvars
```

## Verify

```bash
dig +short x12.example.com
curl -I https://x12.example.com/
curl -fsS https://x12.example.com/api/v1/health
```

The certificate must be issued in `us-east-1` for CloudFront. If validation stalls, check the Route 53 validation records from Terraform output and confirm the hosted zone matches the hostname.
