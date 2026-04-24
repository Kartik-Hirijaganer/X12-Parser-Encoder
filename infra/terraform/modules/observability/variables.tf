variable "function_name" {
  description = "Lambda function name."
  type        = string
}

variable "alarm_sns_topic_arn" {
  description = "Optional SNS topic ARN for alarm actions."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to CloudWatch alarms."
  type        = map(string)
  default     = {}
}
