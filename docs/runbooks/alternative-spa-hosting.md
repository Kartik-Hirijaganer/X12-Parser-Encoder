# Alternative SPA Hosting

You should be done in < 5 min after the AWS API stack is deployed.

This is only for pure-demo forks that will never process real PHI. It is not supported for PHI workloads unless the alternate frontend host is covered by the operator's own BAA and security controls.

## Build The SPA

```bash
cd apps/web
npm ci
VITE_API_BASE_URL="https://<cloudfront-domain>/api/v1" npm run build
```

Deploy `apps/web/dist` to the static host of your choice.

## Required API URL

Use the CloudFront API URL:

```text
https://<distribution>.cloudfront.net/api/v1
```

or the custom-domain equivalent:

```text
https://x12.example.com/api/v1
```

Do not point the browser at the raw Lambda Function URL while origin-secret middleware is enabled. Browsers cannot supply the CloudFront-only `X-Origin-Verify` header, so direct calls return 403.

## Verify

Open the hosted SPA, generate a synthetic 270, then parse a synthetic 271. DevTools Network should show API calls going to the CloudFront hostname, not the raw Function URL.
