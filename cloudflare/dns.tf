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

# Redirect the apex to www (canonical host). 301, preserves the path.
#
# This is a Page Rule, not the Redirect Rule (`http_request_dynamic_redirect`
# ruleset) you would reach for today. The reason is permissions, not taste:
# the Terraform token can edit Cache Rules and the WAF but is refused on the
# dynamic-redirect phase ("request is not authorized"), and the permission
# group for it could not be located in Cloudflare's token editor. Page Rules
# the token can already write — two of them are managed in waf.tf.
#
# Cost of the workaround: this takes the free plan's LAST page-rule slot
# (3 total; the other two are the rate limits in waf.tf). If you ever need a
# fourth page rule, that is the moment to go back and find the redirect
# permission — swap this resource for a `cloudflare_ruleset` on phase
# `http_request_dynamic_redirect` with a `redirect` action, and the slot
# comes back. Page Rules are Cloudflare's legacy mechanism and will
# eventually be retired, so treat this as owed work, not a resting place.
resource "cloudflare_page_rule" "apex_redirect" {
  zone_id  = cloudflare_zone.pg.id
  target   = "petergrecian.co.uk/*" # apex only — www is matched separately
  priority = 3                      # 1 and 2 are the waf.tf rate limits

  actions {
    forwarding_url {
      url         = "https://www.petergrecian.co.uk/$1"
      status_code = 301
    }
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
  content = "petergrecian-rrds7fhs7d5nvhvvvvvv" # placeholder; read from AWS if needed
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

# ACM DNS validation for *.petergrecian.co.uk (terraform/vars.tf:acm_certificate_arn).
# Permanent: ACM re-checks this same name at every renewal, so it must not be
# removed once the cert is issued. Its absence stalled the Oct 2026 renewal
# (AWS Health AWS_ACM_RENEWAL_STATE_CHANGE, 11 Sep 2026) — the record was lost
# when the zone came under Cloudflare/Terraform management.
resource "cloudflare_record" "acm_validation" {
  zone_id = cloudflare_zone.pg.id
  name    = "_4c15b1e7551c0756cff18f2d8cb4f886"
  type    = "CNAME"
  content = "_ce13797c1076e978733e8078162b79d8.djqtsrsxkq.acm-validations.aws."
  ttl     = 300
  proxied = false # must be real DNS — ACM resolves it directly
}
