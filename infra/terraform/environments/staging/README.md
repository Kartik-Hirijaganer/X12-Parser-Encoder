# staging

Terraform root for the serverless staging deploy.

Create local-only config before applying:

```bash
cp terraform.tfvars.example terraform.tfvars
cp ../../backend.hcl.example backend.hcl
```

Set `backend.hcl` key to `staging/terraform.tfstate`, replace the state bucket placeholders, and replace `origin_verify_header_value` in `terraform.tfvars`.

The first staging bootstrap should keep `manage_github_oidc_provider = true` so Terraform creates the account-level GitHub Actions OIDC provider. Later deploys use the Terraform-managed role `x12-parser-encoder-deploy-staging`.

Staging keeps Phase 4 production knobs conservative by default:

- `enable_snapstart = false`
- `reserved_concurrency = 10`
- `enable_waf = false`

Set `enable_waf = true` temporarily in staging when testing WAF behavior before applying production.

To test the optional Phase 5 hostname path, set `custom_domain`, `dns_provider`, and `hosted_zone_id` in `terraform.tfvars`. Route 53 mode provisions the ACM certificate, validation records, CloudFront alias, and Route 53 ALIAS record.
