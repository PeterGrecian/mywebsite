"""Pages kept off the public /contents answer only to the password."""

import base64

import pytest

LOCKED = [
    "/cv", "/gotg", "/lambda-stats", "/lambda-stats/data", "/manim", "/rcr",
    "/site-test", "/springcam", "/springcam/gallery", "/springcam/fullres",
    "/springcam/play", "/springcam/videos", "/us-vs-the-machines",
]


def _auth(event, mywebsite, password):
    token = base64.b64encode(f"x:{password}".encode()).decode()
    event["headers"]["Authorization"] = f"Basic {token}"
    return event


@pytest.mark.parametrize("path", LOCKED)
def test_refused_without_password(mywebsite, make_event, make_context, path):
    r = mywebsite.lambda_handler(make_event(path), make_context())
    assert r["statusCode"] == 401
    assert "WWW-Authenticate" in r["headers"]
    assert r["headers"]["Cache-Control"] == "no-store"


@pytest.mark.parametrize("path", LOCKED)
def test_wrong_password_refused(mywebsite, make_event, make_context, path, monkeypatch):
    monkeypatch.setattr(mywebsite, "GARDENCAM_PASSWORD", "right")
    event = _auth(make_event(path), mywebsite, "wrong")
    assert mywebsite.lambda_handler(event, make_context())["statusCode"] == 401


@pytest.mark.parametrize("path", ["/cv", "/gotg", "/manim", "/site-test", "/rcr"])
def test_password_admits_and_is_never_cached(mywebsite, make_event, make_context, path, monkeypatch):
    monkeypatch.setattr(mywebsite, "GARDENCAM_PASSWORD", "right")
    monkeypatch.chdir(mywebsite.__file__.rsplit("/", 1)[0])
    event = _auth(make_event(path), mywebsite, "right")
    r = mywebsite.lambda_handler(event, make_context())
    assert r["statusCode"] in (200, 302)
    assert r["headers"]["Cache-Control"] == "no-store"


@pytest.mark.parametrize("path", ["/", "/contents", "/astro", "/skycam", "/stereo",
                                  "/t3", "/ai-memory", "/biog", "/pi-fleet",
                                  "/gotg/manifest.json"])
def test_public_pages_ask_for_nothing(mywebsite, make_event, make_context, path):
    assert mywebsite.lambda_handler(make_event(path), make_context())["statusCode"] != 401
