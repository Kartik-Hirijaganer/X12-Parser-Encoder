variable "function_name" {
  description = "Name of the Lambda function."
  type        = string
}

variable "zip_path" {
  description = "Local Lambda zip path. Mutually exclusive with s3_bucket/s3_key and image_uri."
  type        = string
  default     = null
}

variable "s3_bucket" {
  description = "S3 bucket containing the Lambda zip artifact. Must be set with s3_key."
  type        = string
  default     = null
}

variable "s3_key" {
  description = "S3 key containing the Lambda zip artifact. Must be set with s3_bucket."
  type        = string
  default     = null
}

variable "image_uri" {
  description = "Container image URI fallback for the Lambda function. Mutually exclusive with zip inputs."
  type        = string
  default     = null
}

variable "environment_vars" {
  description = "Environment variables injected into the Lambda function."
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "memory_mb" {
  description = "Lambda memory size in MB."
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
  description = "Enable SnapStart for published Lambda versions. Defaults off until Phase 4."
  type        = bool
  default     = false
}

variable "reserved_concurrency" {
  description = "Reserved concurrency ceiling for the Lambda function."
  type        = number
  default     = 10
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days."
  type        = number
  default     = 14
}

variable "tags" {
  description = "Tags applied to Lambda and supporting resources."
  type        = map(string)
  default     = {}
}
