"""/biog and /ai-memory — the two pages added 2026-09-18.

Both are template pages on the existing `templates/*.html` +
`.format(theme_css_js=...)` convention. The tests that matter are the ones a
template page gets wrong: an unescaped brace in the CSS (which raises at
render, not at import), a missing viewport meta, and the route not actually
being claimed.
"""

import pytest


class TestBiog:
    def test_serves(self, mywebsite, make_event, make_context):
        r = mywebsite.lambda_handler(make_event("/biog"), make_context())
        assert r["statusCode"] == 200
        assert "Peter Grecian" in r["body"]

    def test_has_viewport(self, mywebsite, make_event, make_context):
        r = mywebsite.lambda_handler(make_event("/biog"), make_context())
        assert 'name="viewport"' in r["body"]

    def test_is_hidden_until_written(self, contents_items):
        """It ships with a placeholder, so it must not be on either contents
        page yet. Flip `visible` when the prose lands."""
        entry = next(i for i in contents_items if i["path"] == "biog")
        assert entry["visible"] is False


class TestAiMemory:
    def test_serves(self, mywebsite, make_event, make_context):
        r = mywebsite.lambda_handler(make_event("/ai-memory"), make_context())
        assert r["statusCode"] == 200
        assert "AI Which Remembers" in r["body"]

    def test_has_viewport(self, mywebsite, make_event, make_context):
        r = mywebsite.lambda_handler(make_event("/ai-memory"), make_context())
        assert 'name="viewport"' in r["body"]

    def test_describes_the_actual_method(self, mywebsite, make_event,
                                         make_context):
        """Guard against the page drifting into generic AI copy. These are
        the load-bearing terms of the method it claims to introduce."""
        body = mywebsite.lambda_handler(
            make_event("/ai-memory"), make_context())["body"]
        for term in ("STATE.md", "IDEAS.md", "keeper", "builder"):
            assert term in body, f"{term} missing from the methodology page"

    def test_is_public(self, contents_items):
        entry = next(i for i in contents_items if i["path"] == "ai-memory")
        assert entry["visible"] is True
        assert not entry.get("auth_required")


class TestColophon:
    def test_contents_names_the_stack(self, mywebsite, make_event,
                                      make_context):
        body = mywebsite.lambda_handler(
            make_event("/contents"), make_context())["body"]
        for term in ("API Gateway", "Lambda", "DynamoDB", "Cloudflare"):
            assert term in body


@pytest.fixture(scope="module")
def contents_items():
    import json
    import os
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo, "site-contents.json")) as f:
        return json.load(f)
