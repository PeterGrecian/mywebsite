# Visitor digest — sends each visitor alert once the visit is over, with the
# pages it saw (lambda/visitor_digest.py). Separate from the web Lambda so the
# site's role never gains read access to its own logs, and so this role can do
# nothing but read those logs and the contents table, and work the visitor-alerts
# table. The code ships with terraform apply, not ./deploy.
#
# Cost: 96 invocations a day and, on a day with visitors, a few short log
# filters. Inside the free tier; under $0.01/month if it were not.

data "archive_file" "visitor_digest" {
  type        = "zip"
  source_file = "${path.module}/../lambda/visitor_digest.py"
  output_path = "${path.module}/.build/visitor_digest.zip"
}

resource "aws_iam_role" "visitor_digest" {
  name = "visitor-digest-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "visitor_digest" {
  name = "visitor-digest"
  role = aws_iam_role.visitor_digest.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:Query", "dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.visitor_alerts.arn
      },
      {
        # Which pages are private: the same flag /contents filters on.
        Effect   = "Allow"
        Action   = ["dynamodb:Scan"]
        Resource = "arn:aws:dynamodb:eu-west-1:${data.aws_caller_identity.current.account_id}:table/mywebsite-contents"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:FilterLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.visitor_digest.arn}:*"
      },
    ]
  })
}

resource "aws_cloudwatch_log_group" "visitor_digest" {
  name              = "/aws/lambda/visitor-digest"
  retention_in_days = 14
}

resource "aws_lambda_function" "visitor_digest" {
  function_name    = "visitor-digest"
  role             = aws_iam_role.visitor_digest.arn
  handler          = "visitor_digest.lambda_handler"
  runtime          = "python3.12"
  timeout          = 120
  memory_size      = 128
  filename         = data.archive_file.visitor_digest.output_path
  source_code_hash = data.archive_file.visitor_digest.output_base64sha256

  # One at a time; a second run could only repeat the first's work.
  reserved_concurrent_executions = 1

  depends_on = [aws_cloudwatch_log_group.visitor_digest]
}

resource "aws_cloudwatch_event_rule" "visitor_digest" {
  name                = "visitor-digest"
  description         = "Send visitor alerts for visits that have finished"
  schedule_expression = "rate(15 minutes)"
}

resource "aws_cloudwatch_event_target" "visitor_digest" {
  rule = aws_cloudwatch_event_rule.visitor_digest.name
  arn  = aws_lambda_function.visitor_digest.arn
}

resource "aws_lambda_permission" "visitor_digest_schedule" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.visitor_digest.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.visitor_digest.arn
}
