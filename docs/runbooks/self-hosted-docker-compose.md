# Self-Hosted Docker Compose

You should be done in < 5 min for a local or lab-only deployment.

This path is not the default production path and is not PHI-supported by this repository. Operators who process real PHI outside the AWS serverless stack own their hosting compliance, BAA coverage, logging, backups, TLS, and network controls.

## Run Locally

```bash
docker compose up --build
```

Open:

- Web: `http://localhost:5173`
- API: `http://localhost:8000`

## Smoke Test

```bash
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/api/v1/health
```

## Stop

```bash
docker compose down --remove-orphans
```

## Production Notes

- Put TLS termination, request-size limits, and access logs in front of the compose stack.
- Keep `X12_API_DEPLOYMENT_TARGET=container`.
- Do not expose `/metrics` publicly.
- Do not write uploaded files, generated X12, filenames, or member identifiers to persistent logs.
