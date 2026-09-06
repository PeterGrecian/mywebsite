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

# ---------------------------------------------------------------------------
# Scanner blocking (added 2026-09-06)
#
# Why: on 2026-09-06 a single host (185.177.72.67) sent ~2,600 requests in ten
# minutes — a flat ~255/min from 07:21 to 07:30 BST. Every one reached Lambda
# and rendered the 404 page, taking `mywebsite` from its ~60/hour baseline to
# 2,683 in the hour and pushing peak concurrency to 56. Nothing broke (zero
# errors, zero throttles) but the site was slow while it ran, and the whole
# burst was probes for software this site does not run: .env files, .git
# config, WordPress, phpMyAdmin, the Docker daemon API, Grafana, MLflow,
# Jupyter and an F5 BIG-IP file-read exploit.
#
# The managed free ruleset above did not stop it — it targets injection and
# known-bad payloads, not path enumeration against a site with no PHP.
#
# Two rules, deliberately layered:
#   1. A path blocklist, which is exact and cannot touch a real visitor.
#   2. A rate limit, which is general and catches the next scanner that
#      probes paths nobody has thought of yet.
#
# Free plan allows 5 custom rules and 1 rate-limiting rule; this uses 2 of 5
# and the single rate-limit slot. Unlike the page rules in this file, custom
# rules and rate limits are separate quotas — they do not consume the three
# page-rule slots that dns.tf's apex redirect competes for.
# ---------------------------------------------------------------------------

resource "cloudflare_ruleset" "scanner_block" {
  zone_id     = cloudflare_zone.pg.id
  name        = "Block vulnerability scanners"
  description = "Drop probes for software this site does not run, before Lambda"
  kind        = "zone"
  phase       = "http_request_firewall_custom"

  # Every pattern below was observed in the 2026-09-06 burst or is the
  # obvious sibling of one. None of them can match a real route: the site's
  # paths are listed in mywebsite/README.md and none contains a dot-file, a
  # script extension, or a "wp-" segment. `/api` IS a real route here, so
  # the API probes are matched by their full path, never by an `/api/` prefix.
  rules {
    action      = "block"
    description = "Dotfiles, script extensions and known scanner endpoints"
    enabled     = true
    expression  = <<-EOT
      (lower(http.request.uri.path) contains ".env")
      or (lower(http.request.uri.path) contains ".git")
      or (lower(http.request.uri.path) contains ".svn")
      or (lower(http.request.uri.path) contains ".ssh")
      or (lower(http.request.uri.path) contains ".aws")
      or (lower(http.request.uri.path) contains ".htaccess")
      or (lower(http.request.uri.path) contains ".php")
      or (lower(http.request.uri.path) contains ".jsp")
      or (lower(http.request.uri.path) contains ".asp")
      or (lower(http.request.uri.path) contains "wp-")
      or (lower(http.request.uri.path) contains "phpmyadmin")
      or (lower(http.request.uri.path) contains "xmlrpc")
      or (lower(http.request.uri.path) contains "/cgi-bin/")
      or (lower(http.request.uri.path) contains "/vendor/")
      or (lower(http.request.uri.path) contains "/_profiler/")
      or (lower(http.request.uri.path) contains "/actuator")
      or (lower(http.request.uri.path) contains "sendgrid.json")
      or (lower(http.request.uri.path) contains "config.json")
      or (lower(http.request.uri.path) contains "/containers/json")
      or (lower(http.request.uri.path) contains "/images/json")
      or (lower(http.request.uri.path) contains "/api/datasources")
      or (lower(http.request.uri.path) contains "/mlflow/")
      or (lower(http.request.uri.path) contains "/tmui/")
    EOT
  }
}

# The general backstop. The blocklist above only knows the probes we have
# already seen; this one only cares about volume, so it catches the next
# scanner regardless of which paths it invents.
#
# Threshold: the burst ran at ~4.2 req/s from one IP. A real visitor loading
# a gallery page issues a burst of thumbnail requests too, which is why the
# expression excludes image and video paths — those are S3-backed and served
# from cache, so they are not what we are protecting. What is left is HTML
# page views, where 40 in 10 seconds from one address is not a person.
resource "cloudflare_ruleset" "rate_limit" {
  zone_id     = cloudflare_zone.pg.id
  name        = "Rate limit page requests per IP"
  description = "Backstop against request floods that the path blocklist misses"
  kind        = "zone"
  phase       = "http_ratelimit"

  rules {
    action      = "block"
    description = "20 page requests per 10s per IP"
    enabled     = true
    # No regex here: the free plan refuses the `matches` operator outright
    # ("an higher Advanced Rate Limiting plan is required"), so the asset
    # exclusion is spelled out with `contains`.
    #
    # What this exclusion actually covers, corrected 2026-09-06: only the
    # routes where the Lambda answers with a 302 to a presigned S3 URL —
    # /thumbs/ and the /*/fullres set. Those do arrive in bursts and are
    # worth excluding. The astro gallery pages do NOT: they embed the
    # presigned S3 URL directly in the img src, on the bucket's own
    # amazonaws.com hostname, so those image requests never reach Cloudflare
    # or Lambda at all and were never counted by this rule in the first
    # place. The exclusion is narrower in effect than it looks — harmless,
    # but do not read it as "galleries are protected".
    #
    # That split is itself the inefficiency: the 7.4 MB an astro page pulls
    # bypasses the CDN entirely and is re-fetched on every view, because the
    # presigned signature changes per render. See the strand IDEAS spool.
    expression  = <<-EOT
      not (http.request.uri.path contains "/thumbs/"
           or http.request.uri.path contains "/fullres"
           or http.request.uri.path contains ".jpg"
           or http.request.uri.path contains ".jpeg"
           or http.request.uri.path contains ".png"
           or http.request.uri.path contains ".gif"
           or http.request.uri.path contains ".webp"
           or http.request.uri.path contains ".svg"
           or http.request.uri.path contains ".ico"
           or http.request.uri.path contains ".mp4"
           or http.request.uri.path contains ".webm"
           or http.request.uri.path contains ".css"
           or http.request.uri.path contains ".js")
    EOT

    ratelimit {
      characteristics = ["ip.src", "cf.colo.id"]
      period          = 10

      # 20 non-asset requests per 10s per IP. Two constraints set this number.
      # The free plan forces mitigation_timeout == period == 10, so a blocked
      # client is released after ten seconds and the rule is a sustained-rate
      # cap rather than a ban: the effective ceiling is requests_per_period/10
      # per second. The 2026-09-06 scanner ran at ~4.2/s, so a threshold of 40
      # would have been a ceiling it was already under and would have done
      # nothing. 20 caps a single address at 2 HTML page-views per second,
      # which no human reaches and which leaves the once-a-minute
      # /calendaralarm/api/rules poller on pip untouched.
      requests_per_period = 20
      mitigation_timeout  = 10
    }
  }
}
