# mywebsite TODO

Updated 2026-04-18. Hybrid Cloudflare Pages (static/PWA) + Lambda (API) architecture is live.

## Done

- [x] Cloudflare Pages deployment (wrangler.toml, public/, _redirects)
- [x] PWA homepage with icons, manifest, service worker
- [x] Cloudflare edge caching + WAF rules
- [x] Route extraction — 14 modules in lambda/routes/, mywebsite.py is now a dispatcher
- [x] Skycam video browsing + Chromecast player

## Active issues

- [ ] Claude usage page not loading (cleft works fine — why?)
- [ ] Claude usage: add "last refreshed" clock + manual refresh button
- [ ] Better repo name/docs — this is the website publishing core, document how it works

## Future

### Logging: migrate from DynamoDB to CloudWatch
**Current**: Lambda → DynamoDB → manual export → S3
**Better**: Lambda → CloudWatch Logs → S3 (→ Athena/Grafana)

CloudWatch already captures everything (duration, memory, errors, prints). DynamoDB logging is redundant. Free tier covers this volume easily.

### Lambda monolith
mywebsite.py is still 3643 lines but now mostly dispatching to route modules. Full microservices split (separate Lambdas per service) would help independent scaling and deploys but is a big undertaking for marginal gain at current scale. Revisit if any single route becomes a bottleneck.

### T3 logging
Capture query parameters (stop=parklands/surbiton) in logs for usage breakdowns.
