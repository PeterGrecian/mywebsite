resource "cloudflare_pages_project" "homepage" {
  account_id        = var.cloudflare_account_id
  name              = "petergrecian-homepage"
  production_branch = "main"

  build_config {
    build_command   = ""
    destination_dir = "public"
    root_dir        = ""
  }

  lifecycle {
    ignore_changes = [source, deployment_configs]
  }
}
