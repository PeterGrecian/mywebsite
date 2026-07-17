# DNS records for petergrecian.co.uk
# Critical: MX, TXT, DKIM records are NOT proxied (orange cloud OFF)
# Only www CNAME is proxied (blue cloud ON) to enable WAF/caching

locals {
  api_gw_cname = coalesce(
    var.api_gw_cname,
    try(data.terraform_remote_state.mywebsite.outputs.api_gateway_domain_name, null)
  )
}

# www CNAME → API Gateway (proxied through Cloudflare, enables WAF)
resource "cloudflare_record" "www" {
  zone_id = cloudflare_zone.pg.id
  name    = "www"
  type    = "CNAME"
  content = local.api_gw_cname
  ttl     = 1    # auto (when proxied)
  proxied = true # Enable Cloudflare WAF/caching
}

# Apex CNAME (flattened by Cloudflare to an A record) → API Gateway.
# Proxied so Cloudflare answers for the bare domain at all; requests are then
# 301-redirected to www by the apex_redirect ruleset below. We must give the
# apex a proxied record even though it only redirects, because a redirect rule
# can't fire on a hostname Cloudflare has no DNS record for. The origin itself
# 403s on a `petergrecian.co.uk` Host header (it only serves `www.`), so we
# never actually pass apex traffic through — the redirect intercepts first.
resource "cloudflare_record" "apex" {
  zone_id = cloudflare_zone.pg.id
  name    = "@"
  type    = "CNAME"
  content = local.api_gw_cname
  ttl     = 1    # auto (when proxied)
  proxied = true # required for CNAME flattening + redirect rule to apply
}

# Redirect the apex to www (canonical host). 301, preserves path + query.
resource "cloudflare_ruleset" "apex_redirect" {
  zone_id     = cloudflare_zone.pg.id
  name        = "Redirect apex to www"
  description = "301 petergrecian.co.uk/* -> https://www.petergrecian.co.uk/*"
  kind        = "zone"
  phase       = "http_request_dynamic_redirect"

  rules {
    action = "redirect"
    action_parameters {
      from_value {
        status_code = 301
        target_url {
          expression = "concat(\"https://www.petergrecian.co.uk\", http.request.uri.path)"
        }
        preserve_query_string = true
      }
    }
    expression  = "(http.host eq \"petergrecian.co.uk\")"
    description = "Apex to www canonical redirect"
  }
}

# MX record for email (NOT proxied — SES needs real DNS)
resource "cloudflare_record" "mx" {
  zone_id  = cloudflare_zone.pg.id
  name     = "@"
  type     = "MX"
  priority = 10
  content  = "inbound-smtp.eu-west-1.amazonaws.com"
  ttl      = 300
  proxied  = false
}

# SPF record (NOT proxied)
resource "cloudflare_record" "spf" {
  zone_id = cloudflare_zone.pg.id
  name    = "@"
  type    = "TXT"
  content = "v=spf1 include:amazonses.com ~all"
  ttl     = 300
  proxied = false
}

# Google site verification (NOT proxied)
resource "cloudflare_record" "google_verification" {
  zone_id = cloudflare_zone.pg.id
  name    = "@"
  type    = "TXT"
  content = var.google_site_verification
  ttl     = 300
  proxied = false
}

# SES domain verification TXT
resource "cloudflare_record" "ses_verification" {
  zone_id = cloudflare_zone.pg.id
  name    = "_amazonses"
  type    = "TXT"
  content = "petergrecian-rrds7fhs7d5nvhvvvvvv"  # placeholder; read from AWS if needed
  ttl     = 300
  proxied = false
}

# SES DKIM records (NOT proxied) — 3 CNAMEs
resource "cloudflare_record" "dkim" {
  count   = 3
  zone_id = cloudflare_zone.pg.id
  name    = "${var.dkim_tokens[count.index]}._domainkey"
  type    = "CNAME"
  content = "${var.dkim_tokens[count.index]}.dkim.amazonses.com"
  ttl     = 300
  proxied = false
}
