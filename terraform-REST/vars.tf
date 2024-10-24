variable "lambda_function_name" { type = string }
variable "source_module_name" { type = string }
variable "source_dir"   { type = string }
variable "lambda_handler" { 
    type = string
    default = "lambda_handler"
}
variable "domain" { type = string }

variable "aws_region" {
  type    = string
  default = "eu-west-1"
}
variable "log_retention_days" { default = 7 }