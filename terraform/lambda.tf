# Lambda Function
resource "aws_lambda_function" "mywebsite" {
  function_name = "mywebsite"
  role          = aws_iam_role.mywebsite_lambda.arn
  handler       = "mywebsite.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 512

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
