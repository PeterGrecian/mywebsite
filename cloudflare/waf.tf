# Cloudflare WAF — Managed Free Ruleset + Page Rules for rate limiting

# Deploy Cloudflare Managed Free Ruleset
# Provides protection against XSS, SQL injection, bots, DDoS
resource "cloudflare_ruleset" "managed_waf" {
  zone_id     = cloudflare_zone.pg.id
  name        = "Cloudflare Managed Free Ruleset"
  description = "Cloudflare Managed Ruleset for WAF (free tier)"
  kind        = "zone"
  phase       = "http_request_firewall_managed"

  rules {
    action = "execute"
    action_parameters {
      id = "77454fe2d30c4220b5701f6fdfb893ba" # Cloudflare Managed Free Ruleset
    }
    expression  = "true"
    description = "Execute Cloudflare Managed Free Ruleset"
  }
}

# Page Rules for enhanced security (free tier approach)
# /gardencam/capture — high security level
resource "cloudflare_page_rule" "gardencam_capture_rate_limit" {
  zone_id = cloudflare_zone.pg.id
  target  = "www.petergrecian.co.uk/gardencam/capture*"
  priority = 1

  actions {
    security_level = "high"
  }
}

# /pi-fleet — high security level
resource "cloudflare_page_rule" "pi_fleet_rate_limit" {
  zone_id = cloudflare_zone.pg.id
  target  = "www.petergrecian.co.uk/pi-fleet*"
  priority = 2

  actions {
    security_level = "high"
  }
}
