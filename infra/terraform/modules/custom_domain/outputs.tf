output "domain_name" {
  description = "Configured custom domain, or null when disabled."
  value       = local.domain_enabled ? var.domain_name : null
}

output "certificate_arn" {
  description = "ACM certificate ARN for CloudFront. Route 53 mode waits for DNS validation before returning it."
  value = local.domain_enabled ? (
    local.route53_enabled ? aws_acm_certificate_validation.this[0].certificate_arn : aws_acm_certificate.this[0].arn
  ) : null
}

output "validation_records" {
  description = "DNS validation records required by ACM. External DNS operators add these records manually."
  value       = [for record in local.validation_records : record]
}

output "cname_record" {
  description = "Deprecated placeholder retained for module output compatibility. Environment roots provide the CloudFront CNAME target."
  value       = null
}
