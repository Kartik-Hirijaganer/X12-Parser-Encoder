# lambda_api

Provisions the Python 3.12 Lambda API, a `live` alias, a public Lambda Function URL with `AuthType = NONE`, the public Function URL permission, and the Lambda log group.

## Inputs

| Name | Description | Default |
|---|---|---|
| `function_name` | Lambda function name. | Required |
| `zip_path` | Local Lambda zip path. Mutually exclusive with S3 zip and image inputs. | `null` |
| `s3_bucket` | S3 bucket containing the Lambda zip. Must be set with `s3_key`. | `null` |
| `s3_key` | S3 key containing the Lambda zip. Must be set with `s3_bucket`. | `null` |
| `image_uri` | Container image URI fallback. Mutually exclusive with zip inputs. | `null` |
| `environment_vars` | Lambda environment variables. | `{}` |
| `memory_mb` | Lambda memory in MB. | `1024` |
| `timeout_s` | Lambda timeout in seconds. | `30` |
| `lambda_architecture` | Runtime architecture, `x86_64` or `arm64`. | `x86_64` |
| `enable_snapstart` | Enable SnapStart for published versions. | `false` |
| `reserved_concurrency` | Reserved concurrency ceiling. | `10` |
| `log_retention_days` | CloudWatch log retention in days. | `14` |
| `tags` | Tags for resources. | `{}` |

## Outputs

| Name | Description |
|---|---|
| `function_url_domain` | Function URL domain without scheme or trailing slash. |
| `function_arn` | Lambda function ARN. |
| `function_name` | Lambda function name. |
| `function_version` | Published Lambda function version routed by the live alias. |
| `invoke_arn` | Lambda invoke ARN. |
| `log_group_name` | Lambda log group name. |

## Usage

```hcl
module "lambda_api" {
  source        = "../../modules/lambda_api"
  function_name = "x12-parser-encoder-api-example"
  zip_path      = "${path.module}/placeholder-lambda.zip"

  environment_vars = {
    X12_API_DEPLOYMENT_TARGET       = "lambda"
    X12_API_ORIGIN_SECRET_ENABLED   = "true"
    X12_API_ORIGIN_SECRET           = var.origin_verify_header_value
    X12_API_ORIGIN_SECRET_PREVIOUS  = ""
    X12_API_ENVIRONMENT             = "example"
    X12_API_SERVE_FRONTEND          = "false"
    X12_API_METRICS_ENABLED         = "true"
  }
}
```
