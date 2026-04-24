variable "domain_name" {
  description = "Custom domain name reserved for Phase 5."
  type        = string
  default     = null
}

variable "hosted_zone_id" {
  description = "Route 53 hosted zone ID reserved for Phase 5."
  type        = string
  default     = null
}

variable "cloudfront_distribution_domain_name" {
  description = "CloudFront domain name reserved for Phase 5 alias records."
  type        = string
  default     = null
}

variable "cloudfront_distribution_hosted_zone_id" {
  description = "CloudFront hosted zone ID reserved for Phase 5 alias records."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags reserved for Phase 5 custom-domain resources."
  type        = map(string)
  default     = {}
}
