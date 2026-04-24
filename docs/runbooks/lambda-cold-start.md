# Lambda Cold-Start Verification

You should be done in < 5 min once the CloudFront URL is deployed.

Use this after enabling SnapStart in production. SnapStart applies only to published Lambda versions, and this stack invokes the `live` alias through the Function URL.

## Preconditions

- Production has been applied with `enable_snapstart = true`.
- `terraform output -raw cloudfront_url` works from `infra/terraform/environments/production`.
- `aws logs` can read the Lambda log group.

## Measure

```bash
cd infra/terraform/environments/production
export BASE_URL="$(terraform output -raw cloudfront_url)"
export LOG_GROUP="$(terraform output -raw lambda_log_group_name)"

for i in $(seq 1 50); do
  curl -fsS "$BASE_URL/api/v1/health" >/dev/null
  sleep 900
done

aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"Init Duration"' \
  --query 'events[].message' \
  --output text
```

Compare the p50 `Init Duration` values with the Phase 3 baseline. The Phase 4 acceptance bar is material improvement, not a hard-coded millisecond target.

## If SnapStart Is Disabled

Document the reason in the production deploy notes, usually one of:

- The selected region does not support Python SnapStart.
- The function moved to a container image.
- The function uses a SnapStart-incompatible Lambda feature.

AWS references: [SnapStart support](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html), [activation and version behavior](https://docs.aws.amazon.com/lambda/latest/dg/snapstart-activate.html).
