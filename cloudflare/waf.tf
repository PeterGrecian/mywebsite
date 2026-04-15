# Cloudflare WAF — free tier managed rules + custom rate limiting

# Deploy Cloudflare Managed Ruleset
resource "cloudflare_ruleset" "managed_waf" {
  zone_id     = cloudflare_zone.pg.id
  name        = "Cloudflare Managed Ruleset"
  description = "Cloudflare Managed Ruleset for WAF"
  kind        = "zone"
  phase       = "http_request_firewall_managed"

  rules {
    action = "execute"
    action_parameters {
      id = "efb7b8c949ac4650a09736fc376e9adb" # Cloudflare Managed Ruleset ID
    }
    expression = "true"
    description = "Execute Cloudflare Managed Ruleset"
  }
}

# Rate limiting ruleset
resource "cloudflare_ruleset" "rate_limiting" {
  zone_id     = cloudflare_zone.pg.id
  name        = "Rate Limiting"
  description = "Rate limiting for expensive endpoints"
  kind        = "zone"
  phase       = "http_ratelimit"

  # /gardencam/capture POST — 10 requests per minute per IP
  rules {
    action = "challenge"
    ratelimit {
      characteristics = [
        "ip.src"
      ]
      counting_expression = "true"
      mitigation_timeout  = 60
      period              = 60
      requests_per_period = 10
      requests_to_origin  = false
    }
    expression = "request.uri.path contains \"/gardencam/capture\" and http.request.method == \"POST\""
    description = "Rate limit: /gardencam/capture POST"
  }

  # /pi-fleet — 30 requests per minute per IP
  rules {
    action = "challenge"
    ratelimit {
      characteristics = [
        "ip.src"
      ]
      counting_expression = "true"
      mitigation_timeout  = 60
      period              = 60
      requests_per_period = 30
      requests_to_origin  = false
    }
    expression = "request.uri.path contains \"/pi-fleet\""
    description = "Rate limit: /pi-fleet"
  }
}
