# Cache rules for static routes — avoids Lambda invocations for content
# that rarely changes. Cloudflare edge caches these responses and serves
# them directly until the TTL expires.
#
# Routes cached:
#   /cv, /gitinfo, /robots.txt — pure static (file reads, no AWS calls)
#   /contents                  — DynamoDB-driven but changes infrequently

resource "cloudflare_ruleset" "cache_rules" {
  zone_id     = cloudflare_zone.pg.id
  name        = "Cache rules for static routes"
  description = "Cache static and slow-changing routes at the edge"
  kind        = "zone"
  phase       = "http_request_cache_settings"

  # /cv — static HTML, changes only on deploy
  rules {
    action = "set_cache_settings"
    action_parameters {
      cache = true
      edge_ttl {
        mode    = "override_origin"
        default = 86400 # 24 hours
      }
      browser_ttl {
        mode    = "override_origin"
        default = 3600 # 1 hour — visitor gets fresh-ish content
      }
    }
    expression  = "(http.request.uri.path eq \"/cv\")"
    description = "Cache CV page — 24h edge, 1h browser"
  }

  # /gitinfo — static HTML, changes only on deploy
  rules {
    action = "set_cache_settings"
    action_parameters {
      cache = true
      edge_ttl {
        mode    = "override_origin"
        default = 86400
      }
      browser_ttl {
        mode    = "override_origin"
        default = 3600
      }
    }
    expression  = "(http.request.uri.path eq \"/gitinfo\")"
    description = "Cache gitinfo page — 24h edge, 1h browser"
  }

  # /robots.txt — hardcoded string, never changes between deploys
  rules {
    action = "set_cache_settings"
    action_parameters {
      cache = true
      edge_ttl {
        mode    = "override_origin"
        default = 604800 # 7 days
      }
      browser_ttl {
        mode    = "override_origin"
        default = 86400
      }
    }
    expression  = "(http.request.uri.path eq \"/robots.txt\")"
    description = "Cache robots.txt — 7d edge, 24h browser"
  }

  # /contents — reads DynamoDB but only changes when you run sync-contents.py
  rules {
    action = "set_cache_settings"
    action_parameters {
      cache = true
      edge_ttl {
        mode    = "override_origin"
        default = 3600 # 1 hour
      }
      browser_ttl {
        mode    = "override_origin"
        default = 300 # 5 minutes
      }
    }
    expression  = "(http.request.uri.path eq \"/contents\")"
    description = "Cache contents page — 1h edge, 5m browser"
  }
}
