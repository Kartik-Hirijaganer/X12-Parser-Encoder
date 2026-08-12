#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
test_dir="$(mktemp -d)"
trap 'rm -rf "${test_dir}"' EXIT

delete_log="${test_dir}/deleted-versions"
fake_aws="${test_dir}/aws"

cat > "${fake_aws}" <<'FAKE_AWS'
#!/usr/bin/env bash
set -euo pipefail

case "${1:-} ${2:-}" in
  "lambda list-versions-by-function")
    printf '$LATEST\t5\t4\t3\t2\n'
    ;;
  "lambda list-aliases")
    printf '4\n'
    ;;
  "lambda delete-function")
    while (($#)); do
      if [[ "$1" == "--qualifier" ]]; then
        printf '%s\n' "$2" >> "${FAKE_AWS_DELETE_LOG}"
        exit 0
      fi
      shift
    done
    echo "delete-function did not receive --qualifier" >&2
    exit 1
    ;;
  *)
    printf 'Unexpected fake AWS call: %q ' "$@" >&2
    echo >&2
    exit 1
    ;;
esac
FAKE_AWS
chmod +x "${fake_aws}"

FAKE_AWS_DELETE_LOG="${delete_log}" AWS="${fake_aws}" \
  bash "${repo_root}/scripts/prune_lambda_versions.sh" x12-parser-encoder-api-production

deleted_versions="$(tr '\n' ' ' < "${delete_log}" | sed 's/ $//')"
[[ "${deleted_versions}" == "3 2" ]] || {
  echo "Expected versions 3 and 2 to be deleted; got: ${deleted_versions}" >&2
  exit 1
}

for invalid_keep_count in 0 nope; do
  invalid_output="${test_dir}/invalid-${invalid_keep_count}.log"
  set +e
  FAKE_AWS_DELETE_LOG="${delete_log}" AWS="${fake_aws}" \
    LAMBDA_VERSION_KEEP_COUNT="${invalid_keep_count}" \
    bash "${repo_root}/scripts/prune_lambda_versions.sh" \
      x12-parser-encoder-api-production >"${invalid_output}" 2>&1
  invalid_status=$?
  set -e

  [[ "${invalid_status}" -eq 2 ]] || {
    echo "Expected invalid keep count ${invalid_keep_count} to exit 2; got ${invalid_status}." >&2
    exit 1
  }
  grep -q "must be a positive integer" "${invalid_output}" || {
    echo "Expected validation error for keep count ${invalid_keep_count}." >&2
    exit 1
  }
done

echo "Pruning test passed: newest version 5 and aliased version 4 were preserved; versions 3 and 2 were deleted; invalid keep counts were rejected."
