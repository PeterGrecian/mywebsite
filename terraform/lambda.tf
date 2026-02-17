# Lambda Function
resource "aws_lambda_function" "mywebsite" {
  function_name = "mywebsite"
  role          = aws_iam_role.mywebsite_lambda.arn
  handler       = "mywebsite.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128

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
