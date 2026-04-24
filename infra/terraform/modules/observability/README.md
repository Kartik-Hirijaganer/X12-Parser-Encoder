# observability

Creates Phase 2 CloudWatch metric filters and alarms for the Lambda API log group.

## Inputs

| Name | Description | Default |
|---|---|---|
| `function_name` | Lambda function name. | Required |
| `alarm_sns_topic_arn` | Optional SNS topic ARN for alarm notifications. | `null` |
| `tags` | Tags for alarms. | `{}` |

## Outputs

| Name | Description |
|---|---|
| `metric_namespace` | Custom CloudWatch namespace. |
| `alarm_names` | Names of the CloudWatch alarms. |

## Usage

```hcl
module "observability" {
  source        = "../../modules/observability"
  function_name = "x12-parser-encoder-api-example"
}
```
