locals {
  metric_name_prefix = replace(var.name_prefix, "/[^A-Za-z0-9_-]/", "-")
  geo_rule_enabled   = length(var.geo_allow_countries) > 0

  # Content-Length values strictly greater than 6,291,456 bytes.
  upload_size_limit_regex = "^([1-9][0-9]{7,}|[7-9][0-9]{6}|6[3-9][0-9]{5}|629[2-9][0-9]{3}|6291[5-9][0-9]{2}|62914[6-9][0-9]|629145[7-9])$"
}

resource "aws_wafv2_web_acl" "this" {
  name        = "${var.name_prefix}-web-acl"
  description = "CloudFront WAF for the X12 Parser Encoder serverless edge."
  scope       = "CLOUDFRONT"
  tags        = var.tags

  default_action {
    allow {}
  }

  dynamic "rule" {
    for_each = local.geo_rule_enabled ? [1] : []

    content {
      name     = "GeoAllowList"
      priority = 0

      action {
        block {}
      }

      statement {
        not_statement {
          statement {
            geo_match_statement {
              country_codes = var.geo_allow_countries
            }
          }
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${local.metric_name_prefix}-geo-block"
        sampled_requests_enabled   = true
      }
    }
  }

  rule {
    name     = "UploadBodySizeLimit"
    priority = 10

    action {
      block {
        custom_response {
          response_code = 413
        }
      }
    }

    statement {
      regex_match_statement {
        regex_string = local.upload_size_limit_regex

        field_to_match {
          single_header {
            name = "content-length"
          }
        }

        text_transformation {
          priority = 0
          type     = "NONE"
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.metric_name_prefix}-upload-size"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "RateLimitByIp"
    priority = 20

    action {
      block {}
    }

    statement {
      rate_based_statement {
        aggregate_key_type = "IP"
        limit              = var.rate_limit_per_5_min
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.metric_name_prefix}-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 30

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        rule_action_override {
          name = "SizeRestrictions_BODY"

          action_to_use {
            count {}
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.metric_name_prefix}-common"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 40

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.metric_name_prefix}-known-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.metric_name_prefix}-web-acl"
    sampled_requests_enabled   = true
  }
}
