# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

terraform {

  backend "s3" {
    bucket = "grecian-terraform-state"
    key    = "learn-terraform-lambda-api-gateway"
    region = "eu-west-1"
  }

}
