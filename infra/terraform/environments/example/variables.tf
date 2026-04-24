variable "app_env" {
  description = "Application environment name. This environment defaults to example."
  type        = string
  default     = "example"
}

variable "aws_region" {
  description = "AWS region for regional resources."
  type        = string
  default     = "us-east-2"
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
  description = "Local Lambda zip path. Defaults to the checked-in Phase 2 placeholder."
  type        = string
  default     = "placeholder-lambda.zip"
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
  description = "Enable Lambda SnapStart. Phase 2 default is false."
  type        = bool
  default     = false
}

variable "reserved_concurrency" {
  description = "Lambda reserved concurrency."
  type        = number
  default     = 10
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

variable "enable_waf" {
  description = "Enable the WAF module. Phase 2 default is false."
  type        = bool
  default     = false
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
