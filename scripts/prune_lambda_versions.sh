#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/prune_lambda_versions.sh <function-name>

Keeps the newest published Lambda versions and deletes older unaliased versions.

Environment:
  LAMBDA_VERSION_KEEP_COUNT  Number of published versions to keep. Defaults to 3.
  AWS_REGION                 AWS region passed to the AWS CLI when set.
  AWS                        AWS CLI binary. Defaults to aws.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

function_name="${1:-}"
if [[ -z "$function_name" ]]; then
  usage >&2
  exit 2
fi

aws_cli="${AWS:-aws}"
keep_count="${LAMBDA_VERSION_KEEP_COUNT:-3}"

if ! [[ "$keep_count" =~ ^[0-9]+$ ]] || [[ "$keep_count" -lt 1 ]]; then
  echo "LAMBDA_VERSION_KEEP_COUNT must be a positive integer." >&2
  exit 2
fi

region_args=()
if [[ -n "${AWS_REGION:-}" ]]; then
  region_args=(--region "$AWS_REGION")
fi

published_versions=()
while IFS= read -r version; do
  published_versions+=("$version")
done < <(
  "$aws_cli" lambda list-versions-by-function \
    --function-name "$function_name" \
    "${region_args[@]}" \
    --query 'Versions[?Version!=`$LATEST`].Version' \
    --output text |
    tr '\t' '\n' |
    grep -E '^[0-9]+$' |
    sort -nr
)

if [[ "${#published_versions[@]}" -le "$keep_count" ]]; then
  echo "Lambda $function_name has ${#published_versions[@]} published version(s); nothing to prune."
  exit 0
fi

aliased_versions=()
while IFS= read -r version; do
  aliased_versions+=("$version")
done < <(
  "$aws_cli" lambda list-aliases \
    --function-name "$function_name" \
    "${region_args[@]}" \
    --query 'Aliases[].FunctionVersion' \
    --output text |
    tr '\t' '\n' |
    grep -E '^[0-9]+$' || true
)

is_aliased_version() {
  local version="$1"
  local aliased
  for aliased in "${aliased_versions[@]}"; do
    [[ "$aliased" == "$version" ]] && return 0
  done
  return 1
}

deleted_count=0
index=0
for version in "${published_versions[@]}"; do
  index=$((index + 1))
  if [[ "$index" -le "$keep_count" ]]; then
    continue
  fi

  if is_aliased_version "$version"; then
    echo "Keeping Lambda version $version because an alias points at it."
    continue
  fi

  echo "Deleting Lambda version $version for $function_name."
  "$aws_cli" lambda delete-function \
    --function-name "$function_name" \
    --qualifier "$version" \
    "${region_args[@]}"
  deleted_count=$((deleted_count + 1))
done

echo "Pruned $deleted_count old Lambda version(s) for $function_name; kept newest $keep_count plus aliased versions."
