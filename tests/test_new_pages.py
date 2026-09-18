"""/biog and /ai-memory — the two pages added 2026-09-18.

Both are template pages on the existing `templates/*.html` +
`.format(theme_css_js=...)` convention. The tests that matter are the ones a
template page gets wrong: an unescaped brace in the CSS (which raises at
render, not at import), a missing viewport meta, and the route not actually
being claimed.
"""

import re

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
        assert "AI That Remembers" in r["body"]

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


class TestContentsCards:
    """The contents page moved from pill links to cards on 2026-09-18.

    The pills had to stay short, which cramped every description onto a
    squeezed second line and left nowhere for an image.
    """

    @pytest.fixture(scope="class")
    def body(self, mywebsite, contents_items):
        """Rendered off the checked-in JSON, not through lambda_handler:
        boto3 is mocked in tests, so the live DynamoDB scan returns nothing
        and the page comes back with no cards at all."""
        import sys
        from unittest.mock import MagicMock
        from routes.contents import render_contents_page

        fake = MagicMock()
        fake.resource.return_value.Table.return_value.scan.return_value = {
            "Items": contents_items}
        real, sys.modules["boto3"] = sys.modules.get("boto3"), fake
        try:
            return render_contents_page(theme_css_js="", private=False)
        finally:
            if real is not None:
                sys.modules["boto3"] = real

    def test_pills_are_gone(self, body):
        assert "link-ellipse" not in body
        assert 'class="card-title"' in body

    def test_ai_memory_is_first(self, body):
        titles = re.findall(r'class="card-title" href="[^"]*">([^<]+)', body)
        assert titles[0].startswith("AI That Remembers")

    def test_github_is_at_the_bottom(self, body):
        """Moved out of the header into a footer, so the cards lead."""
        assert "identity-nav" not in body
        gh = body.index("github.com/PeterGrecian")
        assert gh > body.rindex('class="card-title"')

    def test_skycam_card_carries_the_youtube_link(self, body):
        """Beautiful Clouds moved off the page header onto the card it
        belongs to."""
        assert "card-extra" in body
        assert "UCXbk1ItK5B8RAqhUPNTX7zw" in body

    def test_second_link_is_not_a_nested_anchor(self, body):
        """The card is a div precisely so the extra link is a sibling of the
        title, not nested inside it — nested anchors are invalid HTML and
        browsers recover from them unpredictably."""
        card = body[body.index('<div class="card">'):]
        card = card[:card.index("</div>")]
        assert card.count("<a ") <= 2
        title_end = body.index("</a>", body.index('class="card-title"'))
        extra = body.find('class="card-extra"')
        assert extra == -1 or extra > title_end

    def test_astronomy_card_has_its_image(self, body):
        assert 'class="card-img"' in body
        assert "assets/cards/astronomy.jpg" in body

    def test_cards_work_without_an_image(self, mywebsite):
        """image_url is optional. This renders the no-image path directly
        rather than counting cards on the live page: every public entry has
        an image now, so a count-based assertion silently stopped testing
        anything the moment the last one was filled in."""
        import sys
        from unittest.mock import MagicMock
        from routes.contents import render_contents_page

        items = [
            {"path": "with", "title": "With", "description": "d",
             "sort_order": 1, "visible": True,
             "image_url": "https://example.com/x.jpg"},
            {"path": "without", "title": "Without", "description": "d",
             "sort_order": 2, "visible": True},
        ]
        fake = MagicMock()
        fake.resource.return_value.Table.return_value.scan.return_value = {
            "Items": items}
        real, sys.modules["boto3"] = sys.modules.get("boto3"), fake
        try:
            html = render_contents_page(theme_css_js="", private=False)
        finally:
            if real is not None:
                sys.modules["boto3"] = real

        assert html.count('class="card-title"') == 2
        assert html.count('class="card-img"') == 1
        # the imageless card still renders its title and description
        assert ">Without</a>" in html


@pytest.fixture(scope="module")
def contents_items():
    import json
    import os
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo, "site-contents.json")) as f:
        return json.load(f)
