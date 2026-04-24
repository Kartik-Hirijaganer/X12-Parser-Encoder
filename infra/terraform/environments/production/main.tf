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

provider "aws" {
  alias  = "global"
  region = "us-east-1"
}

data "aws_caller_identity" "current" {}

locals {
  names         = jsondecode(file("${path.module}/../../../shared/names.json"))
  app_name      = local.names.app_name
  name_prefix   = "${local.app_name}-${var.app_env}"
  function_name = "${local.names.function_name_prefix}-${var.app_env}"

  tfstate_bucket_name = "${local.app_name}-tfstate-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  lock_table_name     = "${local.app_name}-tflocks"
  deploy_role_name    = "${local.app_name}-deploy-${var.app_env}"
  artifact_prefix     = "lambda-artifacts/${var.app_env}"

  github_oidc_subjects = (
    var.github_oidc_subjects == null ?
    ["repo:${var.github_repository}:environment:${var.app_env}"] :
    var.github_oidc_subjects
  )

  github_oidc_provider_arn = (
    var.manage_github_oidc_provider ?
    aws_iam_openid_connect_provider.github[0].arn :
    coalesce(
      var.github_oidc_provider_arn,
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
    )
  )
  route53_hosted_zone_arn = (
    try(trimspace(var.hosted_zone_id), "") == "" ?
    "arn:aws:route53:::hostedzone/*" :
    "arn:aws:route53:::hostedzone/${var.hosted_zone_id}"
  )
  waf_web_acl_arn = "arn:aws:wafv2:us-east-1:${data.aws_caller_identity.current.account_id}:global/webacl/${local.name_prefix}-web-acl/*"
  cloudfront_support_resource_arns = [
    "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:function/${local.name_prefix}-spa-rewrite",
    "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:origin-access-control/*",
    "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:response-headers-policy/*",
  ]
  acm_certificate_policy_arn = "arn:aws:acm:us-east-1:${data.aws_caller_identity.current.account_id}:certificate/*"

  spa_bucket_name = coalesce(
    var.spa_bucket_name,
    "${local.app_name}-spa-${var.app_env}-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  )
  custom_domain_enabled         = var.custom_domain != null && trimspace(var.custom_domain) != ""
  route53_custom_domain_enabled = local.custom_domain_enabled && lower(var.dns_provider) == "route53"

  lambda_zip_path = (
    var.lambda_zip_path == null ? null :
    startswith(var.lambda_zip_path, "/") ? var.lambda_zip_path : abspath("${path.module}/${var.lambda_zip_path}")
  )

  lambda_contract_environment_values = [
    "lambda",
    "true",
    var.origin_verify_header_value,
    var.origin_verify_header_previous_value == null ? "" : var.origin_verify_header_previous_value,
    var.app_env,
    "false",
    "true",
  ]

  lambda_environment_vars = merge(
    zipmap(local.names.env_var_names, local.lambda_contract_environment_values),
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

data "tls_certificate" "github_actions" {
  count = var.manage_github_oidc_provider ? 1 : 0
  url   = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  count = var.manage_github_oidc_provider ? 1 : 0

  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    data.tls_certificate.github_actions[0].certificates[
      length(data.tls_certificate.github_actions[0].certificates) - 1
    ].sha1_fingerprint
  ]

  tags = local.common_tags
}

data "aws_iam_policy_document" "deploy_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = [local.github_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.github_oidc_subjects
    }
  }
}

resource "aws_iam_role" "deploy" {
  name               = local.deploy_role_name
  assume_role_policy = data.aws_iam_policy_document.deploy_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "deploy" {
  statement {
    sid       = "ReadCallerIdentity"
    effect    = "Allow"
    actions   = ["sts:GetCallerIdentity"]
    resources = ["*"]
  }

  statement {
    sid    = "UseTerraformState"
    effect = "Allow"
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]
    resources = ["arn:aws:s3:::${local.tfstate_bucket_name}"]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        "${var.app_env}/*",
        "${local.artifact_prefix}/*",
      ]
    }
  }

  statement {
    sid    = "ReadWriteTerraformStateAndArtifacts"
    effect = "Allow"
    actions = [
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = [
      "arn:aws:s3:::${local.tfstate_bucket_name}/${var.app_env}/*",
      "arn:aws:s3:::${local.tfstate_bucket_name}/${local.artifact_prefix}/*",
    ]
  }

  statement {
    sid    = "UseTerraformLocks"
    effect = "Allow"
    actions = [
      "dynamodb:DeleteItem",
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
    ]
    resources = ["arn:aws:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${local.lock_table_name}"]
  }

  statement {
    sid    = "ManageSpaBucket"
    effect = "Allow"
    actions = [
      "s3:CreateBucket",
      "s3:DeleteBucket",
      "s3:DeleteBucketPolicy",
      "s3:GetAccelerateConfiguration",
      "s3:GetBucketAcl",
      "s3:GetBucketCORS",
      "s3:GetBucketLocation",
      "s3:GetBucketLogging",
      "s3:GetBucketObjectLockConfiguration",
      "s3:GetBucketOwnershipControls",
      "s3:GetBucketPolicy",
      "s3:GetBucketPublicAccessBlock",
      "s3:GetBucketRequestPayment",
      "s3:GetBucketTagging",
      "s3:GetBucketVersioning",
      "s3:GetBucketWebsite",
      "s3:GetEncryptionConfiguration",
      "s3:GetLifecycleConfiguration",
      "s3:GetReplicationConfiguration",
      "s3:ListBucket",
      "s3:PutBucketOwnershipControls",
      "s3:PutBucketPolicy",
      "s3:PutBucketPublicAccessBlock",
      "s3:PutBucketTagging",
      "s3:PutBucketVersioning",
      "s3:PutEncryptionConfiguration",
    ]
    resources = ["arn:aws:s3:::${local.spa_bucket_name}"]
  }

  statement {
    sid    = "SyncSpaObjects"
    effect = "Allow"
    actions = [
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = ["arn:aws:s3:::${local.spa_bucket_name}/*"]
  }

  statement {
    sid    = "ManageLambdaExecutionAndDeployRoles"
    effect = "Allow"
    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:DeleteRolePolicy",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListRolePolicies",
      "iam:PassRole",
      "iam:PutRolePolicy",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.deploy_role_name}",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.function_name}-exec",
    ]
  }

  statement {
    sid    = "ManageGitHubOidcProviderWhenEnabled"
    effect = "Allow"
    actions = [
      "iam:AddClientIDToOpenIDConnectProvider",
      "iam:CreateOpenIDConnectProvider",
      "iam:DeleteOpenIDConnectProvider",
      "iam:GetOpenIDConnectProvider",
      "iam:RemoveClientIDFromOpenIDConnectProvider",
      "iam:TagOpenIDConnectProvider",
      "iam:UntagOpenIDConnectProvider",
      "iam:UpdateOpenIDConnectProviderThumbprint",
    ]
    resources = [local.github_oidc_provider_arn]
  }

  statement {
    sid    = "ManageLambdaApi"
    effect = "Allow"
    actions = [
      "lambda:AddPermission",
      "lambda:CreateAlias",
      "lambda:CreateFunction",
      "lambda:CreateFunctionUrlConfig",
      "lambda:DeleteAlias",
      "lambda:DeleteFunction",
      "lambda:DeleteFunctionConcurrency",
      "lambda:DeleteFunctionUrlConfig",
      "lambda:GetAlias",
      "lambda:GetFunction",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:GetFunctionConcurrency",
      "lambda:GetFunctionConfiguration",
      "lambda:GetFunctionUrlConfig",
      "lambda:GetPolicy",
      "lambda:ListAliases",
      "lambda:ListVersionsByFunction",
      "lambda:PublishVersion",
      "lambda:PutFunctionConcurrency",
      "lambda:RemovePermission",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:UpdateAlias",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
      "lambda:UpdateFunctionUrlConfig",
    ]
    resources = [
      "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.function_name}",
      "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.function_name}:*",
    ]
  }

  statement {
    sid    = "ManageLambdaLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:DeleteMetricFilter",
      "logs:DescribeLogGroups",
      "logs:DescribeMetricFilters",
      "logs:ListTagsForResource",
      "logs:PutMetricFilter",
      "logs:PutRetentionPolicy",
      "logs:TagResource",
      "logs:UntagResource",
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.function_name}",
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.function_name}:*",
    ]
  }

  statement {
    sid    = "ReadLambdaLogGroups"
    effect = "Allow"
    actions = [
      "logs:DescribeLogGroups",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageLambdaAlarms"
    effect = "Allow"
    actions = [
      "cloudwatch:DeleteAlarms",
      "cloudwatch:DescribeAlarms",
      "cloudwatch:ListTagsForResource",
      "cloudwatch:PutMetricAlarm",
      "cloudwatch:TagResource",
      "cloudwatch:UntagResource",
    ]
    resources = ["arn:aws:cloudwatch:${var.aws_region}:${data.aws_caller_identity.current.account_id}:alarm:${local.function_name}-*"]
  }

  statement {
    sid       = "ReadLambdaAlarms"
    effect    = "Allow"
    actions   = ["cloudwatch:DescribeAlarms"]
    resources = ["*"]
  }

  statement {
    sid    = "ManageCloudFrontWaf"
    effect = "Allow"
    actions = [
      "wafv2:CreateWebACL",
      "wafv2:DeleteWebACL",
      "wafv2:GetWebACL",
      "wafv2:ListTagsForResource",
      "wafv2:TagResource",
      "wafv2:UntagResource",
      "wafv2:UpdateWebACL",
    ]
    resources = [local.waf_web_acl_arn]
  }

  statement {
    sid    = "ReadCloudFrontWafCatalog"
    effect = "Allow"
    actions = [
      "wafv2:DescribeManagedRuleGroup",
      "wafv2:ListWebACLs",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageCloudFrontDistribution"
    effect = "Allow"
    actions = [
      "cloudfront:CreateInvalidation",
      "cloudfront:DeleteDistribution",
      "cloudfront:GetDistribution",
      "cloudfront:GetDistributionConfig",
      "cloudfront:ListTagsForResource",
      "cloudfront:TagResource",
      "cloudfront:UntagResource",
      "cloudfront:UpdateDistribution",
    ]
    resources = [module.cloudfront_distribution.distribution_arn]
  }

  statement {
    sid    = "ManageCloudFrontSupportResources"
    effect = "Allow"
    actions = [
      "cloudfront:CreateFunction",
      "cloudfront:CreateOriginAccessControl",
      "cloudfront:CreateResponseHeadersPolicy",
      "cloudfront:DeleteFunction",
      "cloudfront:DeleteOriginAccessControl",
      "cloudfront:DeleteResponseHeadersPolicy",
      "cloudfront:DescribeFunction",
      "cloudfront:GetFunction",
      "cloudfront:GetOriginAccessControl",
      "cloudfront:GetOriginAccessControlConfig",
      "cloudfront:GetResponseHeadersPolicy",
      "cloudfront:GetResponseHeadersPolicyConfig",
      "cloudfront:ListTagsForResource",
      "cloudfront:PublishFunction",
      "cloudfront:TagResource",
      "cloudfront:UntagResource",
      "cloudfront:UpdateFunction",
      "cloudfront:UpdateOriginAccessControl",
      "cloudfront:UpdateResponseHeadersPolicy",
    ]
    resources = local.cloudfront_support_resource_arns
  }

  statement {
    sid    = "ReadCloudFrontCatalog"
    effect = "Allow"
    actions = [
      "cloudfront:ListDistributions",
      "cloudfront:ListFunctions",
      "cloudfront:ListOriginAccessControls",
      "cloudfront:ListResponseHeadersPolicies",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "RequestCustomDomainCertificate"
    effect = "Allow"
    actions = [
      "acm:RequestCertificate",
    ]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Application"
      values   = [local.app_name]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Environment"
      values   = [var.app_env]
    }
  }

  statement {
    sid    = "ManageCustomDomainCertificate"
    effect = "Allow"
    actions = [
      "acm:AddTagsToCertificate",
      "acm:DeleteCertificate",
      "acm:DescribeCertificate",
      "acm:ListTagsForCertificate",
      "acm:RemoveTagsFromCertificate",
    ]
    resources = [local.acm_certificate_policy_arn]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Application"
      values   = [local.app_name]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Environment"
      values   = [var.app_env]
    }
  }

  statement {
    sid    = "ManageCustomDomainDnsRecords"
    effect = "Allow"
    actions = [
      "route53:ChangeResourceRecordSets",
      "route53:GetHostedZone",
      "route53:ListResourceRecordSets",
    ]
    resources = [local.route53_hosted_zone_arn]
  }

  statement {
    sid       = "ReadCustomDomainDnsChanges"
    effect    = "Allow"
    actions   = ["route53:GetChange"]
    resources = ["arn:aws:route53:::change/*"]
  }
}

resource "aws_iam_role_policy" "deploy" {
  name   = "${local.deploy_role_name}-policy"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy.json
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

  providers = {
    aws = aws.global
  }

  name_prefix          = local.name_prefix
  rate_limit_per_5_min = var.waf_rate_limit_per_5_min
  geo_allow_countries  = var.waf_geo_allow_countries
  tags                 = local.common_tags
}

module "cloudfront_distribution" {
  source = "../../modules/cloudfront_distribution"

  name_prefix                = local.name_prefix
  spa_bucket_regional_domain = module.s3_spa.bucket_regional_domain_name
  lambda_function_url_domain = module.lambda_api.function_url_domain
  origin_verify_header_value = var.origin_verify_header_value
  price_class                = var.price_class
  custom_domain              = var.custom_domain
  acm_certificate_arn        = module.custom_domain.certificate_arn
  enable_waf                 = var.enable_waf
  waf_web_acl_arn            = var.enable_waf ? module.waf[0].web_acl_arn : null
  tags                       = local.common_tags
}

module "custom_domain" {
  source = "../../modules/custom_domain"

  providers = {
    aws = aws.global
  }

  domain_name    = var.custom_domain
  dns_provider   = var.dns_provider
  hosted_zone_id = var.hosted_zone_id
  tags           = local.common_tags
}

resource "terraform_data" "custom_domain_route53_alias_inputs" {
  count = local.route53_custom_domain_enabled ? 1 : 0

  input = {
    hosted_zone_id = var.hosted_zone_id
  }

  lifecycle {
    precondition {
      condition     = var.hosted_zone_id != null && trimspace(var.hosted_zone_id) != ""
      error_message = "hosted_zone_id is required when dns_provider is route53 and custom_domain is set."
    }
  }
}

resource "aws_route53_record" "custom_domain_alias" {
  count = local.route53_custom_domain_enabled ? 1 : 0

  zone_id = coalesce(var.hosted_zone_id, "")
  name    = var.custom_domain
  type    = "A"

  alias {
    name                   = module.cloudfront_distribution.domain_name
    zone_id                = module.cloudfront_distribution.hosted_zone_id
    evaluate_target_health = false
  }

  depends_on = [terraform_data.custom_domain_route53_alias_inputs]
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
