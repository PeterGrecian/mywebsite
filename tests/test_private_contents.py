"""The public/private split of the contents page.

One DynamoDB table feeds two pages, on two independent flags:

    visible=False       retired or broken — off BOTH pages.
    auth_required=True  private — /my-contents only, never /contents.

Before this, `auth_required` only drew a PRIVATE badge, so the public page
listed every private entry and labelled it as the thing it was withholding.
"""

import base64
import json
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _links(html):
    return [t.strip() for t in
            re.findall(r'class="link-ellipse">\s*([^<\n]+)', html)]


@pytest.fixture(scope="module")
def contents_json():
    with open(os.path.join(REPO, "site-contents.json")) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def pages(mywebsite, contents_json):
    """Render both pages off the checked-in JSON rather than the live table,
    so the test describes the source of truth `sync-contents.py` pushes."""
    import sys
    from unittest.mock import MagicMock
    from routes.contents import render_contents_page

    fake = MagicMock()
    fake.resource.return_value.Table.return_value.scan.return_value = {
        "Items": contents_json}
    real, sys.modules["boto3"] = sys.modules.get("boto3"), fake
    try:
        return {
            False: render_contents_page(theme_css_js="", private=False),
            True: render_contents_page(theme_css_js="", private=True),
        }
    finally:
        if real is not None:
            sys.modules["boto3"] = real


def test_private_entries_are_absent_from_the_public_page(pages, contents_json):
    public = _links(pages[False])
    private_titles = [i["title"] for i in contents_json
                      if i.get("auth_required") and i.get("visible", True)]
    assert private_titles, "fixture is meaningless if nothing is marked private"
    for title in private_titles:
        assert title not in public, f"{title} is auth_required but public"


def test_private_page_is_a_superset(pages, contents_json):
    public, private = _links(pages[False]), _links(pages[True])
    assert set(public) < set(private)
    expected = {i["title"] for i in contents_json
                if i.get("auth_required") and i.get("visible", True)}
    assert set(private) - set(public) == expected


def test_invisible_entries_are_on_neither_page(pages, contents_json):
    hidden = [i["title"] for i in contents_json if not i.get("visible", True)]
    for title in hidden:
        assert title not in _links(pages[False])
        assert title not in _links(pages[True])


def test_no_private_network_urls_on_the_public_page(pages):
    """The reason betterverse had to move: a LAN address in the public nav is
    a link that hangs for every visitor who clicks it."""
    assert not re.search(r"//(192\.168\.|10\.|127\.|localhost)", pages[False])


def test_public_page_does_not_advertise_the_private_one(pages):
    assert "my-contents" not in pages[False]


def test_private_page_is_noindex(pages):
    assert 'name="robots" content="noindex,nofollow"' in pages[True]
    assert "robots" not in pages[False]


class TestMyContentsRoute:
    def test_unauthenticated_gets_401(self, mywebsite, make_event, make_context):
        r = mywebsite.lambda_handler(make_event("/my-contents"), make_context())
        assert r["statusCode"] == 401
        assert r["headers"]["WWW-Authenticate"].startswith("Basic ")

    def test_authenticated_gets_the_private_page(self, mywebsite, make_event,
                                                 make_context):
        cred = base64.b64encode(b"peter:test-password").decode()
        r = mywebsite.lambda_handler(
            make_event("/my-contents",
                       headers={"Authorization": f"Basic {cred}"}),
            make_context())
        assert r["statusCode"] == 200
        assert "Peter Grecian — private" in r["body"]

    def test_never_cached(self, mywebsite, make_event, make_context):
        """/contents is edge-cached for 1h. An authenticated page must say
        no-store itself rather than depend on that rule staying exact."""
        for headers in (None, {"Authorization": "Basic " + base64.b64encode(
                b"peter:test-password").decode()}):
            r = mywebsite.lambda_handler(
                make_event("/my-contents", headers=headers), make_context())
            assert r["headers"]["Cache-Control"] == "no-store"
