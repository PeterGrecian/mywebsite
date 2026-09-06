#!/usr/bin/env python3
"""Sync site-contents.json to DynamoDB mywebsite-contents table.

DESTRUCTIVE: this is a full replace. Any row in DynamoDB whose `path` is
not in site-contents.json gets DELETED. The JSON is the single source of
truth; the table is downstream. So:

  1. Always edit site-contents.json, never the DynamoDB table directly.
  2. Run `git diff site-contents.json` before sync; that's exactly the
     set of changes about to land in DynamoDB.
  3. If something is in DynamoDB but not in the JSON it will disappear
     on the next sync. That is the intended behaviour, not a bug.

Lesson learned 2026-05-17: `skycam` and `stereo` were added directly to
DynamoDB and never back-propagated. A later sync deleted them. Recovered
by adding both to the JSON and re-running.
"""

import json
import subprocess
import sys
import urllib.error
import urllib.request
from decimal import Decimal

import boto3

TABLE_NAME = "mywebsite-contents"
REGION = "eu-west-1"
CONTENTS_FILE = "site-contents.json"

# /contents is edge-cached for 1h (cloudflare/cache.tf). Without a purge here
# a sync would not show up on the site for up to an hour, which reads as "the
# sync didn't work". `deploy` purges after a Lambda upload; this is the other
# way the page's content changes, so it has to purge too.
CF_ZONE_ID = "322ca2637607726fee0c4975d1aed591"  # petergrecian.co.uk
CF_PURGE_URLS = [
    "https://www.petergrecian.co.uk/contents",
    "https://www.petergrecian.co.uk/",
]


def purge_contents_cache():
    """Drop the edge copy of /contents so a sync is visible immediately.

    Best-effort: a failed purge means a stale page for up to an hour, not a
    failed sync, so it warns rather than raising. Uses the same scoped
    purge-only token as `deploy`; the token is never printed.
    """
    try:
        token = subprocess.run(
            ["secrets", "get", "/cloudflare/purge-token"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("WARNING: no Cloudflare purge token — /contents may be stale for up to 1h")
        return

    if not token:
        print("WARNING: empty Cloudflare purge token — skipping purge")
        return

    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/purge_cache",
        data=json.dumps({"files": CF_PURGE_URLS}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"WARNING: cache purge failed ({e}) — /contents may be stale for up to 1h")
        return

    if body.get("success"):
        print(f"Purged edge cache for {len(CF_PURGE_URLS)} URLs")
    else:
        print(f"WARNING: cache purge rejected: {body.get('errors')}")


def main():
    with open(CONTENTS_FILE) as f:
        items = json.load(f)

    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    # Scan existing items to detect removals
    existing = {item["path"] for item in table.scan()["Items"]}
    incoming = {item["path"] for item in items}

    # Delete items no longer in the JSON
    for path in existing - incoming:
        print(f"  Deleting: {path}")
        table.delete_item(Key={"path": path})

    # Put all current items
    for item in items:
        # Convert numbers to Decimal for DynamoDB
        ddb_item = {}
        for k, v in item.items():
            if isinstance(v, bool):
                ddb_item[k] = v
            elif isinstance(v, (int, float)):
                ddb_item[k] = Decimal(str(v))
            else:
                ddb_item[k] = v

        print(f"  Syncing: {item['path']} — {item['title']}")
        table.put_item(Item=ddb_item)

    print(f"Synced {len(items)} items to {TABLE_NAME}")
    purge_contents_cache()


if __name__ == "__main__":
    main()
