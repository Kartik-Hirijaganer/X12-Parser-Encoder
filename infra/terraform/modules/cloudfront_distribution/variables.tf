variable "name_prefix" {
  description = "Name prefix for CloudFront supporting resources."
  type        = string
}

variable "spa_bucket_regional_domain" {
  description = "Regional S3 bucket domain name for the SPA origin."
  type        = string
}

variable "lambda_function_url_domain" {
  description = "Lambda Function URL domain name without scheme or trailing slash."
  type        = string
}

variable "origin_verify_header_value" {
  description = "Secret value CloudFront sends to the Lambda origin in X-Origin-Verify."
  type        = string
  sensitive   = true
}

variable "price_class" {
  description = "CloudFront price class."
  type        = string
  default     = "PriceClass_100"
}

variable "enable_waf" {
  description = "Whether to attach a WAF web ACL."
  type        = bool
  default     = false
}

variable "waf_web_acl_arn" {
  description = "Optional WAF web ACL ARN. Required when enable_waf is true."
  type        = string
  default     = null
}

variable "response_headers_policy_id" {
  description = "Optional existing response headers policy ID. When null, this module creates the Phase 2 policy."
  type        = string
  default     = null
}

variable "content_security_policy" {
  description = "Content-Security-Policy used by the Phase 2 response headers policy."
  type        = string
  default     = "default-src 'self'; connect-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; font-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
}

variable "tags" {
  description = "Tags applied to CloudFront resources that support tagging."
  type        = map(string)
  default     = {}
}
