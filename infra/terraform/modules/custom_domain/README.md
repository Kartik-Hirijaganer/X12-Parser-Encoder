# custom_domain

Provisions the optional Phase 5 custom-domain pieces for the CloudFront distribution:

- ACM certificate in `us-east-1` with DNS validation.
- Route 53 ACM validation records when `dns_provider = "route53"`.
- DNS validation records as outputs when `dns_provider = "external"`.

The environment root owns the CloudFront alias and final Route 53 `A` ALIAS
record. Keeping those records outside this module prevents the ACM certificate
from depending on CloudFront while CloudFront depends on the certificate.

## Inputs

| Name | Description | Default |
|---|---|---|
| `domain_name` | Custom domain name. Null disables this module. | `null` |
| `dns_provider` | `route53` creates DNS records; `external` only outputs required records. | `route53` |
| `hosted_zone_id` | Route 53 hosted zone ID when using Route 53 DNS. | `null` |
| `tags` | Tags for ACM resources. | `{}` |

## Outputs

| Name | Description |
|---|---|
| `domain_name` | Custom domain name, or `null` when disabled. |
| `certificate_arn` | ACM certificate ARN. Route 53 mode waits for DNS validation. |
| `validation_records` | ACM DNS validation records for external DNS providers. |
| `cname_record` | Deprecated compatibility output. Environment roots provide the CloudFront CNAME target. |

## Usage

```hcl
module "custom_domain" {
  source = "../../modules/custom_domain"

  providers = {
    aws = aws.global
  }

  domain_name                            = var.custom_domain
  dns_provider                           = var.dns_provider
  hosted_zone_id                         = var.hosted_zone_id
  tags                                   = local.common_tags
}
```
