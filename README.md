# mywebsite

The Lambda serving **[www.petergrecian.co.uk](https://www.petergrecian.co.uk)** —
Peter's personal site and technical showcase. A single Python Lambda behind API
Gateway (HTTP API v2), fronted by Cloudflare for DNS, WAF, rate limiting, and
edge caching. It publishes a CV plus a growing set of small applications
(garden/sky/star cameras, a Pi-fleet dashboard, bus times, Lambda cost stats,
and more).

> **Not the `cv` repo.** `~/cv` is a separate, older codebase (`cv.py`,
> `./update`, Lambda `cvdev`, `w3.petergrecian.co.uk`). This repo is
> `lambda/mywebsite.py`, `./deploy`, Lambda `mywebsite`,
> `www.petergrecian.co.uk`. They coexist during migration and share some data
> stores — see [mywebsite vs cv](#mywebsite-vs-cv) below. Edit and deploy the
> right one.

## Architecture

```
Cloudflare (DNS + WAF + rate limit + edge cache)
    │  proxied CNAME  www → API Gateway
    ▼
API Gateway (HTTP API v2, mywebsite-api)
    ▼
Lambda  mywebsite  (Python 3.12)  ── lambda/mywebsite.py
    │       dispatches most paths to route modules in lambda/routes/
    ├── DynamoDB   contents, fleet status, gardencam stats/commands, exec logs
    ├── S3         gardencam / camera image buckets
    └── SES        peter@petergrecian.co.uk → Gmail forwarding
```

- **Handler:** `lambda/mywebsite.py` (`lambda_handler`). ~3600 lines; the top is
  a big path dispatch that delegates most applications to modules under
  `lambda/routes/` (`astro.py`, `camera.py`, `gardencam.py`, `pi_fleet.py`,
  `t3.py`, `lambda_stats.py`, `stereo.py`, `memspeed.py`, `srfcplus.py`, …).
  HTML templates live in `lambda/templates/`.
- **Paths are stage-tolerant:** every route matches both `/{stage}/foo` and
  `/foo` so it works whether or not API Gateway prepends a stage prefix.
- **AWS region:** eu-west-1 (Ireland).
- **Infra as code:** `terraform/` (AWS: Lambda, API Gateway, DynamoDB, SES) and
  `cloudflare/` (DNS, WAF, cache — **separate** Terraform state,
  `cloudflare-tfstate`).

## Routes

The route set grows over time; this is the shape, not an exhaustive list (grep
`lambda/mywebsite.py` for the authoritative dispatch).

| Path | What it serves |
|---|---|
| `/` | CV (default) — renders `lambda/cv.html` |
| `/contents` | Data-driven navigation page (reads DynamoDB `mywebsite-contents`) |
| `/gitinfo` | Git commit of the deployed code (generated at deploy time) |
| `/event` | Debug: raw Lambda event/context |
| `/robots.txt` | Static robots file |
| `/gardencam*` | Garden camera: latest images, gallery, stats, remote capture (POST `/gardencam/capture`) — password protected |
| `/springcam*`, `/skycam*`, `/starcam*` | Other cameras: galleries, timelapses, video players (incl. Chromecast) |
| `/astro*` | Astro pages (starcam night index, storage view) |
| `/pi-fleet` | Raspberry Pi fleet status dashboard |
| `/t3` | K2 bus arrivals (TfL) — redundant, see note below |
| `/lambda-stats` | Lambda execution metrics and free-tier / cost tracking |
| `/glacier` | Private cold-archive contents page |
| `/memspeed` | Memory/upload-download speed test toy |
| `/stereo`, `/manim`, `/gotg`, `/rcr`, `/us-vs-the-machines`, `/srfcplus` | Misc project pages/showcases |

## Deployment

```bash
./deploy                          # build + deploy Lambda code, then purge CF cache
terraform -chdir=terraform apply  # AWS infrastructure changes
python tools/sync-contents.py     # push /contents navigation data to DynamoDB
```

`./deploy`:
1. `py_compile`s `lambda/mywebsite.py`.
2. Generates `lambda/gitinfo.html` from the current commit (served at `/gitinfo`,
   so you can confirm which commit is live).
3. Zips `lambda/` (code, HTML, images, `routes/`, `templates/`) into
   `mywebsite.zip`.
4. `aws lambda update-function-code --function-name mywebsite`, waits for
   update, sets the handler.
5. Purges the Cloudflare edge cache (scoped `/cloudflare/purge-token`;
   `purge_everything`) so cached routes serve fresh content.

Typical loop: edit → `./deploy` → verify at the URL and check `/gitinfo` →
`git commit` → `git push`. (GitHub Actions is possible but slower than the
direct deploy, so the script is preferred.)

## Site contents (`/contents`)

Data-driven navigation:
- **Source of truth:** `site-contents.json` in this repo.
- **Sync to DynamoDB:** `python tools/sync-contents.py` → table
  `mywebsite-contents` (partition key `path`).
- **Destructive full replace:** any DynamoDB row whose `path` is not in the
  JSON is deleted. Never edit the table directly — edit the JSON and re-sync, or
  your change is silently wiped on the next sync.

## Cloudflare

DNS/WAF/cache is separate Terraform in `cloudflare/` with its own S3 state.
Token: `/cloudflare/terraform-token` (Bearer), passed as
`TF_VAR_cloudflare_api_token`.

- **`www`** — proxied CNAME to the API Gateway origin (enables WAF + caching).
- **apex (`@`)** — proxied CNAME added 2026-07-14 so the bare domain resolves;
  intended to 301-redirect to `www` (the origin only serves the `www` Host).
  The redirect rule is written in `cloudflare/dns.tf` but not yet applied — the
  terraform token currently lacks ruleset permission. See the
  `mywebsite-tweaks` strand STATE for the exact unblock.
- **Email:** MX + SPF + DKIM + SES-verification records are **not** proxied
  (real DNS required for SES).
- **WAF:** Cloudflare free managed ruleset; rate limits on
  `/gardencam/capture` and `/pi-fleet`.
- **Edge cache** (`cloudflare/cache.tf`): `/cv`, `/gitinfo`, `/robots.txt`,
  `/contents` cached at the edge with route-specific TTLs to avoid Lambda
  invocations. (Note: the cache ruleset was authored but historically never
  applied for the same missing-permission reason.)

## mywebsite vs cv

Two separate repos run in parallel during migration:

| | mywebsite (this repo) | cv (`~/cv`) |
|---|---|---|
| Domain | `www.petergrecian.co.uk` | `w3.petergrecian.co.uk` |
| Lambda | `mywebsite` | `cvdev` |
| Handler | `lambda/mywebsite.py` | `cv.py` |
| Deploy | `./deploy` | `./update` |
| Terraform state | `mywebsite-tfstate` | `cv-tfstate` |
| Contents page | DynamoDB-driven | Static HTML |

Both Lambdas read some of the same shared data stores (gardencam S3/DynamoDB,
exec logs, SSM secrets), so changing shared data affects both. Do not modify
cv's AWS resources from here. **End goal:** this repo becomes the sole website;
cv eventually only provides CV content.

## Notes & known drift

- **`/t3` is redundant.** The K2 bus fetcher exists in three places: the `t3`
  Lambda (canonical, used by the Android app), this `/t3` route (duplicated
  logic), and the `busclock` Flask prototype. Leave `/t3` for now; retire or
  redirect it to the `t3` Lambda later.
- **Timestamps:** S3 filenames use UTC (correct — don't change); anything shown
  to a human on the site must be converted to Europe/London (GMT/BST).
- **`lambda.zip` / `lambda/__pycache__`** in the tree are build artefacts, not
  the source of truth — the source is `lambda/*.py` and `lambda/routes/*.py`.
- See `TODO.md` for the live backlog (contents-page nav bug, Cloudflare purge
  investigation, skycam cast overlay, logging migration to CloudWatch, etc.).

## Cost model (why serverless)

Low-traffic serverless is the point: Lambda is ~$0.20/M requests plus a tiny
per-invocation charge, and this workload sits inside the always-free tier. The
main exposure is $0.09/GB egress if a page went viral, and Cloudflare (free
tier: 1 TB / 10 M requests) absorbs most of that. API Gateway throttling is set
to ~1 req/s as a cost guardrail; AWS budget + cost-anomaly alerts back it up.
An always-on EC2 + Apache alternative would cost ~$24–40/yr before any traffic.
