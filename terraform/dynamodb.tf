# Site contents table — drives the navigation/contents page
resource "aws_dynamodb_table" "mywebsite_contents" {
  name         = "mywebsite-contents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "path"

  attribute {
    name = "path"
    type = "S"
  }
}

# AI usage metering — tracks every ai_client call
resource "aws_dynamodb_table" "ai_usage" {
  name         = "ai-usage"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "date"
  range_key    = "timestamp"

  attribute {
    name = "date"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}
