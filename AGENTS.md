# AGENTS.md

Project guidance for Codex and other OpenAI-style coding agents working in this repository.

## Canonical AWS Account

- The canonical AWS account for this project is `970385384114`.
- Do not infer the deployment account from the currently active default AWS CLI profile.
- Before any AWS bootstrap, Terraform, GitHub Actions deploy setup, or production deploy, verify the selected credentials:

```bash
aws sts get-caller-identity --query Account --output text
```

- Proceed with production deployment work only when the verified account is `970385384114`.
- GitHub Actions deploy configuration for this project should use repository variable `AWS_ACCOUNT_ID=970385384114`.
- The Terraform/GitHub Actions deploy path defaults to `AWS_REGION=us-east-2` unless the user explicitly changes it.

## Project Notes

- Use `CLAUDE.md` as the fuller project guide for commands, architecture, conventions, and safety rules.
- Treat upload data and fixture data as sensitive healthcare-adjacent data; do not add real patient data or log raw X12 payloads.
