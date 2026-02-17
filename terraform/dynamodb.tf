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
