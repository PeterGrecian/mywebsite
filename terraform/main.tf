provider "aws" {
  region = "eu-west-1"
}

terraform {
  backend "s3" {}
}

data "aws_route53_zone" "pg" {
  name         = "petergrecian.co.uk."
  private_zone = false
}

data "aws_caller_identity" "current" {}
