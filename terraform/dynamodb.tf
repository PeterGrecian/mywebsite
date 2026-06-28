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

# Astro storage inventory — one item per (night x location). Records where
# each camera-night's data physically lives across hot/warm/cold tiers.
# Replaces ~/astro/whereisallthedata.csv as the source of truth so the web
# Lambda can read it (a CSV on a workstation can't be reached). See
# astro/design/storage-status-and-inventory.md.
resource "aws_dynamodb_table" "astro_storage_inventory" {
  name         = "astro-storage-inventory"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "night"
  range_key    = "loc" # camera#host#path

  attribute {
    name = "night"
    type = "S"
  }

  attribute {
    name = "loc"
    type = "S"
  }

  attribute {
    name = "storage_class"
    type = "S"
  }

  # "what's still local" / "what's in deep-archive" without a full scan.
  global_secondary_index {
    name            = "by-storage-class"
    hash_key        = "storage_class"
    range_key       = "night"
    projection_type = "ALL"
  }
}

# Astro per-host disk capacity — one item per (host x filesystem), refreshed
# by a per-host reporter cron. Drives the capacity bars on /astro/storage.
resource "aws_dynamodb_table" "astro_host_capacity" {
  name         = "astro-host-capacity"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "host"
  range_key    = "fs"

  attribute {
    name = "host"
    type = "S"
  }

  attribute {
    name = "fs"
    type = "S"
  }
}
