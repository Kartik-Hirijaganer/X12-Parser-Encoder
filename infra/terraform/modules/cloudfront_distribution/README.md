# cloudfront_distribution

Provisions the single CloudFront distribution with a private S3 SPA default origin and a `/api/*` Lambda Function URL origin. CloudFront injects `X-Origin-Verify` for the Lambda origin; no Lambda OAC is created in Phase 2.

## Inputs

| Name | Description | Default |
|---|---|---|
| `name_prefix` | Prefix for CloudFront support resources. | Required |
| `spa_bucket_regional_domain` | Regional S3 bucket domain for the SPA origin. | Required |
| `lambda_function_url_domain` | Lambda Function URL domain without scheme or slash. | Required |
| `origin_verify_header_value` | Secret sent as `X-Origin-Verify` to the Lambda origin. | Required |
| `price_class` | CloudFront price class. | `PriceClass_100` |
| `enable_waf` | Attach a WAF web ACL. | `false` |
| `waf_web_acl_arn` | WAF web ACL ARN when WAF is enabled. | `null` |
| `response_headers_policy_id` | Existing response headers policy ID; otherwise this module creates one. | `null` |
| `content_security_policy` | Baseline CSP value. | Permissive Phase 2 policy |
| `tags` | Tags for resources. | `{}` |

## Outputs

| Name | Description |
|---|---|
| `distribution_id` | CloudFront distribution ID. |
| `domain_name` | CloudFront distribution domain name. |
| `distribution_arn` | CloudFront distribution ARN. |

## Usage

```hcl
module "cloudfront_distribution" {
  source                     = "../../modules/cloudfront_distribution"
  name_prefix                = "x12-parser-encoder-example"
  spa_bucket_regional_domain = module.s3_spa.bucket_regional_domain_name
  lambda_function_url_domain = module.lambda_api.function_url_domain
  origin_verify_header_value = var.origin_verify_header_value
}
```
