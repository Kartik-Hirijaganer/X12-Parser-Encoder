# WAF IP Unblock

You should be done in < 5 min.

Use this when a legitimate tester is blocked by the WAF rate-based rule. This Phase 4 WAF does not maintain a manual block list; rate blocks expire automatically when the source IP falls below 2,000 requests in the trailing 5-minute window.

## Confirm The Block

```bash
cd infra/terraform/environments/production
export WEB_ACL_ARN="$(terraform output -raw waf_web_acl_arn)"

aws wafv2 get-sampled-requests \
  --region us-east-1 \
  --scope CLOUDFRONT \
  --web-acl-arn "$WEB_ACL_ARN" \
  --rule-metric-name x12-parser-encoder-production-rate-limit \
  --time-window StartTime="$(date -u -v-10M +%FT%TZ)",EndTime="$(date -u +%FT%TZ)" \
  --max-items 100
```

On Linux, replace the `date -v-10M` command with:

```bash
date -u -d '10 minutes ago' +%FT%TZ
```

## Unblock

1. Ask the tester to stop the burst client.
2. Wait 5 minutes for the rate window to decay.
3. Retry:

```bash
curl -i "$(terraform output -raw cloudfront_url)/api/v1/health"
```

If the request is still blocked, inspect sampled requests for a managed-rule match. Do not disable WAF globally to unblock one client; either fix the offending request or make a narrow Terraform rule override in a follow-up change.

AWS reference: [AWS WAF rate-based rules](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based.html).
