variable "cloudflare_api_token" {
  description = "Cloudflare scoped API token (zone-level: DNS, Cache Purge, Zone Settings, WAF)"
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID"
  type        = string
  default     = "49363caa0ef13c5b8e98b769eab5a6f7"
}

variable "domain" {
  description = "Root domain"
  type        = string
  default     = "petergrecian.co.uk"
}

variable "api_gw_cname" {
  description = "API Gateway regional domain name (can also read from remote state)"
  type        = string
  default     = null
}

# DKIM tokens from SES (3 tokens)
variable "dkim_tokens" {
  description = "SES DKIM tokens for DNS CNAME records"
  type        = list(string)
  default = [
    "cbqidsomkjqxzymobczuqmtnl2x72fw7",
    "rq2c5zykwlhriq7a2uqwdzdleyzcjy5x",
    "6fgspbagtehhjcfcwxodu6e7tw3u5e55",
  ]
}

variable "google_site_verification" {
  description = "Google site verification token"
  type        = string
  default     = "google-site-verification=Qje-T8_Z1XOZFjG1V9XWt-V7bR3TajOoaCJw7gopjM4"
}
