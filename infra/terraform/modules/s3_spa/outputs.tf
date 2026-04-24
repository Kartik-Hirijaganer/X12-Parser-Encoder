output "bucket_regional_domain_name" {
  description = "Regional domain name for the SPA S3 bucket."
  value       = aws_s3_bucket.this.bucket_regional_domain_name
}

output "bucket_arn" {
  description = "ARN of the SPA S3 bucket."
  value       = aws_s3_bucket.this.arn
}
