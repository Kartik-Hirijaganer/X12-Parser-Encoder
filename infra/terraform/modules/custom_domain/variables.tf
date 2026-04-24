variable "domain_name" {
  description = "Custom domain name to attach to the CloudFront distribution. Null disables custom-domain resources."
  type        = string
  default     = null
}

variable "dns_provider" {
  description = "DNS provider mode for the custom domain. route53 creates validation and ALIAS records; external only outputs records for manual DNS."
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

variable "cloudfront_distribution_domain_name" {
  description = "CloudFront distribution domain name used as the custom-domain DNS target."
  type        = string
  default     = null
}

variable "cloudfront_distribution_hosted_zone_id" {
  description = "CloudFront distribution hosted zone ID used by Route 53 ALIAS records."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to custom-domain resources that support tagging."
  type        = map(string)
  default     = {}
}
