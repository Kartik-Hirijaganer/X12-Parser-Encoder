output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID."
  value       = module.cloudfront_distribution.distribution_id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name."
  value       = module.cloudfront_distribution.domain_name
}

output "cloudfront_url" {
  description = "HTTPS URL for the CloudFront distribution."
  value       = "https://${module.cloudfront_distribution.domain_name}"
}

output "spa_bucket_name" {
  description = "Private SPA bucket name."
  value       = local.spa_bucket_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN."
  value       = module.lambda_api.function_arn
}

output "lambda_log_group_name" {
  description = "Lambda log group name."
  value       = module.lambda_api.log_group_name
}

output "observability_metric_namespace" {
  description = "CloudWatch namespace for Lambda API custom metrics."
  value       = module.observability.metric_namespace
}
