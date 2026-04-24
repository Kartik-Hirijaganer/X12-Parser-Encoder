variable "name_prefix" {
  description = "Name prefix reserved for the Phase 4 WAF web ACL."
  type        = string
}

variable "tags" {
  description = "Tags reserved for Phase 4 WAF resources."
  type        = map(string)
  default     = {}
}
