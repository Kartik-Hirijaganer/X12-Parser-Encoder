locals {
  uses_local_zip = var.zip_path != null
  uses_s3_zip    = var.s3_bucket != null && var.s3_key != null
  uses_image     = var.image_uri != null
  artifact_source_count = (
    (local.uses_local_zip ? 1 : 0) +
    (local.uses_s3_zip ? 1 : 0) +
    (local.uses_image ? 1 : 0)
  )
}

resource "terraform_data" "artifact_validation" {
  input = local.artifact_source_count

  lifecycle {
    precondition {
      condition     = local.artifact_source_count == 1
      error_message = "Provide exactly one Lambda artifact source: zip_path, s3_bucket+s3_key, or image_uri."
    }

    precondition {
      condition     = (var.s3_bucket == null && var.s3_key == null) || (var.s3_bucket != null && var.s3_key != null)
      error_message = "s3_bucket and s3_key must be set together."
    }

    precondition {
      condition     = !(local.uses_image && var.enable_snapstart)
      error_message = "SnapStart is not supported for container-image Lambda functions."
    }
  }
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${var.function_name}-exec"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = var.tags
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

data "aws_iam_policy_document" "logs" {
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      aws_cloudwatch_log_group.this.arn,
      "${aws_cloudwatch_log_group.this.arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "logs" {
  name   = "${var.function_name}-logs"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.logs.json
}

resource "aws_lambda_function" "this" {
  function_name                  = var.function_name
  role                           = aws_iam_role.execution.arn
  package_type                   = local.uses_image ? "Image" : "Zip"
  filename                       = local.uses_local_zip ? var.zip_path : null
  source_code_hash               = local.uses_local_zip ? filebase64sha256(var.zip_path) : null
  s3_bucket                      = local.uses_s3_zip ? var.s3_bucket : null
  s3_key                         = local.uses_s3_zip ? var.s3_key : null
  image_uri                      = local.uses_image ? var.image_uri : null
  handler                        = local.uses_image ? null : "app.lambda_handler.handler"
  runtime                        = local.uses_image ? null : "python3.12"
  architectures                  = [var.lambda_architecture]
  memory_size                    = var.memory_mb
  timeout                        = var.timeout_s
  reserved_concurrent_executions = var.reserved_concurrency
  publish                        = true
  tags                           = var.tags

  environment {
    variables = var.environment_vars
  }

  dynamic "snap_start" {
    for_each = var.enable_snapstart ? [1] : []

    content {
      apply_on = "PublishedVersions"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.this,
    aws_iam_role_policy.logs,
    terraform_data.artifact_validation,
  ]
}

resource "aws_lambda_alias" "live" {
  name             = "live"
  description      = "Live Lambda API version served by the Function URL."
  function_name    = aws_lambda_function.this.function_name
  function_version = aws_lambda_function.this.version
}

resource "aws_lambda_function_url" "live" {
  function_name      = aws_lambda_alias.live.function_name
  qualifier          = aws_lambda_alias.live.name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "function_url_public" {
  statement_id           = "AllowPublicFunctionUrlInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_alias.live.function_name
  principal              = "*"
  qualifier              = aws_lambda_alias.live.name
  function_url_auth_type = "NONE"
}

resource "terraform_data" "function_url_invoke_public_permission" {
  input = {
    function_name = aws_lambda_alias.live.function_name
    qualifier     = aws_lambda_alias.live.name
    statement_id  = "AllowPublicFunctionInvokeViaFunctionUrl"
  }

  triggers_replace = [
    aws_lambda_alias.live.function_name,
    aws_lambda_alias.live.name,
  ]

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      err_file="$(mktemp)"
      if aws lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --qualifier "$QUALIFIER" \
        --statement-id "$STATEMENT_ID" \
        --action lambda:InvokeFunction \
        --principal "*" \
        --invoked-via-function-url >/dev/null 2>"$err_file"; then
        rm -f "$err_file"
        exit 0
      fi
      if grep -q "ResourceConflictException" "$err_file"; then
        rm -f "$err_file"
        exit 0
      fi
      cat "$err_file" >&2
      rm -f "$err_file"
      exit 1
    EOT

    environment = {
      FUNCTION_NAME = self.input.function_name
      QUALIFIER     = self.input.qualifier
      STATEMENT_ID  = self.input.statement_id
    }
  }

  depends_on = [
    aws_lambda_function_url.live,
    aws_lambda_permission.function_url_public,
  ]
}
