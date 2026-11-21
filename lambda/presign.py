"""Stable expiries for presigned S3 URLs, so browsers can cache the images.

S3 presigned URLs here are SigV2 (`AWSAccessKeyId`, `Expires=<epoch>`,
`Signature`): the URL is a function of the key, the credentials and the
absolute expiry. botocore sets that expiry to int(now + int(ExpiresIn)), so every
render minted a new URL for the same image and nothing was ever cached (7.4 MB
re-fetched per astro page view, STATE "Pending").

`stable_expires(n)` returns an ExpiresIn that lands the absolute expiry on the
next BOUNDARY after now + n. Every render inside that window, in that Lambda
container (same STS credentials), produces a byte-identical URL. Each URL stays
valid for at least n and at most n + BOUNDARY seconds. The STS session token
still caps it as before: when it expires or rotates, URLs change and old ones 403.

If botocore ever presigns S3 as SigV4 (X-Amz-Date in the URL), the signing time
varies per call and this no longer makes URLs stable, though it does no harm.
"""

import math
import time

BOUNDARY = 3600


def stable_expires(expires_in, now=None):
    """An ExpiresIn for generate_presigned_url that rounds the expiry up to the hour."""
    now = time.time() if now is None else now
    target = math.ceil((now + expires_in) / BOUNDARY) * BOUNDARY
    # botocore's SigV2 query signer computes int(time.time() + int(ExpiresIn)),
    # so hand it a whole number measured from the current whole second. It lands
    # on target unless a second ticks between here and its own clock read.
    return int(target - math.floor(now))
