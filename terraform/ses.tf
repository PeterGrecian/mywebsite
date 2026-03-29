# Email forwarding: SES receives mail for petergrecian.co.uk,
# stores in S3, Lambda forwards to Gmail.

# ── SES Domain Identity ──────────────────────────────────────────────────────

resource "aws_ses_domain_identity" "pg" {
  domain = "petergrecian.co.uk"
}

resource "aws_ses_domain_dkim" "pg" {
  domain = aws_ses_domain_identity.pg.domain
}

# ── DNS Records ──────────────────────────────────────────────────────────────

# MX record — route inbound mail to SES
resource "aws_route53_record" "mx" {
  zone_id = data.aws_route53_zone.pg.zone_id
  name    = "petergrecian.co.uk"
  type    = "MX"
  ttl     = 300
  records = ["10 inbound-smtp.eu-west-1.amazonaws.com"]
}

# SPF — authorise SES to send on our behalf
# TXT records for the apex — SPF + existing Google site verification
# (Route 53 requires all TXT values in a single record set)
resource "aws_route53_record" "txt" {
  zone_id = data.aws_route53_zone.pg.zone_id
  name    = "petergrecian.co.uk"
  type    = "TXT"
  ttl     = 300
  records = [
    "v=spf1 include:amazonses.com ~all",
    "google-site-verification=Qje-T8_Z1XOZFjG1V9XWt-V7bR3TajOoaCJw7gopjM4",
  ]
}

# DKIM — three CNAME records for SES domain verification
resource "aws_route53_record" "dkim" {
  count   = 3
  zone_id = data.aws_route53_zone.pg.zone_id
  name    = "${aws_ses_domain_dkim.pg.dkim_tokens[count.index]}._domainkey.petergrecian.co.uk"
  type    = "CNAME"
  ttl     = 300
  records = ["${aws_ses_domain_dkim.pg.dkim_tokens[count.index]}.dkim.amazonses.com"]
}

# Domain verification TXT
resource "aws_route53_record" "ses_verification" {
  zone_id = data.aws_route53_zone.pg.zone_id
  name    = "_amazonses.petergrecian.co.uk"
  type    = "TXT"
  ttl     = 300
  records = [aws_ses_domain_identity.pg.verification_token]
}

# ── S3 Bucket for Inbound Mail ──────────────────────────────────────────────

resource "aws_s3_bucket" "email" {
  bucket = "petergrecian-email-eu-west-1"
}

resource "aws_s3_bucket_lifecycle_configuration" "email" {
  bucket = aws_s3_bucket.email.id

  rule {
    id     = "delete-after-7-days"
    status = "Enabled"

    expiration {
      days = 7
    }
  }
}

resource "aws_s3_bucket_policy" "email" {
  bucket = aws_s3_bucket.email.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "ses.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.email.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# ── Lambda: Email Forwarder ──────────────────────────────────────────────────

resource "aws_iam_role" "email_forwarder" {
  name = "email-forwarder-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "email_forwarder_logs" {
  role       = aws_iam_role.email_forwarder.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "email_forwarder" {
  name = "email-forwarder-policy"
  role = aws_iam_role.email_forwarder.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.email.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = "ses:SendRawEmail"
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "email_forwarder" {
  function_name = "email-forwarder"
  role          = aws_iam_role.email_forwarder.arn
  handler       = "email_forwarder.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128

  filename         = "dummy.zip"
  source_code_hash = filebase64sha256("dummy.zip")

  environment {
    variables = {
      FORWARD_TO  = "peter.grecian@gmail.com"
      MAIL_BUCKET = aws_s3_bucket.email.id
    }
  }

  lifecycle {
    ignore_changes = [
      filename,
      source_code_hash,
    ]
  }
}

resource "aws_lambda_permission" "ses_invoke" {
  statement_id  = "AllowSESInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.email_forwarder.function_name
  principal     = "ses.amazonaws.com"
  source_account = data.aws_caller_identity.current.account_id
}

# ── SES Receipt Rule ────────────────────────────────────────────────────────

resource "aws_ses_receipt_rule_set" "main" {
  rule_set_name = "petergrecian-rules"
}

resource "aws_ses_active_receipt_rule_set" "main" {
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
}

resource "aws_ses_receipt_rule" "forward" {
  name          = "forward-to-gmail"
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
  enabled       = true
  scan_enabled  = true
  recipients    = ["petergrecian.co.uk"]

  s3_action {
    bucket_name = aws_s3_bucket.email.id
    position    = 1
  }

  lambda_action {
    function_arn    = aws_lambda_function.email_forwarder.arn
    invocation_type = "Event"
    position        = 2
  }
}
