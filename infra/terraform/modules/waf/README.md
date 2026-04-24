# waf

Phase 4 implements WAF rules. Phase 2 provides this stub so environment wiring can keep a stable module boundary.

## Inputs

| Name | Description | Default |
|---|---|---|
| `name_prefix` | Prefix reserved for the WAF web ACL. | Required |
| `tags` | Tags reserved for WAF resources. | `{}` |

## Outputs

| Name | Description |
|---|---|
| `web_acl_arn` | WAF web ACL ARN. `null` until Phase 4. |

## Usage

```hcl
module "waf" {
  count       = var.enable_waf ? 1 : 0
  source      = "../../modules/waf"
  name_prefix = "x12-parser-encoder-example"
}
```
