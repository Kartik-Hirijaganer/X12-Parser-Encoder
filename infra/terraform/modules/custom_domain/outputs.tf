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
  description = "CNAME record external DNS operators can point at the CloudFront distribution."
  value = local.domain_enabled ? {
    name  = var.domain_name
    type  = "CNAME"
    value = var.cloudfront_distribution_domain_name
  } : null
}

output "route53_alias_fqdn" {
  description = "Route 53 ALIAS record FQDN, or null when Route 53 DNS is not managed by Terraform."
  value       = local.route53_enabled ? aws_route53_record.alias[0].fqdn : null
}
