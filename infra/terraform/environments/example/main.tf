terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  names         = jsondecode(file("${path.module}/../../../shared/names.json"))
  app_name      = local.names.app_name
  name_prefix   = "${local.app_name}-${var.app_env}"
  function_name = "${local.names.function_name_prefix}-${var.app_env}"

  spa_bucket_name = coalesce(
    var.spa_bucket_name,
    "${local.app_name}-spa-${var.app_env}-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  )

  lambda_zip_path = (
    var.lambda_zip_path == null ? null :
    startswith(var.lambda_zip_path, "/") ? var.lambda_zip_path : abspath("${path.module}/${var.lambda_zip_path}")
  )

  lambda_environment_vars = merge(
    {
      X12_API_DEPLOYMENT_TARGET      = "lambda"
      X12_API_ORIGIN_SECRET_ENABLED  = "true"
      X12_API_ORIGIN_SECRET          = var.origin_verify_header_value
      X12_API_ORIGIN_SECRET_PREVIOUS = var.origin_verify_header_previous_value == null ? "" : var.origin_verify_header_previous_value
      X12_API_ENVIRONMENT            = var.app_env
      X12_API_SERVE_FRONTEND         = "false"
      X12_API_METRICS_ENABLED        = "true"
    },
    var.lambda_environment_vars
  )

  common_tags = merge(
    {
      Application = local.app_name
      Environment = var.app_env
      ManagedBy   = "terraform"
    },
    var.tags
  )
}

module "lambda_api" {
  source = "../../modules/lambda_api"

  function_name        = local.function_name
  zip_path             = var.lambda_zip_s3_key == null && var.lambda_image_uri == null ? local.lambda_zip_path : null
  s3_bucket            = var.lambda_zip_s3_key == null ? null : var.lambda_zip_s3_bucket
  s3_key               = var.lambda_zip_s3_key
  image_uri            = var.lambda_image_uri
  environment_vars     = local.lambda_environment_vars
  memory_mb            = var.memory_mb
  timeout_s            = var.timeout_s
  lambda_architecture  = var.lambda_architecture
  enable_snapstart     = var.enable_snapstart
  reserved_concurrency = var.reserved_concurrency
  log_retention_days   = var.log_retention_days
  tags                 = local.common_tags
}

module "s3_spa" {
  source = "../../modules/s3_spa"

  bucket_name   = local.spa_bucket_name
  kms_key_arn   = var.kms_key_arn
  force_destroy = var.force_destroy_spa_bucket
  tags          = local.common_tags
}

module "waf" {
  count  = var.enable_waf ? 1 : 0
  source = "../../modules/waf"

  name_prefix = local.name_prefix
  tags        = local.common_tags
}

module "cloudfront_distribution" {
  source = "../../modules/cloudfront_distribution"

  name_prefix                = local.name_prefix
  spa_bucket_regional_domain = module.s3_spa.bucket_regional_domain_name
  lambda_function_url_domain = module.lambda_api.function_url_domain
  origin_verify_header_value = var.origin_verify_header_value
  price_class                = var.price_class
  enable_waf                 = var.enable_waf
  waf_web_acl_arn            = var.enable_waf ? module.waf[0].web_acl_arn : null
  tags                       = local.common_tags
}

data "aws_iam_policy_document" "spa_oac_read" {
  statement {
    sid     = "AllowCloudFrontOACRead"
    effect  = "Allow"
    actions = ["s3:GetObject"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    resources = ["${module.s3_spa.bucket_arn}/*"]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [module.cloudfront_distribution.distribution_arn]
    }
  }
}

resource "aws_s3_bucket_policy" "spa_oac_read" {
  bucket = local.spa_bucket_name
  policy = data.aws_iam_policy_document.spa_oac_read.json

  depends_on = [module.s3_spa]
}

module "observability" {
  source = "../../modules/observability"

  function_name       = local.function_name
  alarm_sns_topic_arn = var.alarm_sns_topic_arn
  tags                = local.common_tags

  depends_on = [module.lambda_api]
}
