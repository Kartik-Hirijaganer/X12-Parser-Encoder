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

results_dir="$(mktemp -d)"
for i in $(seq 1 20); do
  curl -fsS -o "${results_dir}/${i}.json" \
    -w '%{http_code}\t%{time_total}\n' \
    "$BASE_URL/api/v1/health" > "${results_dir}/${i}.metrics" &
done
wait

aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"Init Duration"' \
  --query 'events[].message' \
  --output text
```

Record health latency p50/p95, Lambda errors, and `Init Duration`. Keep
retention at `2` until the comparison is complete so the previous alias target
remains available. Accept the non-SnapStart candidate only when all gates pass:

- all 20 requests succeed with zero Lambda/API errors;
- health p95 is below 2 seconds; and
- health p95 regresses by no more than 1 second from the SnapStart baseline.

Changing `enable_snapstart` must be its own change and deployment. If any gate
fails, move `live` back to the retained SnapStart version. Once the candidate
passes, set `enable_snapstart = false` in production Terraform and
`TERRAFORM_TFVARS`, restore retention to `1`, and prune the old snapshot.

## Evaluation Log

On 2026-08-12, the production comparison was rejected before deploying a
non-SnapStart candidate. The required 20-concurrent baseline returned 13 HTTP
200 responses and 7 HTTP 429 `ConcurrentInvocationLimitExceeded` responses;
successful-request p95 was 1.074 seconds. The regional concurrency quota was
10, so the zero-error gate could not pass. The `live` alias remained on
SnapStart-enabled version 4 and `enable_snapstart` remains `true`. Repeat the
comparison only after the concurrency quota can support 20 simultaneous cold
starts.

## If SnapStart Is Disabled

Document the reason in the production deploy notes, usually one of:

- The selected region does not support Python SnapStart.
- The function moved to a container image.
- The function uses a SnapStart-incompatible Lambda feature.

AWS references: [SnapStart support](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html), [activation and version behavior](https://docs.aws.amazon.com/lambda/latest/dg/snapstart-activate.html).
