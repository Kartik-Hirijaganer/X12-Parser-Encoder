# custom_domain

Provisions the optional Phase 5 custom-domain pieces for the CloudFront distribution:

- ACM certificate in `us-east-1` with DNS validation.
- Route 53 ACM validation records and an `A` ALIAS record when `dns_provider = "route53"`.
- DNS instructions as outputs when `dns_provider = "external"`.

## Inputs

| Name | Description | Default |
|---|---|---|
| `domain_name` | Custom domain name. Null disables this module. | `null` |
| `dns_provider` | `route53` creates DNS records; `external` only outputs required records. | `route53` |
| `hosted_zone_id` | Route 53 hosted zone ID when using Route 53 DNS. | `null` |
| `cloudfront_distribution_domain_name` | CloudFront target domain for ALIAS/CNAME records. | `null` |
| `cloudfront_distribution_hosted_zone_id` | CloudFront hosted zone ID for Route 53 ALIAS records. | `null` |
| `tags` | Tags for ACM resources. | `{}` |

## Outputs

| Name | Description |
|---|---|
| `domain_name` | Custom domain name, or `null` when disabled. |
| `certificate_arn` | ACM certificate ARN. Route 53 mode waits for DNS validation. |
| `validation_records` | ACM DNS validation records for external DNS providers. |
| `cname_record` | CNAME target for external DNS providers. |
| `route53_alias_fqdn` | Route 53 ALIAS FQDN when Terraform manages Route 53. |

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
  cloudfront_distribution_domain_name    = module.cloudfront_distribution.domain_name
  cloudfront_distribution_hosted_zone_id = module.cloudfront_distribution.hosted_zone_id
  tags                                   = local.common_tags
}
```
