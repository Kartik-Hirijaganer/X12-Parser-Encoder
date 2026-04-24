#!/usr/bin/env bash

set -euo pipefail

LAMBDA_ARCHITECTURE="${LAMBDA_ARCHITECTURE:-x86_64}"
LAMBDA_BUILD_IMAGE="${LAMBDA_BUILD_IMAGE:-public.ecr.aws/lambda/python:3.12}"
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-315532800}"
export PIP_ROOT_USER_ACTION=ignore

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${REPO_ROOT}/build"
PACKAGE_DIR="${BUILD_DIR}/lambda"
WHEEL_DIR="${BUILD_DIR}/lambda-wheels"
ZIP_PATH="${BUILD_DIR}/lambda.zip"
SHA_PATH="${ZIP_PATH}.sha256"

case "${LAMBDA_ARCHITECTURE}" in
  x86_64)
    DOCKER_PLATFORM="linux/amd64"
    ;;
  arm64)
    DOCKER_PLATFORM="linux/arm64"
    ;;
  *)
    echo "LAMBDA_ARCHITECTURE must be x86_64 or arm64; got ${LAMBDA_ARCHITECTURE}." >&2
    exit 1
    ;;
esac

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Missing required command: ${command_name}" >&2
    exit 1
  fi
}

if [[ "${LAMBDA_PACKAGE_IN_DOCKER:-0}" != "1" ]]; then
  require_command docker
  docker run --rm \
    --platform "${DOCKER_PLATFORM}" \
    --entrypoint /bin/bash \
    -e LAMBDA_PACKAGE_IN_DOCKER=1 \
    -e LAMBDA_ARCHITECTURE="${LAMBDA_ARCHITECTURE}" \
    -e SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}" \
    -e HOST_UID="$(id -u)" \
    -e HOST_GID="$(id -g)" \
    -v "${REPO_ROOT}:/workspace" \
    -w /workspace \
    "${LAMBDA_BUILD_IMAGE}" \
    -lc "scripts/package_lambda.sh"
  exit 0
fi

require_command python

if ! command -v zip >/dev/null 2>&1; then
  if command -v dnf >/dev/null 2>&1; then
    dnf install -y zip findutils >/dev/null
  elif command -v microdnf >/dev/null 2>&1; then
    microdnf install -y zip findutils >/dev/null
  else
    echo "Missing required command: zip" >&2
    exit 1
  fi
fi

rm -rf "${PACKAGE_DIR}" "${WHEEL_DIR}" "${ZIP_PATH}" "${SHA_PATH}"
mkdir -p "${PACKAGE_DIR}" "${WHEEL_DIR}"

python -m pip install --upgrade pip build wheel >/dev/null
python -m pip wheel --no-cache-dir --wheel-dir "${WHEEL_DIR}" "${REPO_ROOT}/packages/x12-edi-tools" >/dev/null
python -m pip wheel --no-cache-dir --wheel-dir "${WHEEL_DIR}" "${REPO_ROOT}/apps/api" >/dev/null

LIB_WHEEL="$(find "${WHEEL_DIR}" -maxdepth 1 -name 'x12_edi_tools-*.whl' | sort | tail -n 1)"
API_WHEEL="$(find "${WHEEL_DIR}" -maxdepth 1 -name 'eligibility_workbench_api-*.whl' | sort | tail -n 1)"

if [[ -z "${LIB_WHEEL}" || -z "${API_WHEEL}" ]]; then
  echo "Expected x12-edi-tools and API wheels were not produced." >&2
  exit 1
fi

python -m pip install \
  --target "${PACKAGE_DIR}" \
  --no-cache-dir \
  --no-compile \
  "${LIB_WHEEL}" \
  "${API_WHEEL}[lambda]" \
  >/dev/null

cp -R "${REPO_ROOT}/apps/api/templates" "${PACKAGE_DIR}/templates"
cp "${REPO_ROOT}/VERSION" "${PACKAGE_DIR}/VERSION"

find "${PACKAGE_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "${PACKAGE_DIR}" -type f -name "*.pyc" -delete
find "${PACKAGE_DIR}" -type f -path "*.dist-info/RECORD" -delete

python - "${PACKAGE_DIR}" "${SOURCE_DATE_EPOCH}" <<'PY'
from __future__ import annotations

import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
timestamp = int(sys.argv[2])

for path in sorted(root.rglob("*")):
    try:
        os.utime(path, (timestamp, timestamp), follow_symlinks=False)
    except OSError:
        pass
PY

(
  cd "${PACKAGE_DIR}"
  find . \( -type f -o -type l \) | LC_ALL=C sort | sed "s#^\./##" | zip -X -q "${ZIP_PATH}" -@
)

ZIP_BYTES="$(stat -c "%s" "${ZIP_PATH}")"
UNZIPPED_BYTES="$(du -sb "${PACKAGE_DIR}" | cut -f1)"

if (( ZIP_BYTES > 50 * 1024 * 1024 )); then
  echo "Warning: zipped Lambda artifact exceeds 50 MB; S3 deployment is required." >&2
fi

if (( UNZIPPED_BYTES > 200 * 1024 * 1024 )); then
  echo "Warning: unzipped Lambda artifact exceeds 200 MB." >&2
fi

if (( UNZIPPED_BYTES > 240 * 1024 * 1024 )); then
  echo "Unzipped Lambda artifact exceeds 240 MB; switch to the container-image fallback before deploying." >&2
  exit 1
fi

sha256sum "${ZIP_PATH}" | tee "${SHA_PATH}"
printf "Lambda artifact: %s\n" "${ZIP_PATH}"
printf "Zipped bytes: %s\n" "${ZIP_BYTES}"
printf "Unzipped bytes: %s\n" "${UNZIPPED_BYTES}"

if [[ -n "${HOST_UID:-}" && -n "${HOST_GID:-}" ]]; then
  chown -R "${HOST_UID}:${HOST_GID}" "${BUILD_DIR}"
fi
