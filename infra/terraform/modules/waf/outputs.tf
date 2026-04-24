output "web_acl_arn" {
  description = "WAF web ACL ARN for CloudFront web_acl_id."
  value       = aws_wafv2_web_acl.this.arn
}

output "web_acl_id" {
  description = "WAF web ACL ID."
  value       = aws_wafv2_web_acl.this.id
}

output "rate_limit_per_5_min" {
  description = "Configured per-IP WAF rate limit over 5 minutes."
  value       = var.rate_limit_per_5_min
}
