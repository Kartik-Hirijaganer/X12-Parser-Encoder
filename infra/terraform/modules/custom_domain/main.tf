# Phase 5 owns custom domains, ACM, and Route 53. Phase 2 keeps this module as a stable integration point.
resource "terraform_data" "stub" {
  input = {
    domain_name                            = var.domain_name
    hosted_zone_id                         = var.hosted_zone_id
    cloudfront_distribution_domain_name    = var.cloudfront_distribution_domain_name
    cloudfront_distribution_hosted_zone_id = var.cloudfront_distribution_hosted_zone_id
    tags                                   = var.tags
  }
}
