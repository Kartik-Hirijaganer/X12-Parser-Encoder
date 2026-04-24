# waf

Creates the CloudFront-scope WAF web ACL used in Phase 4.

Rules:

- `AWSManagedRulesCommonRuleSet`
- `AWSManagedRulesKnownBadInputsRuleSet`
- `RateLimitByIp` at 2,000 requests per 5 minutes per source IP by default
- `UploadBodySizeLimit`, which blocks `Content-Length` values above 6 MiB with `413`
- Optional geo allow-list, disabled by default

The common rule set's `SizeRestrictions_BODY` rule is overridden to `count` so normal multipart uploads are not blocked below the app's 5 MiB upload contract. The explicit upload-size rule owns that edge check. It uses `Content-Length` because AWS WAF body inspection for CloudFront is capped below this app's upload size; the application still enforces the authoritative 5 MiB API limit.

## Inputs

| Name | Description | Default |
|---|---|---|
| `name_prefix` | Prefix for the WAF web ACL and metrics. | Required |
| `rate_limit_per_5_min` | Per-IP request limit over 5 minutes. | `2000` |
| `geo_allow_countries` | Optional ISO country allow-list; empty means global. | `[]` |
| `tags` | Tags for WAF resources. | `{}` |

## Outputs

| Name | Description |
|---|---|
| `web_acl_arn` | WAF web ACL ARN for CloudFront `web_acl_id`. |
| `web_acl_id` | WAF web ACL ID. |
| `rate_limit_per_5_min` | Configured per-IP rate limit. |

## Usage

```hcl
module "waf" {
  count       = var.enable_waf ? 1 : 0
  source      = "../../modules/waf"
  name_prefix = "x12-parser-encoder-example"
}
```
