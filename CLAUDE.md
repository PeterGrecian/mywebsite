# mywebsite — Claude Context

## What This Repo Does

The main website Lambda serving `www.petergrecian.co.uk`. This is Peter's personal showcase — a demonstration of technical ability to potential employers, and a place to show off projects to himself and others. Hosts CV, gardencam viewer, pi-fleet dashboard, bus times, and other applications.

## Architecture

- **Lambda** (`lambda/mywebsite.py`): Main handler with all routes
- **API Gateway**: HTTP API v2, custom domain `www.petergrecian.co.uk`
- **DynamoDB**: `mywebsite-contents` table drives the contents/navigation page
- **Terraform** (`terraform/`): All AWS infrastructure

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
| API Gateway | `mywebsite-api` | HTTP API v2 |
| Custom domain | `www.petergrecian.co.uk` | Uses wildcard ACM cert |
| DynamoDB | `mywebsite-contents` | Navigation data (partition key: `path`) |
| IAM role | `mywebsite-lambda-role` | Access to shared data stores |

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

## /t3 Route — Redundant

The `/t3` route has its own TfL API calls baked into `mywebsite.py`. There are now three separate implementations of the same K2 bus fetcher:

| | Key source | Status |
|---|---|---|
| `t3` Lambda | SSM | **Canonical** — used by Android app |
| `/t3` on this site | SSM (`/berrylands/tfl/api-key`) | Redundant — future unclear |
| `busclock` Flask app | `.env` | Prototype for physical servo clock |

The `/t3` web page has no clear future. Options: retire it, or redirect it to call the `t3` Lambda instead of duplicating the logic. Leave it for now.

## AWS Region

eu-west-1 (Ireland)
