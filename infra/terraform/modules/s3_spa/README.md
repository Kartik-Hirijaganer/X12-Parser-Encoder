# s3_spa

Provisions the private S3 bucket used for the SPA bundle. CloudFront access is granted by the environment root after the distribution ARN exists.

## Inputs

| Name | Description | Default |
|---|---|---|
| `bucket_name` | Private SPA bucket name. | Required |
| `kms_key_arn` | Optional KMS key ARN. Uses SSE-S3 when null. | `null` |
| `force_destroy` | Allow deletion of a non-empty bucket. | `false` |
| `tags` | Tags for resources. | `{}` |

## Outputs

| Name | Description |
|---|---|
| `bucket_regional_domain_name` | Regional bucket domain for the CloudFront S3 origin. |
| `bucket_arn` | SPA bucket ARN. |

## Usage

```hcl
module "s3_spa" {
  source      = "../../modules/s3_spa"
  bucket_name = "x12-parser-encoder-spa-example-123456789012-us-east-2"
}
```
