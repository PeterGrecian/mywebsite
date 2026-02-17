# mywebsite — Claude Context

## What This Repo Does

The main website Lambda serving `www.petergrecian.co.uk`. Hosts CV, gardencam viewer, pi-fleet dashboard, bus times, and other applications.

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
| `/t3` | K2 bus arrivals (TfL API) |
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

## Relation to cv Repo

This repo replaces the `cv` repo's role as the website Lambda. The cv repo (`~/cv`) previously served `w3.petergrecian.co.uk` — this repo serves `www.petergrecian.co.uk`. Both run in parallel during migration.

## AWS Region

eu-west-1 (Ireland)
