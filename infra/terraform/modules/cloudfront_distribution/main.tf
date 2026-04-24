locals {
  s3_origin_id     = "spa-s3"
  lambda_origin_id = "lambda-api"

  # AWS-managed CloudFront policy IDs.
  caching_optimized_policy_id             = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  caching_disabled_policy_id              = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
  all_viewer_except_host_header_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  effective_response_headers_policy_id    = var.response_headers_policy_id != null ? var.response_headers_policy_id : aws_cloudfront_response_headers_policy.security[0].id
  custom_domain_enabled                   = var.custom_domain != null && trimspace(var.custom_domain) != ""
}

resource "aws_cloudfront_origin_access_control" "s3" {
  name                              = "${var.name_prefix}-spa-oac"
  description                       = "SigV4 OAC for the private SPA S3 bucket."
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_function" "spa_rewrite" {
  name    = "${var.name_prefix}-spa-rewrite"
  runtime = "cloudfront-js-1.0"
  comment = "Rewrite SPA routes to /index.html while leaving /api/* and file paths unchanged."
  publish = true
  code    = <<-EOT
function handler(event) {
  var request = event.request;
  var uri = request.uri;

  if (uri.indexOf('/api/') === 0) {
    return request;
  }

  if (uri.charAt(uri.length - 1) === '/') {
    request.uri = '/index.html';
    return request;
  }

  var lastSegment = uri.substring(uri.lastIndexOf('/') + 1);
  if (lastSegment.indexOf('.') === -1) {
    request.uri = '/index.html';
  }

  return request;
}
EOT
}

resource "aws_cloudfront_response_headers_policy" "security" {
  count = var.response_headers_policy_id == null ? 1 : 0

  name    = "${var.name_prefix}-security-headers"
  comment = "Phase 4 security headers for the CloudFront SPA and API."

  security_headers_config {
    content_security_policy {
      content_security_policy = var.content_security_policy
      override                = true
    }

    content_type_options {
      override = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }

    strict_transport_security {
      access_control_max_age_sec = 63072000
      include_subdomains         = true
      preload                    = true
      override                   = true
    }
  }

  custom_headers_config {
    items {
      header   = "Permissions-Policy"
      value    = "camera=(), microphone=(), geolocation=(), payment=()"
      override = true
    }
  }
}

resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.name_prefix} SPA and Lambda API"
  default_root_object = "index.html"
  price_class         = var.price_class
  web_acl_id          = var.enable_waf ? var.waf_web_acl_arn : null
  aliases             = local.custom_domain_enabled ? [var.custom_domain] : []
  tags                = var.tags

  origin {
    domain_name              = var.spa_bucket_regional_domain
    origin_id                = local.s3_origin_id
    origin_access_control_id = aws_cloudfront_origin_access_control.s3.id
  }

  origin {
    domain_name = var.lambda_function_url_domain
    origin_id   = local.lambda_origin_id

    custom_header {
      name  = "X-Origin-Verify"
      value = var.origin_verify_header_value
    }

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = local.s3_origin_id
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = local.caching_optimized_policy_id
    compress               = true

    response_headers_policy_id = local.effective_response_headers_policy_id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_rewrite.arn
    }
  }

  ordered_cache_behavior {
    path_pattern               = "/api/*"
    target_origin_id           = local.lambda_origin_id
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods             = ["GET", "HEAD", "OPTIONS"]
    cache_policy_id            = local.caching_disabled_policy_id
    origin_request_policy_id   = local.all_viewer_except_host_header_policy_id
    response_headers_policy_id = local.effective_response_headers_policy_id
    compress                   = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn            = local.custom_domain_enabled ? var.acm_certificate_arn : null
    cloudfront_default_certificate = local.custom_domain_enabled ? null : true
    minimum_protocol_version       = local.custom_domain_enabled ? "TLSv1.2_2021" : null
    ssl_support_method             = local.custom_domain_enabled ? "sni-only" : null
  }

  lifecycle {
    precondition {
      condition     = !var.enable_waf || var.waf_web_acl_arn != null
      error_message = "waf_web_acl_arn is required when enable_waf is true."
    }

    precondition {
      condition     = !local.custom_domain_enabled || try(trimspace(var.acm_certificate_arn) != "", false)
      error_message = "acm_certificate_arn is required when custom_domain is set."
    }
  }
}
