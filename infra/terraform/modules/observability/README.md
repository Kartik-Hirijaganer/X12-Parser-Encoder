# observability

Creates CloudWatch metric filters and the Phase 4 Lambda API alarms.

Alarms:

- 5xx responses greater than 1% of Lambda invocations over 5 minutes
- Throttles greater than 0 over 5 minutes
- Lambda duration p95 greater than 3 seconds over 5 minutes
- Lambda errors greater than 5 over 5 minutes

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
