output "metric_namespace" {
  description = "CloudWatch namespace for custom Lambda API metrics."
  value       = local.namespace
}

output "alarm_names" {
  description = "CloudWatch alarm names created by this module."
  value = [
    aws_cloudwatch_metric_alarm.http_5xx.alarm_name,
    aws_cloudwatch_metric_alarm.throttles.alarm_name,
    aws_cloudwatch_metric_alarm.latency_p95.alarm_name,
    aws_cloudwatch_metric_alarm.lambda_errors.alarm_name,
  ]
}
