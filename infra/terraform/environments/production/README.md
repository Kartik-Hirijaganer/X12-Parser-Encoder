# production

Terraform root for the Phase 4 serverless production path.

Create local-only config before applying:

```bash
cp terraform.tfvars.example terraform.tfvars
cp ../../backend.hcl.example backend.hcl
```

Set `backend.hcl` key to `production/terraform.tfstate`, replace the state bucket placeholders, and replace `origin_verify_header_value` in `terraform.tfvars`.

Production deploys are manual only through the GitHub `Deploy` workflow with `environment=production`, or locally with:

```bash
make deploy ENV=production
```

Production defaults:

- `enable_snapstart = true`
- `reserved_concurrency = 50`
- `enable_waf = true`
- WAF rate limit: 2,000 requests per 5 minutes per source IP
- No WAF geo filter unless `waf_geo_allow_countries` is set

To enable the optional Phase 5 branded hostname, set `custom_domain`, `dns_provider`, and `hosted_zone_id` in the protected production `TERRAFORM_TFVARS` secret. Route 53 mode provisions the ACM certificate and validation records first, then attaches the CloudFront alias and creates the Route 53 ALIAS record from the environment root.
