output "function_url_domain" {
  description = "Lambda Function URL domain name without scheme or trailing slash."
  value       = trimsuffix(trimprefix(aws_lambda_function_url.live.function_url, "https://"), "/")
}

output "function_arn" {
  description = "ARN of the Lambda function."
  value       = aws_lambda_function.this.arn
}

output "invoke_arn" {
  description = "Invoke ARN of the Lambda function."
  value       = aws_lambda_function.this.invoke_arn
}

output "log_group_name" {
  description = "CloudWatch log group name for the Lambda function."
  value       = aws_cloudwatch_log_group.this.name
}
