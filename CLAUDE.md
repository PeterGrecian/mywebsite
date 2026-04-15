# mywebsite — Claude Context

## What This Repo Does

The main website Lambda serving `www.petergrecian.co.uk`. This is Peter's personal showcase — a demonstration of technical ability to potential employers, and a place to show off projects to himself and others. Hosts CV, gardencam viewer, pi-fleet dashboard, bus times, and other applications.

## Architecture

- **Lambda** (`lambda/mywebsite.py`): Main handler with all routes
- **API Gateway**: HTTP API v2, custom domain `www.petergrecian.co.uk`
- **Cloudflare**: DNS + WAF + rate limiting (proxies traffic to API Gateway)
- **DynamoDB**: `mywebsite-contents` table drives the contents/navigation page
- **Terraform**:
  - `terraform/`: AWS infrastructure (Lambda, API Gateway, DynamoDB, SES, Route53)
  - `cloudflare/`: Cloudflare DNS, WAF, and rate limiting (separate TF state)

## Routes

| Path | Function |
|------|----------|
| `/` (default) | Serves CV page |
| `/contents` | Data-driven navigation page (reads from DynamoDB) |
| `/gardencam` | Latest garden images (password protected) |
| `/gardencam/gallery` | Thumbnail gallery |
| `/gardencam/stats` | Statistics visualization |
| `/gardencam/capture` | POST: trigger remote capture |
| `/pi-fleet` | Pi fleet monitoring dashboard |
| `/t3` | K2 bus arrivals (TfL API) — **redundant**, see note below |
| `/lambda-stats` | Execution metrics and costs |
| `/event` | Debug info |
| `/gitinfo` | Git deployment info |

## AWS Resources

| Resource | Name | Notes |
|----------|------|-------|
| Lambda | `mywebsite` | Python 3.12, 128MB, 30s timeout |
| API Gateway | `mywebsite-api` | HTTP API v2; origin for Cloudflare CNAME |
| Custom domain | `www.petergrecian.co.uk` | Uses wildcard ACM cert; proxied by Cloudflare |
| DynamoDB | `mywebsite-contents` | Navigation data (partition key: `path`) |
| IAM role | `mywebsite-lambda-role` | Access to shared data stores |
| SES | Email forwarding | `peter@petergrecian.co.uk` → Gmail; DNS MX records non-proxied in Cloudflare |

## Site Contents

The contents/navigation page is data-driven:
- Source of truth: `site-contents.json` in this repo
- Sync to DynamoDB: `python tools/sync-contents.py`
- Lambda reads `mywebsite-contents` table at runtime

## Shared Data Stores (read from other projects)

- DynamoDB: `pi-fleet-status`, `gardencam-stats`, `gardencam-commands`, `cv-access-logs`, `lambda-execution-logs`
- S3: `gardencam-berrylands-eu-west-1`
- SSM: `/berrylands/gardencam/password`, `/berrylands/tfl/api-key`

## Deployment

```bash
./deploy              # Deploy Lambda code
terraform -chdir=terraform apply   # Apply infrastructure changes
python tools/sync-contents.py      # Sync navigation data to DynamoDB
```

## mywebsite vs cv — Don't Confuse Them

These are two separate repos running in parallel during migration:

| | mywebsite (this repo) | cv (`~/cv`) |
|---|---|---|
| **Domain** | `www.petergrecian.co.uk` | `w3.petergrecian.co.uk` |
| **Lambda** | `mywebsite` | `cvdev` |
| **API Gateway** | `mywebsite-api` | `cvdev` |
| **IAM role** | `mywebsite-lambda-role` | `cvdev` |
| **Terraform state** | `mywebsite-tfstate` | `cv-tfstate` |
| **Deploy script** | `./deploy` | `./update` |
| **Handler file** | `lambda/mywebsite.py` | `cv.py` |
| **Contents page** | DynamoDB-driven (`mywebsite-contents`) | Static HTML (`contents.html`) |

**Key rules:**
- Edit `lambda/mywebsite.py` here, NOT `cv.py` in `~/cv` — they are independent copies
- Run `./deploy` here, NOT `./update` from `~/cv`
- Terraform state is separate — `terraform apply` in each repo only affects its own resources
- Both Lambdas read the same shared data stores (DynamoDB tables, S3 bucket, SSM parameters) — changes to shared data affect both
- Do NOT delete or modify cv's AWS resources from this repo — they coexist

**End goal:** This repo becomes the sole website. The cv repo will eventually only provide CV content data.

## Planned: Android App Showcase

The Android apps will eventually be featured on the site:

- **T3 (tersetransporttimes)** — bus and train times, GPS-aware, minimalist
- **blescape** — stereo soundscape from BLE scan data
- **nightsound** — snoring/sleep sound capture

Not yet done — apps need to reach a presentable state first.

## /t3 Route — Redundant

The `/t3` route has its own TfL API calls baked into `mywebsite.py`. There are now three separate implementations of the same K2 bus fetcher:

| | Key source | Status |
|---|---|---|
| `t3` Lambda | SSM | **Canonical** — used by Android app |
| `/t3` on this site | SSM (`/berrylands/tfl/api-key`) | Redundant — future unclear |
| `busclock` Flask app | `.env` | Prototype for physical servo clock |

The `/t3` web page has no clear future. Options: retire it, or redirect it to call the `t3` Lambda instead of duplicating the logic. Leave it for now.

## Timestamps

- **S3 filenames** use UTC timestamps — this is correct, do not change
- **Website display** must always show Europe/London local time (GMT/BST) — convert UTC timestamps before rendering

## AWS Region

eu-west-1 (Ireland)

## Cloudflare Setup

**DNS & WAF fronting the website** — separate Terraform in `cloudflare/` with its own S3 state (`cloudflare-tfstate`).

### Records in Cloudflare

| Name | Type | Proxied | Purpose |
|---|---|---|---|
| `www` | CNAME | ✅ **Yes** | Points to API Gateway; enables WAF/caching |
| `@` (apex) | MX | ❌ **No** | `inbound-smtp.eu-west-1.amazonaws.com` for SES email |
| `@` | TXT | ❌ **No** | SPF + Google site verification |
| `_amazonses` | TXT | ❌ **No** | SES domain verification token |
| `<token>._domainkey` ×3 | CNAME | ❌ **No** | SES DKIM records (orange cloud OFF — real DNS required) |

### WAF & Rate Limiting

**Managed Rules:** Cloudflare Managed Ruleset (free tier) blocks XSS, SQLi, bots.

**Rate Limiting:**
- `/gardencam/capture` POST: 10 requests/min per IP → challenge
- `/pi-fleet`: 30 requests/min per IP → challenge

### Edge Caching (`cloudflare/cache.tf`)

Static and slow-changing routes are cached at Cloudflare's edge to avoid Lambda invocations:

| Route | Edge TTL | Browser TTL | Notes |
|-------|----------|-------------|-------|
| `/cv` | 24h | 1h | Static HTML file read |
| `/gitinfo` | 24h | 1h | Static HTML file read |
| `/robots.txt` | 7d | 24h | Hardcoded string |
| `/contents` | 1h | 5m | DynamoDB-driven, changes on `sync-contents.py` |

**Cache purge:** `./deploy` automatically purges all four cached URLs after uploading to Lambda. Manual purge available via Cloudflare dashboard or API.

### Deployment

```bash
# Store API key in SSM (one-time setup)
aws ssm put-parameter \
  --name /cloudflare/global-api-key \
  --value "$(cat ~/.config/cloudflare.key)" \
  --type SecureString --region eu-west-1

# Plan/apply with key from SSM
cd cloudflare
CF_KEY=$(aws ssm get-parameter --name /cloudflare/global-api-key --with-decryption --query Parameter.Value --output text)
terraform init -backend-config=backends.tfvars
terraform plan -var="cloudflare_api_key=$CF_KEY"
terraform apply -var="cloudflare_api_key=$CF_KEY"
```

### After Initial Apply: Nameserver Migration

1. Copy Cloudflare nameservers from `terraform output nameservers`
2. Update registrar (who/where: TBD) to point to Cloudflare nameservers
3. Wait for propagation (minutes to ~1 hour); check with `dig NS petergrecian.co.uk`
4. Verify: `curl -v https://www.petergrecian.co.uk` → 200 from Cloudflare edge
5. Test email: send to `peter@petergrecian.co.uk`, confirm forwarding to Gmail

**Route53 records stay in place** (become dormant) — useful for rollback if needed.

### Cloudflare Global API Key

Stored in AWS SSM (`/cloudflare/global-api-key`). Never commit to git. If the key rotates:
1. Update in `~/.config/cloudflare.key`
2. Re-run the SSM put-parameter command above
3. Re-run terraform apply
