variable "bucket_name" {
  description = "Name of the private S3 bucket that stores the SPA build."
  type        = string
}

variable "kms_key_arn" {
  description = "Optional KMS key ARN for bucket encryption. When null, SSE-S3 is used."
  type        = string
  default     = null
}

variable "force_destroy" {
  description = "Allow Terraform to delete a non-empty SPA bucket. Keep false outside disposable environments."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to S3 resources."
  type        = map(string)
  default     = {}
}
