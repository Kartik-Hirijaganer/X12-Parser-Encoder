#!/usr/bin/env bash

set -euo pipefail

APP_NAME="${APP_NAME:-x12-parser-encoder}"
AWS_REGION="${AWS_REGION:-us-east-2}"
FORCE_DESTROY="${FORCE_DESTROY:-false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BOOTSTRAP_DIR="${REPO_ROOT}/infra/terraform/bootstrap"

if ! command -v terraform >/dev/null 2>&1; then
  echo "Missing required command: terraform" >&2
  exit 1
fi

terraform -chdir="${BOOTSTRAP_DIR}" init
terraform -chdir="${BOOTSTRAP_DIR}" apply -auto-approve \
  -var "app_name=${APP_NAME}" \
  -var "aws_region=${AWS_REGION}" \
  -var "force_destroy=${FORCE_DESTROY}"

TFSTATE_BUCKET="$(terraform -chdir="${BOOTSTRAP_DIR}" output -raw tfstate_bucket)"
LOCK_TABLE="$(terraform -chdir="${BOOTSTRAP_DIR}" output -raw lock_table)"

cat <<EOF

Terraform backend is ready.

bucket         = "${TFSTATE_BUCKET}"
region         = "${AWS_REGION}"
dynamodb_table = "${LOCK_TABLE}"
encrypt        = true

Set key = "<environment>/terraform.tfstate" in each environment backend config.
EOF
