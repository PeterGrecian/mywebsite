terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }

  backend "s3" {}
}

provider "aws" {
  region = "eu-west-1"
}

provider "cloudflare" {
  api_key = var.cloudflare_api_key
  email   = var.cloudflare_email
}

# Read existing mywebsite Terraform state to get API Gateway CNAME target
data "terraform_remote_state" "mywebsite" {
  backend = "s3"

  config = {
    bucket = "tfstate-petergrecian"
    key    = "mywebsite-tfstate"
    region = "eu-west-1"
  }
}
