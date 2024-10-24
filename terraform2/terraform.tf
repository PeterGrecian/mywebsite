terraform {

  backend "s3" {
    bucket = "grecian-terraform-state"
    key    = "cv-experiment"
    region = "eu-west-1"
  }

}
