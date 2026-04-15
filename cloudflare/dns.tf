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
