# API Gateway HTTP API
resource "aws_apigatewayv2_api" "mywebsite" {
  name          = "mywebsite-api"
  protocol_type = "HTTP"
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.mywebsite.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
    format = jsonencode({
      httpMethod              = "$context.httpMethod"
      integrationErrorMessage = "$context.integrationErrorMessage"
      protocol                = "$context.protocol"
      requestId               = "$context.requestId"
      requestTime             = "$context.requestTime"
      resourcePath            = "$context.resourcePath"
      responseLength          = "$context.responseLength"
      routeKey                = "$context.routeKey"
      sourceIp                = "$context.identity.sourceIp"
      status                  = "$context.status"
    })
  }

  default_route_settings {
    detailed_metrics_enabled = false
    throttling_burst_limit   = 100
    throttling_rate_limit    = 50
  }
}

# API Gateway Integration with Lambda
resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.mywebsite.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.mywebsite.invoke_arn

  integration_method     = "POST"
  payload_format_version = "1.0"
  timeout_milliseconds   = 30000
}

# API Gateway Default Route
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.mywebsite.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gw" {
  name              = "/aws/api_gw/mywebsite-api"
  retention_in_days = 14
}
