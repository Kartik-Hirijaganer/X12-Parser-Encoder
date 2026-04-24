variable "name_prefix" {
  description = "Name prefix for the WAF web ACL and metrics."
  type        = string
}

variable "rate_limit_per_5_min" {
  description = "Maximum requests per 5-minute window per source IP before WAF blocks."
  type        = number
  default     = 2000

  validation {
    condition     = var.rate_limit_per_5_min >= 100
    error_message = "rate_limit_per_5_min must be at least 100."
  }
}

variable "geo_allow_countries" {
  description = "Optional ISO 3166-1 alpha-2 country allow-list. Empty means no geo filter."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags applied to WAF resources."
  type        = map(string)
  default     = {}
}
