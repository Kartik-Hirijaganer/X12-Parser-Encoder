variable "app_env" {
  description = "Application environment name."
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region for regional resources."
  type        = string
  default     = "us-east-2"
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the deploy role, formatted as owner/repo."
  type        = string
  default     = "Kartik-Hirijaganer/X12-Parser-Encoder"
}

variable "github_oidc_subjects" {
  description = "Optional explicit GitHub OIDC subject patterns allowed to assume the deploy role."
  type        = list(string)
  default     = null
}

variable "github_oidc_provider_arn" {
  description = "Existing GitHub Actions OIDC provider ARN. Defaults to the standard provider ARN in this account."
  type        = string
  default     = null
}

variable "manage_github_oidc_provider" {
  description = "Create the account-level GitHub Actions OIDC provider from this environment state."
  type        = bool
  default     = false
}

variable "origin_verify_header_value" {
  description = "CloudFront-to-Lambda origin verification secret."
  type        = string
  sensitive   = true
}

variable "origin_verify_header_previous_value" {
  description = "Previous origin verification secret retained during rotation."
  type        = string
  default     = ""
  sensitive   = true
}

variable "lambda_zip_path" {
  description = "Local Lambda zip path used before the first Phase 3 S3 artifact exists."
  type        = string
  default     = "../example/placeholder-lambda.zip"
}

variable "lambda_zip_s3_bucket" {
  description = "S3 bucket containing a Lambda zip artifact. Used with lambda_zip_s3_key."
  type        = string
  default     = null
}

variable "lambda_zip_s3_key" {
  description = "S3 key containing a Lambda zip artifact. Used with lambda_zip_s3_bucket."
  type        = string
  default     = null
}

variable "lambda_image_uri" {
  description = "Container-image fallback URI for the Lambda function."
  type        = string
  default     = null
}

variable "lambda_environment_vars" {
  description = "Additional Lambda environment variables."
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "memory_mb" {
  description = "Lambda memory in MB."
  type        = number
  default     = 1024
}

variable "timeout_s" {
  description = "Lambda timeout in seconds."
  type        = number
  default     = 30
}

variable "lambda_architecture" {
  description = "Lambda runtime architecture."
  type        = string
  default     = "x86_64"

  validation {
    condition     = contains(["x86_64", "arm64"], var.lambda_architecture)
    error_message = "lambda_architecture must be x86_64 or arm64."
  }
}

variable "enable_snapstart" {
  description = "Enable Lambda SnapStart. Production defaults on because the default us-east-2 runtime supports Python 3.12 SnapStart."
  type        = bool
  default     = true
}

variable "reserved_concurrency" {
  description = "Lambda reserved concurrency."
  type        = number
  default     = 50
}

variable "log_retention_days" {
  description = "Lambda CloudWatch log retention in days."
  type        = number
  default     = 14
}

variable "spa_bucket_name" {
  description = "Optional explicit SPA bucket name. Defaults to an app/env/account/region name."
  type        = string
  default     = null
}

variable "kms_key_arn" {
  description = "Optional KMS key ARN for SPA bucket encryption."
  type        = string
  default     = null
}

variable "force_destroy_spa_bucket" {
  description = "Allow deleting a non-empty SPA bucket. Keep false outside disposable environments."
  type        = bool
  default     = false
}

variable "price_class" {
  description = "CloudFront price class."
  type        = string
  default     = "PriceClass_100"
}

variable "custom_domain" {
  description = "Optional custom hostname to attach to CloudFront."
  type        = string
  default     = null
}

variable "dns_provider" {
  description = "DNS provider mode for custom_domain. route53 creates DNS records; external outputs records for manual DNS."
  type        = string
  default     = "route53"
  nullable    = false

  validation {
    condition     = contains(["route53", "external"], lower(var.dns_provider))
    error_message = "dns_provider must be route53 or external."
  }
}

variable "hosted_zone_id" {
  description = "Route 53 hosted zone ID used when dns_provider is route53."
  type        = string
  default     = null
}

variable "enable_waf" {
  description = "Enable the CloudFront WAF module."
  type        = bool
  default     = true
}

variable "waf_rate_limit_per_5_min" {
  description = "Maximum requests per 5-minute window per source IP before WAF blocks."
  type        = number
  default     = 2000
}

variable "waf_geo_allow_countries" {
  description = "Optional ISO 3166-1 alpha-2 country allow-list. Empty means global."
  type        = list(string)
  default     = []
}

variable "alarm_sns_topic_arn" {
  description = "Optional SNS topic ARN for CloudWatch alarm actions."
  type        = string
  default     = null
}

variable "tags" {
  description = "Additional tags for Terraform-managed resources."
  type        = map(string)
  default     = {}
}
