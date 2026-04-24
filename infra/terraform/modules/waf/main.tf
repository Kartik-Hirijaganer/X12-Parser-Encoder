# Phase 4 owns WAF rules. Phase 2 keeps this module as a stable integration point.
resource "terraform_data" "stub" {
  input = {
    name_prefix = var.name_prefix
    tags        = var.tags
  }
}
