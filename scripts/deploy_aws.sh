#!/usr/bin/env bash

set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-2}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-306980977180}"
APP_NAME="${APP_NAME:-x12-parser-encoder}"
S3_BUCKET="${S3_BUCKET:-${APP_NAME}-web-${AWS_ACCOUNT_ID}-${AWS_REGION}}"
ECR_REPOSITORY="${ECR_REPOSITORY:-${APP_NAME}-api}"
APP_RUNNER_SERVICE="${APP_RUNNER_SERVICE:-${APP_NAME}-api}"
APP_RUNNER_ECR_ACCESS_ROLE="${APP_RUNNER_ECR_ACCESS_ROLE:-${APP_NAME}-apprunner-ecr-access}"
API_IMAGE_TAG="${API_IMAGE_TAG:-$(date -u +%Y%m%d%H%M%S)-$(git rev-parse --short HEAD 2>/dev/null || echo local)}"
DOCKER_PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"
RATE_LIMIT_ENABLED="${RATE_LIMIT_ENABLED:-true}"
REQUESTS_PER_MINUTE="${REQUESTS_PER_MINUTE:-60}"
CONCURRENT_UPLOAD_LIMIT="${CONCURRENT_UPLOAD_LIMIT:-5}"
AUTH_BOUNDARY_ENABLED="${AUTH_BOUNDARY_ENABLED:-false}"
EXTRA_CORS_ALLOWED_ORIGINS="${EXTRA_CORS_ALLOWED_ORIGINS:-}"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
API_IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:${API_IMAGE_TAG}"
S3_WEBSITE_HOST="${S3_BUCKET}.s3-website.${AWS_REGION}.amazonaws.com"
S3_WEBSITE_URL="http://${S3_WEBSITE_HOST}"
APP_RUNNER_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${APP_RUNNER_ECR_ACCESS_ROLE}"
CLOUDFRONT_COMMENT="${APP_NAME} web"
CLOUDFRONT_DISTRIBUTION_ID=""
CLOUDFRONT_DOMAIN=""
CLOUDFRONT_URL=""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TEMP_DIR}"' EXIT

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Missing required command: ${command_name}" >&2
    exit 1
  fi
}

log_step() {
  printf '\n==> %s\n' "$1" >&2
}

assert_aws_account() {
  local current_account
  current_account="$(aws sts get-caller-identity --query Account --output text)"
  if [[ "${current_account}" != "${AWS_ACCOUNT_ID}" ]]; then
    echo "AWS account mismatch. Expected ${AWS_ACCOUNT_ID}, got ${current_account}." >&2
    exit 1
  fi
}

ensure_s3_bucket() {
  if ! aws s3api head-bucket --bucket "${S3_BUCKET}" >/dev/null 2>&1; then
    log_step "Creating S3 bucket ${S3_BUCKET}"
    if [[ "${AWS_REGION}" == "us-east-1" ]]; then
      aws s3api create-bucket \
        --bucket "${S3_BUCKET}" \
        --region "${AWS_REGION}" \
        >/dev/null
    else
      aws s3api create-bucket \
        --bucket "${S3_BUCKET}" \
        --region "${AWS_REGION}" \
        --create-bucket-configuration "LocationConstraint=${AWS_REGION}" \
        >/dev/null
    fi
  fi

  aws s3api put-bucket-encryption \
    --bucket "${S3_BUCKET}" \
    --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' \
    >/dev/null

  aws s3api put-public-access-block \
    --bucket "${S3_BUCKET}" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false" \
    >/dev/null

  aws s3api put-bucket-website \
    --bucket "${S3_BUCKET}" \
    --website-configuration '{"IndexDocument":{"Suffix":"index.html"},"ErrorDocument":{"Key":"index.html"}}' \
    >/dev/null

  cat > "${TEMP_DIR}/bucket-policy.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadForWebsite",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${S3_BUCKET}/*"
    }
  ]
}
EOF

  aws s3api put-bucket-policy \
    --bucket "${S3_BUCKET}" \
    --policy "file://${TEMP_DIR}/bucket-policy.json" \
    >/dev/null
}

ensure_ecr_repository() {
  if ! aws ecr describe-repositories \
    --region "${AWS_REGION}" \
    --registry-id "${AWS_ACCOUNT_ID}" \
    --repository-names "${ECR_REPOSITORY}" \
    >/dev/null 2>&1; then
    log_step "Creating ECR repository ${ECR_REPOSITORY}"
    aws ecr create-repository \
      --region "${AWS_REGION}" \
      --repository-name "${ECR_REPOSITORY}" \
      --image-scanning-configuration scanOnPush=true \
      >/dev/null
  fi
}

ensure_apprunner_access_role() {
  if aws iam get-role --role-name "${APP_RUNNER_ECR_ACCESS_ROLE}" >/dev/null 2>&1; then
    return
  fi

  log_step "Creating App Runner ECR access role ${APP_RUNNER_ECR_ACCESS_ROLE}"

  cat > "${TEMP_DIR}/apprunner-trust-policy.json" <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "build.apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

  aws iam create-role \
    --role-name "${APP_RUNNER_ECR_ACCESS_ROLE}" \
    --assume-role-policy-document "file://${TEMP_DIR}/apprunner-trust-policy.json" \
    >/dev/null

  aws iam attach-role-policy \
    --role-name "${APP_RUNNER_ECR_ACCESS_ROLE}" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess" \
    >/dev/null

  # IAM propagation can lag slightly after role creation.
  sleep 10
}

login_to_ecr() {
  aws ecr get-login-password --region "${AWS_REGION}" \
    | docker login --username AWS --password-stdin "${ECR_REGISTRY}" >/dev/null
}

build_and_push_api_image() {
  log_step "Building and pushing API image ${API_IMAGE_URI}"
  docker build \
    --platform "${DOCKER_PLATFORM}" \
    -f "${REPO_ROOT}/docker/Dockerfile" \
    -t "${API_IMAGE_URI}" \
    "${REPO_ROOT}"
  docker push "${API_IMAGE_URI}" >/dev/null
}

compose_cors_origins() {
  local origins="${S3_WEBSITE_URL}"
  if [[ -n "${CLOUDFRONT_URL}" ]]; then
    origins+=",${CLOUDFRONT_URL}"
  fi
  if [[ -n "${EXTRA_CORS_ALLOWED_ORIGINS}" ]]; then
    origins+=",${EXTRA_CORS_ALLOWED_ORIGINS}"
  fi
  printf '%s' "${origins}"
}

ensure_cloudfront_distribution() {
  local existing_id
  existing_id="$(
    aws cloudfront list-distributions \
      --query "DistributionList.Items[?Origins.Items[?DomainName=='${S3_WEBSITE_HOST}']].Id | [0]" \
      --output text
  )"

  if [[ -n "${existing_id}" && "${existing_id}" != "None" ]]; then
    CLOUDFRONT_DISTRIBUTION_ID="${existing_id}"
    CLOUDFRONT_DOMAIN="$(
      aws cloudfront get-distribution \
        --id "${existing_id}" \
        --query 'Distribution.DomainName' \
        --output text
    )"
    CLOUDFRONT_URL="https://${CLOUDFRONT_DOMAIN}"
    log_step "Reusing CloudFront distribution ${CLOUDFRONT_DISTRIBUTION_ID} (${CLOUDFRONT_URL})"
    return
  fi

  log_step "Creating CloudFront distribution for ${S3_WEBSITE_HOST}"
  cat > "${TEMP_DIR}/cloudfront-config.json" <<EOF
{
  "CallerReference": "${APP_NAME}-$(date +%s)",
  "Comment": "${CLOUDFRONT_COMMENT}",
  "Enabled": true,
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "s3-website-origin",
        "DomainName": "${S3_WEBSITE_HOST}",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only",
          "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]},
          "OriginReadTimeout": 30,
          "OriginKeepaliveTimeout": 5
        },
        "CustomHeaders": {"Quantity": 0},
        "OriginPath": "",
        "ConnectionAttempts": 3,
        "ConnectionTimeout": 10
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "s3-website-origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}
    },
    "Compress": true,
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6"
  },
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      {"ErrorCode": 403, "ResponsePagePath": "/index.html", "ResponseCode": "200", "ErrorCachingMinTTL": 0},
      {"ErrorCode": 404, "ResponsePagePath": "/index.html", "ResponseCode": "200", "ErrorCachingMinTTL": 0}
    ]
  },
  "PriceClass": "PriceClass_100",
  "ViewerCertificate": {"CloudFrontDefaultCertificate": true},
  "HttpVersion": "http2",
  "IsIPV6Enabled": true
}
EOF

  CLOUDFRONT_DISTRIBUTION_ID="$(
    aws cloudfront create-distribution \
      --distribution-config "file://${TEMP_DIR}/cloudfront-config.json" \
      --query 'Distribution.Id' \
      --output text
  )"
  CLOUDFRONT_DOMAIN="$(
    aws cloudfront get-distribution \
      --id "${CLOUDFRONT_DISTRIBUTION_ID}" \
      --query 'Distribution.DomainName' \
      --output text
  )"
  CLOUDFRONT_URL="https://${CLOUDFRONT_DOMAIN}"
}

invalidate_cloudfront() {
  if [[ -z "${CLOUDFRONT_DISTRIBUTION_ID}" ]]; then
    return
  fi
  log_step "Invalidating CloudFront cache (${CLOUDFRONT_DISTRIBUTION_ID})"
  aws cloudfront create-invalidation \
    --distribution-id "${CLOUDFRONT_DISTRIBUTION_ID}" \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text >/dev/null
}

write_source_configuration() {
  local cors_allowed_origins="$1"

  cat > "${TEMP_DIR}/apprunner-source-configuration.json" <<EOF
{
  "ImageRepository": {
    "ImageIdentifier": "${API_IMAGE_URI}",
    "ImageRepositoryType": "ECR",
    "ImageConfiguration": {
      "Port": "8000",
      "RuntimeEnvironmentVariables": {
        "X12_API_ENVIRONMENT": "production",
        "X12_API_SERVE_FRONTEND": "false",
        "X12_API_RATE_LIMIT_ENABLED": "${RATE_LIMIT_ENABLED}",
        "X12_API_REQUESTS_PER_MINUTE": "${REQUESTS_PER_MINUTE}",
        "X12_API_CONCURRENT_UPLOAD_LIMIT": "${CONCURRENT_UPLOAD_LIMIT}",
        "X12_API_AUTH_BOUNDARY_ENABLED": "${AUTH_BOUNDARY_ENABLED}",
        "X12_API_CORS_ALLOWED_ORIGINS": "${cors_allowed_origins}"
      }
    }
  },
  "AutoDeploymentsEnabled": false,
  "AuthenticationConfiguration": {
    "AccessRoleArn": "${APP_RUNNER_ROLE_ARN}"
  }
}
EOF
}

service_arn_for_name() {
  aws apprunner list-services \
    --region "${AWS_REGION}" \
    --query "ServiceSummaryList[?ServiceName=='${APP_RUNNER_SERVICE}'].ServiceArn | [0]" \
    --output text
}

deploy_apprunner_service() {
  local cors_allowed_origins="$1"
  local existing_service_arn

  write_source_configuration "${cors_allowed_origins}"
  existing_service_arn="$(service_arn_for_name)"

  if [[ -z "${existing_service_arn}" || "${existing_service_arn}" == "None" ]]; then
    log_step "Creating App Runner service ${APP_RUNNER_SERVICE}"
    aws apprunner create-service \
      --region "${AWS_REGION}" \
      --service-name "${APP_RUNNER_SERVICE}" \
      --source-configuration "file://${TEMP_DIR}/apprunner-source-configuration.json" \
      --query 'Service.ServiceArn' \
      --output text
    return
  fi

  log_step "Updating App Runner service ${APP_RUNNER_SERVICE}"
  aws apprunner update-service \
    --region "${AWS_REGION}" \
    --service-arn "${existing_service_arn}" \
    --source-configuration "file://${TEMP_DIR}/apprunner-source-configuration.json" \
    --query 'Service.ServiceArn' \
    --output text
}

wait_for_apprunner_service() {
  local service_arn="$1"
  local attempt status

  for attempt in $(seq 1 90); do
    status="$(
      aws apprunner describe-service \
        --region "${AWS_REGION}" \
        --service-arn "${service_arn}" \
        --query 'Service.Status' \
        --output text
    )"

    case "${status}" in
      RUNNING)
        return
        ;;
      CREATE_FAILED|DELETE_FAILED|PAUSE_FAILED|RESUME_FAILED|UPDATE_FAILED)
        echo "App Runner service entered terminal failure state: ${status}" >&2
        exit 1
        ;;
      *)
        sleep 10
        ;;
    esac
  done

  echo "Timed out waiting for App Runner service to reach RUNNING." >&2
  exit 1
}

apprunner_service_url() {
  local service_arn="$1"
  aws apprunner describe-service \
    --region "${AWS_REGION}" \
    --service-arn "${service_arn}" \
    --query 'Service.ServiceUrl' \
    --output text
}

build_frontend() {
  local api_base_url="$1"

  log_step "Building frontend with API base URL ${api_base_url}"
  (
    cd "${REPO_ROOT}/apps/web"
    npm ci
    VITE_API_BASE_URL="${api_base_url}" npm run build
  )
}

publish_frontend() {
  log_step "Publishing frontend to s3://${S3_BUCKET}"
  aws s3 sync "${REPO_ROOT}/apps/web/dist" "s3://${S3_BUCKET}" \
    --delete \
    --exclude "index.html" \
    >/dev/null

  aws s3 cp "${REPO_ROOT}/apps/web/dist/index.html" "s3://${S3_BUCKET}/index.html" \
    --content-type "text/html; charset=utf-8" \
    --cache-control "no-cache, no-store, must-revalidate" \
    >/dev/null
}

verify_api_health() {
  local api_base_url="$1"
  curl --fail --silent --show-error "${api_base_url}/health" >/dev/null
}

main() {
  require_command aws
  require_command docker
  require_command npm
  require_command curl

  log_step "Validating AWS account"
  assert_aws_account

  log_step "Preparing AWS resources in ${AWS_REGION}"
  ensure_s3_bucket
  ensure_cloudfront_distribution
  ensure_ecr_repository
  ensure_apprunner_access_role
  login_to_ecr
  build_and_push_api_image

  local cors_allowed_origins service_arn service_url api_base_url
  cors_allowed_origins="$(compose_cors_origins)"
  service_arn="$(deploy_apprunner_service "${cors_allowed_origins}")"

  log_step "Waiting for App Runner service deployment"
  wait_for_apprunner_service "${service_arn}"

  service_url="$(apprunner_service_url "${service_arn}")"
  api_base_url="https://${service_url}/api/v1"

  log_step "Verifying API health"
  verify_api_health "${api_base_url}"

  build_frontend "${api_base_url}"
  publish_frontend
  invalidate_cloudfront

  printf '\nDeployment complete.\n'
  printf 'Frontend (CloudFront): %s\n' "${CLOUDFRONT_URL}"
  printf 'Frontend (S3 direct):  %s\n' "${S3_WEBSITE_URL}"
  printf 'API: %s\n' "${api_base_url}"
  printf 'S3 bucket: %s\n' "${S3_BUCKET}"
  printf 'App Runner service: %s\n' "${APP_RUNNER_SERVICE}"
  printf 'CloudFront distribution: %s\n\n' "${CLOUDFRONT_DISTRIBUTION_ID}"
}

main "$@"
