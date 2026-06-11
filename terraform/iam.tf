# IAM Role for Lambda
resource "aws_iam_role" "mywebsite_lambda" {
  name = "mywebsite-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Basic Lambda execution (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.mywebsite_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# DynamoDB access — shared data stores (read) + mywebsite-contents (read)
resource "aws_iam_role_policy" "dynamodb_read" {
  name = "dynamodb-read"
  role = aws_iam_role.mywebsite_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          "arn:aws:dynamodb:eu-west-1:${data.aws_caller_identity.current.account_id}:table/pi-fleet-status",
          "arn:aws:dynamodb:eu-west-1:${data.aws_caller_identity.current.account_id}:table/gardencam-stats",
          "arn:aws:dynamodb:eu-west-1:${data.aws_caller_identity.current.account_id}:table/gardencam-page-timing",
          "arn:aws:dynamodb:eu-west-1:${data.aws_caller_identity.current.account_id}:table/gardencam-video-metadata",
          "arn:aws:dynamodb:eu-west-1:${data.aws_caller_identity.current.account_id}:table/mywebsite-contents",
          "arn:aws:dynamodb:eu-west-1:${data.aws_caller_identity.current.account_id}:table/hits",
        ]
      }
    ]
  })
}

# DynamoDB write access — access logs, execution logs, gardencam commands
resource "aws_iam_role_policy" "dynamodb_write" {
  name = "dynamodb-write"
  role = aws_iam_role.mywebsite_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          "arn:aws:dynamodb:eu-west-1:${data.aws_caller_identity.current.account_id}:table/cv-access-logs",
          "arn:aws:dynamodb:eu-west-1:${data.aws_caller_identity.current.account_id}:table/lambda-execution-logs",
          "arn:aws:dynamodb:eu-west-1:${data.aws_caller_identity.current.account_id}:table/gardencam-commands",
          "arn:aws:dynamodb:eu-west-1:${data.aws_caller_identity.current.account_id}:table/ai-usage",
        ]
      }
    ]
  })
}

# S3 access — gardencam bucket
resource "aws_iam_role_policy" "s3_gardencam" {
  name = "s3-gardencam"
  role = aws_iam_role.mywebsite_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject"
        ]
        Resource = [
          "arn:aws:s3:::gardencam-berrylands-eu-west-1",
          "arn:aws:s3:::gardencam-berrylands-eu-west-1/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "s3_starcam" {
  name = "s3-starcam"
  role = aws_iam_role.mywebsite_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::starcam-berrylands-eu-west-1",
          "arn:aws:s3:::starcam-berrylands-eu-west-1/*"
        ]
      }
    ]
  })
}

# Unified astro deliverables bucket (unify-cameras): <camera>/nights/<date>/
resource "aws_iam_role_policy" "s3_astro" {
  name = "s3-astro"
  role = aws_iam_role.mywebsite_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::astro-berrylands-eu-west-1",
          "arn:aws:s3:::astro-berrylands-eu-west-1/*"
        ]
      }
    ]
  })
}

# SSM Parameter Store access
resource "aws_iam_role_policy" "ssm_parameters" {
  name = "ssm-parameters"
  role = aws_iam_role.mywebsite_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:eu-west-1:${data.aws_caller_identity.current.account_id}:parameter/berrylands/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:PutParameter"
        ]
        Resource = "arn:aws:ssm:eu-west-1:${data.aws_caller_identity.current.account_id}:parameter/ai-config/*"
      },
      {
        Effect = "Allow"
        Action = "kms:Decrypt"
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "ssm.eu-west-1.amazonaws.com"
          }
        }
      }
    ]
  })
}

# Secrets Manager access (gardencam password)
resource "aws_iam_role_policy" "secrets" {
  name = "secrets-access"
  role = aws_iam_role.mywebsite_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "secretsmanager:GetSecretValue"
        Resource = [
          "arn:aws:secretsmanager:eu-west-1:${data.aws_caller_identity.current.account_id}:secret:gardencam/password-*",
          "arn:aws:secretsmanager:eu-west-1:${data.aws_caller_identity.current.account_id}:secret:tfl/api-key-*",
          "arn:aws:secretsmanager:eu-west-2:${data.aws_caller_identity.current.account_id}:secret:gardencam/password-*",
        ]
      }
    ]
  })
}

# CloudWatch metrics access (for lambda-stats page)
resource "aws_iam_role_policy" "cloudwatch" {
  name = "cloudwatch-metrics"
  role = aws_iam_role.mywebsite_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:ListFunctions"
        ]
        Resource = "*"
      }
    ]
  })
}

# Bedrock access — for AI provider switching
resource "aws_iam_role_policy" "bedrock" {
  name = "bedrock-invoke"
  role = aws_iam_role.mywebsite_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = "arn:aws:bedrock:eu-west-1::foundation-model/*"
      }
    ]
  })
}
