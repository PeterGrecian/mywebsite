# mywebsite TODO

## Bugs

- Contents page: links change the location bar but not the contents
- Cloudflare purge appears faulty — investigate

## Active

- Better repo name and docs — this is the website publishing core; document how it works
- T3 logging: capture `stop` query param (parklands/surbiton) for usage breakdowns

## Future

### Logging: migrate from DynamoDB to CloudWatch

Current: Lambda → DynamoDB → manual export → S3.
Better: Lambda → CloudWatch Logs → S3 (→ Athena/Grafana).

CloudWatch already captures duration, memory, errors, prints. DynamoDB logging is redundant; free tier covers this volume easily.

### Lambda monolith

`mywebsite.py` is ~3600 lines, mostly dispatching to route modules in `lambda/routes/`. Full microservices split (one Lambda per service) would help independent scaling and deploys but is a big undertaking for marginal gain at current scale. Revisit if any single route becomes a bottleneck.
