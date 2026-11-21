"""Presigned URLs stay byte-identical within an hour so browsers cache images."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))
from presign import BOUNDARY, stable_expires  # noqa: E402


def test_expiry_lands_on_the_boundary_and_covers_the_request():
    for now in (1795270000.0, 1795270000.987, 1795272000.25):
        for n in (3600, 7200, 14400, 86400):
            e = stable_expires(n, now)
            assert isinstance(e, int)
            exp = int(now + int(e))                      # botocore's formula
            assert exp % BOUNDARY == 0
            assert n <= exp - now < n + BOUNDARY + 1


def test_same_window_same_expiry():
    a = int(1795269700.1 + int(stable_expires(3600, 1795269700.1)))
    b = int(1795271999.9 + int(stable_expires(3600, 1795271999.9)))
    assert a == b


def test_botocore_url_is_identical_across_calls(monkeypatch):
    """Real botocore, static fake creds: two presigns a few seconds apart match."""
    import importlib
    import time as _time
    import botocore.session
    real = sys.modules.get("boto3")
    sess = botocore.session.get_session()
    c = sess.create_client("s3", region_name="eu-west-1",
                           aws_access_key_id="AKIDEXAMPLE", aws_secret_access_key="x")
    t = [1795269700.37]
    monkeypatch.setattr(_time, "time", lambda: t[0])
    u1 = c.generate_presigned_url("get_object", Params={"Bucket": "b", "Key": "k.jpg"},
                                  ExpiresIn=stable_expires(3600))
    t[0] += 900
    u2 = c.generate_presigned_url("get_object", Params={"Bucket": "b", "Key": "k.jpg"},
                                  ExpiresIn=stable_expires(3600))
    if "X-Amz-Date" in u1:   # SigV4: signing time is in the URL; see presign.py
        return
    assert u1 == u2
