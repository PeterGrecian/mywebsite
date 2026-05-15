# mywebsite TODO

## Bugs

- Contents page: links change the location bar but not the contents
- Cloudflare purge appears faulty — investigate

## Active

- **Skycam player: cast loop on Chromecast.** `<video loop>` works in
  the browser fine. Cast doesn't. Tried (1) `mediaInfo.loop = true`,
  (2) one-item Queue with `RepeatMode.ALL`, (3) JS listener for
  IDLE/FINISHED → re-`loadMedia()` — none worked on the test device
  (one-shot, then stops). Reverted to plain one-shot cast (no overlay).
  Worth investigating: which DMR receiver app the Chromecast is using;
  whether a custom CAF receiver (own app ID) would help; whether a
  Chromecast Ultra vs Google TV vs older v2 differs.
- Better repo name and docs — this is the website publishing core; document how it works
- T3 logging: capture `stop` query param (parklands/surbiton) for usage breakdowns
- Retire `newhome.petergrecian.co.uk` — was the PWA test subdomain, test is over.
  Remove the custom domain from the `petergrecian-homepage` Pages project
  (API: DELETE /accounts/:id/pages/projects/petergrecian-homepage/domains/newhome.petergrecian.co.uk).
  Note: this kills the only currently-installable PWA entry point. If we want a
  PWA at `www.petergrecian.co.uk`, the `/` route would need to be moved from
  Lambda to Pages — bigger change, decide separately.

## Future

### Logging: migrate from DynamoDB to CloudWatch

Current: Lambda → DynamoDB → manual export → S3.
Better: Lambda → CloudWatch Logs → S3 (→ Athena/Grafana).

CloudWatch already captures duration, memory, errors, prints. DynamoDB logging is redundant; free tier covers this volume easily.

### Lambda monolith

`mywebsite.py` is ~3600 lines, mostly dispatching to route modules in `lambda/routes/`. Full microservices split (one Lambda per service) would help independent scaling and deploys but is a big undertaking for marginal gain at current scale. Revisit if any single route becomes a bottleneck.
