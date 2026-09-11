# Lambda Function
resource "aws_lambda_function" "mywebsite" {
  function_name = "mywebsite"
  role          = aws_iam_role.mywebsite_lambda.arn
  handler       = "mywebsite.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 512

  # Hard cost ceiling. Without this the function scales to the account limit
  # (1000), so a request flood is billed as Lambda + DynamoDB + CloudWatch
  # with nothing capping the total: ~$737/day at full concurrency.
  #
  # API Gateway already throttles to 50 req/s (api-gateway.tf), but that
  # bounds the RATE, not the cost per request — if a page's duration rises
  # (a slow S3 list), the same rate consumes proportionally more GB-seconds.
  # This bounds the thing actually billed: 20 x 0.512GB x $0.0000166667/GB-s
  # x 86400s = ~$14.75/day absolute worst case.
  #
  # 20 is ~1000x observed usage: 1,981 invocations/day at ~0.5s is an average
  # concurrency near 0.01, and ConcurrentExecutions reports no datapoints at
  # all over 7 days. Headroom is for a gallery page firing several presigned
  # redirects at once, not for growth — raise it deliberately if real traffic
  # ever approaches it, because the failure mode is a 429 to a real visitor.
  reserved_concurrent_executions = 20

  # Dummy zip — actual deployment handled by ./deploy script
  filename         = "dummy.zip"
  source_code_hash = filebase64sha256("dummy.zip")

  lifecycle {
    ignore_changes = [
      filename,
      source_code_hash,
    ]
  }
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mywebsite.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.mywebsite.execution_arn}/*/*"
}

# CloudWatch Log Group for the Lambda.
#
# Created implicitly by Lambda on first invocation and had no retention until
# 2026-09-06 — it had grown to 674 MB covering 6.5 months. The full history was
# exported to s3://backup-peter/mywebsite-cloudwatch-logs/ and analysed
# (analysis/access-history/REPORT.md) before this was applied, because setting
# retention deletes the old data and cannot be undone.
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/mywebsite"
  retention_in_days = 30
}
