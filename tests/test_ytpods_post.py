"""POST /ytpods/read, /ytpods/rate and /ytpods/refresh: the Video Guide page's beacons."""

import base64
import json

import pytest

AUTH = {"authorization": "Basic " + base64.b64encode(b"x:test-password").decode()}
ID1, ID2 = "dQw4w9WgXcQ", "abcdefghijk"


class NoSuchKey(Exception):
    pass


class FakeS3:
    class exceptions:
        NoSuchKey = NoSuchKey

    def __init__(self, objs=None):
        self.objs = dict(objs or {})
        self.puts = []

    def get_object(self, Bucket, Key):
        if Key not in self.objs:
            raise NoSuchKey(Key)

        class B:
            def __init__(s, b): s.b = b
            def read(s): return s.b
        return {"Body": B(self.objs[Key])}

    def head_object(self, Bucket, Key):
        raise NoSuchKey(Key)

    def put_object(self, Bucket, Key, Body, **kw):
        self.objs[Key] = Body
        self.puts.append(Key)


@pytest.fixture
def s3(mywebsite, monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(mywebsite, "s3_client", lambda *a, **k: fake)
    return fake


def _post(mywebsite, make_event, make_context, path, body, auth=True, method="POST"):
    ev = make_event(path, method=method, headers=AUTH if auth else None,
                    body=json.dumps(body) if not isinstance(body, str) else body)
    return mywebsite.lambda_handler(ev, make_context())


@pytest.mark.parametrize("path", ["/ytpods/read", "/ytpods/rate", "/ytpods/refresh"])
def test_auth_and_method(mywebsite, make_event, make_context, s3, path):
    assert _post(mywebsite, make_event, make_context, path, {}, auth=False)["statusCode"] == 401
    assert _post(mywebsite, make_event, make_context, path, {}, method="GET")["statusCode"] == 405
    assert s3.puts == []


def test_read_unions_and_is_idempotent(mywebsite, make_event, make_context, s3):
    s3.objs["ytpods/seen.json"] = json.dumps([ID2]).encode()
    r = _post(mywebsite, make_event, make_context, "/ytpods/read",
              {"seen": [ID1, "bad id", ID1, 7], "t": 1})
    assert r["statusCode"] == 202
    assert json.loads(s3.objs["ytpods/seen.json"]) == sorted([ID1, ID2])
    _post(mywebsite, make_event, make_context, "/ytpods/read", {"seen": [ID1]})
    assert s3.puts == ["ytpods/seen.json"]          # second send changed nothing


def test_read_never_clobbers_a_bad_store(mywebsite, make_event, make_context, s3):
    s3.objs["ytpods/seen.json"] = b'{"not": "a list"}'
    assert _post(mywebsite, make_event, make_context, "/ytpods/read",
                 {"seen": [ID1]})["statusCode"] == 503
    assert s3.puts == []


def test_rate_validates_and_skips_unchanged(mywebsite, make_event, make_context, s3):
    body = {"ratings": {
        ID1: {"funny": 4, "bait": "no", "t": 100, "extra": "x"},
        ID2: {"funny": 9, "bait": "maybe", "t": 5},     # nothing valid left
        "short": {"funny": 3, "t": 1},
        "zzzzzzzzzzz": {"bait": "yes"},                  # no t
    }}
    assert _post(mywebsite, make_event, make_context, "/ytpods/rate", body)["statusCode"] == 202
    assert s3.puts == [f"ytpods/ratings/{ID1}.json"]
    assert json.loads(s3.objs[f"ytpods/ratings/{ID1}.json"]) == {"funny": 4, "bait": "no", "t": 100}
    _post(mywebsite, make_event, make_context, "/ytpods/rate", body)
    assert len(s3.puts) == 1                          # same t: skipped
    body["ratings"][ID1]["t"] = 101
    _post(mywebsite, make_event, make_context, "/ytpods/rate", body)
    assert len(s3.puts) == 2


def test_rate_rejects_big_or_bad_bodies(mywebsite, make_event, make_context, s3):
    assert _post(mywebsite, make_event, make_context, "/ytpods/rate", "not json")["statusCode"] == 400
    big = {"ratings": {ID1: {"funny": 1, "t": 1}}, "pad": "x" * 40000}
    assert _post(mywebsite, make_event, make_context, "/ytpods/rate", big)["statusCode"] == 400
    assert s3.puts == []


def test_refresh_carries_seen(mywebsite, make_event, make_context, s3):
    assert _post(mywebsite, make_event, make_context, "/ytpods/refresh",
                 {"seen": [ID1, "nope"]})["statusCode"] == 202
    assert json.loads(s3.objs["ytpods/refresh-request"])["seen"] == [ID1]
