# Cloudflare WAF — disabled for now (free tier has limitations on managed rulesets)
# Can be configured manually in the Cloudflare dashboard if needed
#
# Free tier limitations:
# - Managed Ruleset IDs change, not directly accessible via Terraform
# - Rate limiting requires cf.colo.id in characteristics (zone-level only)
#
# To enable WAF manually:
# 1. Cloudflare Dashboard → Security → WAF
# 2. Enable "Cloudflare Managed Ruleset" (free tier includes basic rules)
# 3. Security → Rate limiting → add rules as needed
