# custom_domain

Phase 5 implements ACM and Route 53 custom-domain support. Phase 2 provides this stub so the module path and contract exist.

## Inputs

| Name | Description | Default |
|---|---|---|
| `domain_name` | Custom domain name. | `null` |
| `hosted_zone_id` | Route 53 hosted zone ID. | `null` |
| `cloudfront_distribution_domain_name` | CloudFront target domain. | `null` |
| `cloudfront_distribution_hosted_zone_id` | CloudFront hosted zone ID. | `null` |
| `tags` | Tags reserved for custom-domain resources. | `{}` |

## Outputs

| Name | Description |
|---|---|
| `domain_name` | Custom domain name. `null` until Phase 5. |
| `certificate_arn` | ACM certificate ARN. `null` until Phase 5. |

## Usage

```hcl
module "custom_domain" {
  source      = "../../modules/custom_domain"
  domain_name = var.custom_domain_name
}
```
