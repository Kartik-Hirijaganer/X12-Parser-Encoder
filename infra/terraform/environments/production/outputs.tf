output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID."
  value       = module.cloudfront_distribution.distribution_id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name."
  value       = module.cloudfront_distribution.domain_name
}

output "cloudfront_hosted_zone_id" {
  description = "CloudFront distribution hosted zone ID for DNS aliases."
  value       = module.cloudfront_distribution.hosted_zone_id
}

output "cloudfront_url" {
  description = "HTTPS URL for the CloudFront distribution."
  value       = "https://${module.cloudfront_distribution.domain_name}"
}

output "custom_domain_url" {
  description = "HTTPS URL for the custom domain, or null when disabled."
  value       = module.custom_domain.domain_name == null ? null : "https://${module.custom_domain.domain_name}"
}

output "custom_domain_certificate_arn" {
  description = "ACM certificate ARN for the custom domain, or null when disabled."
  value       = module.custom_domain.certificate_arn
}

output "custom_domain_validation_records" {
  description = "ACM DNS validation records for external DNS providers."
  value       = module.custom_domain.validation_records
}

output "custom_domain_cname_record" {
  description = "External DNS CNAME record pointing the custom domain at CloudFront."
  value       = module.custom_domain.cname_record
}

output "custom_domain_route53_alias_fqdn" {
  description = "Route 53 ALIAS record FQDN, or null when Route 53 DNS is not managed by Terraform."
  value       = module.custom_domain.route53_alias_fqdn
}

output "deploy_role_arn" {
  description = "GitHub Actions OIDC deploy role ARN."
  value       = aws_iam_role.deploy.arn
}

output "lambda_function_arn" {
  description = "Lambda function ARN."
  value       = module.lambda_api.function_arn
}

output "lambda_function_name" {
  description = "Lambda function name."
  value       = module.lambda_api.function_name
}

output "lambda_function_version" {
  description = "Published Lambda version served by the live alias."
  value       = module.lambda_api.function_version
}

output "lambda_log_group_name" {
  description = "Lambda log group name."
  value       = module.lambda_api.log_group_name
}

output "observability_metric_namespace" {
  description = "CloudWatch namespace for Lambda API custom metrics."
  value       = module.observability.metric_namespace
}

output "observability_alarm_names" {
  description = "CloudWatch alarm names for the Lambda API."
  value       = module.observability.alarm_names
}

output "spa_bucket_name" {
  description = "Private SPA bucket name."
  value       = local.spa_bucket_name
}

output "waf_web_acl_arn" {
  description = "WAF web ACL ARN attached to CloudFront, or null when WAF is disabled."
  value       = var.enable_waf ? module.waf[0].web_acl_arn : null
}
