locals {
  domain_enabled      = var.domain_name != null && trimspace(var.domain_name) != ""
  dns_provider        = lower(var.dns_provider)
  route53_enabled     = local.domain_enabled && local.dns_provider == "route53"
  route53_zone_id     = coalesce(var.hosted_zone_id, "")
  cloudfront_dns_name = coalesce(var.cloudfront_distribution_domain_name, "")
  cloudfront_zone_id  = coalesce(var.cloudfront_distribution_hosted_zone_id, "")

  validation_records = local.domain_enabled ? {
    for option in aws_acm_certificate.this[0].domain_validation_options : option.domain_name => {
      domain_name = option.domain_name
      name        = option.resource_record_name
      type        = option.resource_record_type
      value       = option.resource_record_value
    }
  } : {}
}

resource "aws_acm_certificate" "this" {
  count = local.domain_enabled ? 1 : 0

  domain_name       = var.domain_name
  validation_method = "DNS"
  tags              = var.tags

  lifecycle {
    create_before_destroy = true
  }
}

resource "terraform_data" "route53_zone_input" {
  count = local.route53_enabled ? 1 : 0

  input = {
    hosted_zone_id = var.hosted_zone_id
  }

  lifecycle {
    precondition {
      condition     = var.hosted_zone_id != null && trimspace(var.hosted_zone_id) != ""
      error_message = "hosted_zone_id is required when dns_provider is route53 and domain_name is set."
    }
  }
}

resource "terraform_data" "route53_alias_inputs" {
  count = local.route53_enabled ? 1 : 0

  input = {
    cloudfront_distribution_domain_name    = var.cloudfront_distribution_domain_name
    cloudfront_distribution_hosted_zone_id = var.cloudfront_distribution_hosted_zone_id
  }

  lifecycle {
    precondition {
      condition     = var.cloudfront_distribution_domain_name != null && trimspace(var.cloudfront_distribution_domain_name) != ""
      error_message = "cloudfront_distribution_domain_name is required when dns_provider is route53 and domain_name is set."
    }

    precondition {
      condition     = var.cloudfront_distribution_hosted_zone_id != null && trimspace(var.cloudfront_distribution_hosted_zone_id) != ""
      error_message = "cloudfront_distribution_hosted_zone_id is required when dns_provider is route53 and domain_name is set."
    }
  }
}

resource "aws_route53_record" "validation" {
  for_each = local.route53_enabled ? local.validation_records : {}

  zone_id         = local.route53_zone_id
  name            = each.value.name
  type            = each.value.type
  ttl             = 60
  records         = [each.value.value]
  allow_overwrite = true

  depends_on = [terraform_data.route53_zone_input]
}

resource "aws_acm_certificate_validation" "this" {
  count = local.route53_enabled ? 1 : 0

  certificate_arn         = aws_acm_certificate.this[0].arn
  validation_record_fqdns = [for record in aws_route53_record.validation : record.fqdn]
}

resource "aws_route53_record" "alias" {
  count = local.route53_enabled ? 1 : 0

  zone_id = local.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = local.cloudfront_dns_name
    zone_id                = local.cloudfront_zone_id
    evaluate_target_health = false
  }

  depends_on = [terraform_data.route53_alias_inputs]
}
