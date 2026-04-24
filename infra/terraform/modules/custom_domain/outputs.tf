output "domain_name" {
  description = "Configured custom domain. Null until Phase 5 implements this module."
  value       = var.domain_name
}

output "certificate_arn" {
  description = "ACM certificate ARN. Null until Phase 5 implements this module."
  value       = null
}
