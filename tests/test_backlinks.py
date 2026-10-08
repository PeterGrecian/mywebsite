"""Every page but home carries a backlink to its parent at the top.

The link is injected in lambda_handler, so these tests drive the injector
directly with synthetic responses; the golden sweep covers the real pages.
"""

import pytest


def _page(body, ctype="text/html; charset=utf-8", status=200):
    return {"statusCode": status, "body": body, "headers": {"Content-Type": ctype}}


def _link(resp):
    body = resp["body"]
    i = body.find('class="site-back"')
    return None if i < 0 else body[i:body.find("</nav>", i)]


@pytest.mark.parametrize("route, href, label", [
    ("/astro", '"/"', "Home"),
    ("/biog", '"/"', "Home"),
    ("/astro/astrocam", '"/astro"', "Astro"),
    ("/astro/astrocam/night/2026-10-07", '"/astro/astrocam"', "Astrocam"),
    ("/astro/storage/2026-10", '"/astro/storage"', "Storage"),
    ("/astro/notes/2026-09-22-astrocam-plate-solve", '"/astro/notes"', "Notes"),
])
def test_parent_link(mywebsite, route, href, label):
    link = _link(mywebsite._with_backlink(route, _page("<html><body><h1>x</h1></body></html>")))
    assert f"href={href}" in link and f"&larr; {label}" in link


@pytest.mark.parametrize("route", ["", "/", "/contents"])
def test_home_has_none(mywebsite, route):
    assert _link(mywebsite._with_backlink(route, _page("<body><h1>Home</h1>"))) is None


def test_link_lands_right_after_body(mywebsite):
    resp = mywebsite._with_backlink("/biog", _page('<html><head></head><body class="x"><h1>B</h1>'))
    assert resp["body"].startswith('<html><head></head><body class="x"><nav class="site-back"')


def test_fragment_page_without_body_tag(mywebsite):
    """The epilogue wraps fragments as <html><head>...</body></html>."""
    frag = ("<html><head><link rel=icon href=/f.png><script>var a='<h1>';</script>"
            "<style>h1{}</style><title>T</title>\n  <h1>Sky</h1></body></html>")
    body = mywebsite._with_backlink("/skycam/gallery", _page(frag))["body"]
    assert body.index("<nav") == body.index("</title>") + len("</title>\n  ")
    assert body.index("</nav>") + len("</nav>") == body.index("<h1>Sky")


def test_own_top_nav_is_kept_alone(mywebsite):
    body = '<body><div class="nav"><a href="/contents">← Home</a></div><h1>S</h1>'
    assert mywebsite._with_backlink("/starcam", _page(body))["body"] == body


def test_footer_backlink_does_not_count(mywebsite):
    body = '<body><h1>Astro Camera</h1><div class="footer"><a href="/astro">&larr; Astro</a></div>'
    assert _link(mywebsite._with_backlink("/astro/astrocam", _page(body))) is not None


@pytest.mark.parametrize("resp", [
    _page("<body><h1>x</h1>", status=404),
    _page("{}", ctype="application/json"),
    {**_page("<body>"), "isBase64Encoded": True},
])
def test_non_pages_untouched(mywebsite, resp):
    assert mywebsite._with_backlink("/astro/astrocam", resp) == resp


def test_handler_injects_end_to_end(mywebsite, make_event, make_context):
    r = mywebsite.lambda_handler(make_event("/biog"), make_context())
    assert 'class="site-back"' in r["body"]
    r = mywebsite.lambda_handler(make_event("/"), make_context())
    assert 'class="site-back"' not in r["body"]
