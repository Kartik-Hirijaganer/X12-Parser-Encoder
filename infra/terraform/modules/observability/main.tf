locals {
  log_group_name = "/aws/lambda/${var.function_name}"
  namespace      = "X12ParserEncoder/LambdaApi"
  alarm_actions  = var.alarm_sns_topic_arn == null ? [] : [var.alarm_sns_topic_arn]
}

resource "aws_cloudwatch_log_metric_filter" "correlation_id" {
  name           = "${var.function_name}-correlation-id"
  log_group_name = local.log_group_name
  pattern        = "{ $.correlation_id = * }"

  metric_transformation {
    name      = "CorrelationIdSeen"
    namespace = local.namespace
    value     = "1"

    dimensions = {
      CorrelationId = "$.correlation_id"
    }
  }
}

resource "aws_cloudwatch_log_metric_filter" "error_code" {
  name           = "${var.function_name}-error-code"
  log_group_name = local.log_group_name
  pattern        = "{ $.error_code = * }"

  metric_transformation {
    name      = "ErrorCodeCount"
    namespace = local.namespace
    value     = "1"

    dimensions = {
      ErrorCode = "$.error_code"
    }
  }
}

resource "aws_cloudwatch_log_metric_filter" "http_5xx" {
  name           = "${var.function_name}-http-5xx"
  log_group_name = local.log_group_name
  pattern        = "{ $.status_code >= 500 }"

  metric_transformation {
    name      = "Http5xxCount"
    namespace = local.namespace
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "request_latency" {
  name           = "${var.function_name}-request-latency"
  log_group_name = local.log_group_name
  pattern        = "{ $.duration_ms = * }"

  metric_transformation {
    name      = "RequestLatencyMs"
    namespace = local.namespace
    value     = "$.duration_ms"
    unit      = "Milliseconds"
  }
}

resource "aws_cloudwatch_log_metric_filter" "cold_start" {
  name           = "${var.function_name}-cold-start"
  log_group_name = local.log_group_name
  pattern        = "\"Init Duration\""

  metric_transformation {
    name      = "ColdStartCount"
    namespace = local.namespace
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "http_5xx" {
  alarm_name          = "${var.function_name}-5xx-rate"
  alarm_description   = "Lambda API returned elevated 5xx responses."
  namespace           = local.namespace
  metric_name         = aws_cloudwatch_log_metric_filter.http_5xx.metric_transformation[0].name
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 5
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "throttles" {
  alarm_name          = "${var.function_name}-throttles"
  alarm_description   = "Lambda API is being throttled."
  namespace           = "AWS/Lambda"
  metric_name         = "Throttles"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  tags                = var.tags

  dimensions = {
    FunctionName = var.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "latency_p95" {
  alarm_name          = "${var.function_name}-latency-p95"
  alarm_description   = "Lambda API p95 latency is elevated."
  namespace           = local.namespace
  metric_name         = aws_cloudwatch_log_metric_filter.request_latency.metric_transformation[0].name
  extended_statistic  = "p95"
  period              = 60
  evaluation_periods  = 5
  threshold           = 5000
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  tags                = var.tags
}

resource "aws_cloudwatch_metric_alarm" "cold_starts" {
  alarm_name          = "${var.function_name}-cold-starts"
  alarm_description   = "Lambda API cold-start frequency is elevated."
  namespace           = local.namespace
  metric_name         = aws_cloudwatch_log_metric_filter.cold_start.metric_transformation[0].name
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions
  tags                = var.tags
}
