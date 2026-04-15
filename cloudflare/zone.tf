# Cloudflare zone for petergrecian.co.uk
resource "cloudflare_zone" "pg" {
  account_id = var.cloudflare_account_id
  zone       = var.domain
  plan       = "free"
}

# Zone settings: SSL, HTTPS, TLS, security
resource "cloudflare_zone_settings_override" "pg" {
  zone_id = cloudflare_zone.pg.id

  settings {
    # SSL/TLS
    ssl                      = "full"
    always_use_https         = "on"
    min_tls_version          = "1.2"
    opportunistic_encryption = "on"

    # Security
    security_level = "medium"

    # Caching
    browser_cache_ttl = 14400 # 4 hours
    cache_level       = "aggressive"
  }
}

# Outputs: Cloudflare nameservers to use at registrar
output "nameservers" {
  value       = cloudflare_zone.pg.name_servers
  description = "Cloudflare nameservers — update registrar to these"
}
