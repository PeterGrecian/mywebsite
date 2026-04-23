# DNS Issue — newhome.petergrecian.co.uk

## Status
CNAME created and active on Cloudflare. Resolves fine via 8.8.8.8 and Cloudflare's own nameservers.
pip has a negative cache entry (NXDOMAIN, 1800s TTL) from before the CNAME was created.

## To resume
1. Wait ~30 mins from when CNAME was created (~10:41 BST 2026-04-18), then retry on pip
2. Visit https://newhome.petergrecian.co.uk on Android phone to test PWA install
3. On Android Chrome: three-dot menu → "Add to Home screen" / "Install app"
4. Verify red tick icon appears on home screen
5. If happy, proceed to make this the main homepage (swap www CNAME to Pages)

## Deploy command (if redeployment needed)
```bash
CF_KEY=$(secrets get /cloudflare/global-api-key 2>/dev/null) && \
CLOUDFLARE_ACCOUNT_ID=49363caa0ef13c5b8e98b769eab5a6f7 \
CLOUDFLARE_API_KEY=$CF_KEY \
CLOUDFLARE_EMAIL=peter.grecian@gmail.com \
wrangler pages deploy ~/mywebsite/public/ --project-name=petergrecian-homepage --commit-dirty=true
```
