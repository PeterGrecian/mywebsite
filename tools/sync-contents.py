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
import sys
from decimal import Decimal

import boto3

TABLE_NAME = "mywebsite-contents"
REGION = "eu-west-1"
CONTENTS_FILE = "site-contents.json"


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


if __name__ == "__main__":
    main()
