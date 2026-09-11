"""Tests for lambda_handler routing — verify each path returns correct status and content type."""

import pytest
import base64
from unittest.mock import MagicMock, patch


class TestSimpleRoutes:
    """Routes that return HTML without external calls."""

    def test_robots_txt(self, mywebsite, make_event, make_context):
        event = make_event("/robots.txt")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 200
        assert result["headers"]["Content-Type"] == "text/plain"
        assert "User-agent: *" in result["body"]
        assert "Disallow: /gardencam" in result["body"]

    def test_robots_txt_with_stage(self, mywebsite, make_event, make_context):
        event = make_event("/default/robots.txt")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 200
        assert "User-agent: *" in result["body"]

    def test_favicon_ico(self, mywebsite, make_event, make_context):
        event = make_event("/favicon.ico")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 200
        assert result["headers"]["Content-Type"] == "image/x-icon"
        assert result.get("isBase64Encoded") is True
        assert len(result["body"]) > 0

    def test_favicon_png(self, mywebsite, make_event, make_context):
        event = make_event("/favicon.png")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 200
        assert result["headers"]["Content-Type"] == "image/png"
        assert result.get("isBase64Encoded") is True
        assert len(result["body"]) > 0

    def test_favicon_svg(self, mywebsite, make_event, make_context):
        event = make_event("/favicon.svg")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 200
        assert result["headers"]["Content-Type"] == "image/svg+xml"
        assert "<svg" in result["body"]

    def test_event_debug(self, mywebsite, make_event, make_context):
        event = make_event("/event")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 200
        assert "text/html" in result["headers"]["Content-Type"]
        assert "log_group" in result["body"]

    def test_gitinfo(self, mywebsite, make_event, make_context, tmp_path):
        """gitinfo reads a local file — create a fake one for testing."""
        gitinfo = tmp_path / "gitinfo.html"
        gitinfo.write_text("<p>git info</p>")
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            event = make_event("/gitinfo")
            result = mywebsite.lambda_handler(event, make_context())
            assert result["statusCode"] == 200
        finally:
            os.chdir(old_cwd)

    def test_contents(self, mywebsite, make_event, make_context):
        event = make_event("/contents")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 200
        assert "text/html" in result["headers"]["Content-Type"]

    def test_default_route_serves_cv(self, mywebsite, make_event, make_context):
        """Unknown path falls through to default — serves CV page."""
        event = make_event("/")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 200
        assert "text/html" in result["headers"]["Content-Type"]


class TestGardencamAccessBoundary:
    """Which gardencam routes need a password, and why.

    The boundary is about PICTURES, not about the camera being secret: the
    gallery, fullres and display routes serve garden photographs that may
    have a person in them, so they need auth. /gardencam/stats is capture
    counts and timings -- numbers only, no imagery -- and is deliberately
    public. An earlier version of this file asserted 401 for stats and had
    been failing ever since; the code was right and the test was wrong.
    """

    IMAGE_ROUTES = [
        "/gardencam/gallery",
        "/gardencam/fullres/some-image.jpg",
        "/gardencam/display/some-image.jpg",
    ]

    CONTROL_ROUTES = [
        "/gardencam/capture",    # writes a command to the camera
        "/gardencam/s3-stats",   # exposes bucket layout and object counts
    ]

    @pytest.mark.parametrize("path", IMAGE_ROUTES)
    def test_image_routes_require_auth(self, mywebsite, make_event, make_context, path):
        """A photo of the garden may include whoever is standing in it."""
        result = mywebsite.lambda_handler(make_event(path), make_context())
        assert result["statusCode"] == 401, f"{path} served without credentials"
        assert "WWW-Authenticate" in result["headers"]

    @pytest.mark.parametrize("path", CONTROL_ROUTES)
    def test_control_routes_require_auth(self, mywebsite, make_event, make_context, path):
        result = mywebsite.lambda_handler(make_event(path), make_context())
        assert result["statusCode"] == 401, f"{path} served without credentials"

    def test_stats_is_deliberately_public(self, mywebsite, make_event, make_context):
        """Capture counts and timings carry no imagery — public on purpose."""
        result = mywebsite.lambda_handler(make_event("/gardencam/stats"), make_context())
        assert result["statusCode"] == 200
        assert "text/html" in result["headers"]["Content-Type"]

    def test_gardencam_root_redirects_to_skycam(self, mywebsite, make_event, make_context):
        result = mywebsite.lambda_handler(make_event("/gardencam"), make_context())
        assert result["statusCode"] == 301
        assert result["headers"]["Location"] == "/skycam"

    @pytest.mark.parametrize("path", ["/gardencam/videos", "/gardencam/timelapse"])
    def test_gardencam_has_no_video_routes(self, mywebsite, make_event, make_context, path):
        """springcam/starcam/skycam have these; gardencam never did.

        They must 404 rather than 401 — a 401 would imply the route exists
        and is merely locked, which is the thing that made the old tests
        look like they were testing auth when they were testing nothing.
        """
        result = mywebsite.lambda_handler(make_event(path), make_context())
        assert result["statusCode"] == 404


class TestResponseStructure:
    """Every route should return a dict with statusCode, headers, and body."""

    PATHS = [
        "/robots.txt",
        "/event",
        "/contents",
        "/gardencam",
        "/gardencam/capture",
        "/gardencam/stats",
        "/gardencam/gallery",
        "/pi-fleet",
        "/t3",
        "/site-test",
    ]

    @pytest.mark.parametrize("path", PATHS)
    def test_response_has_required_keys(self, mywebsite, make_event, make_context, path):
        event = make_event(path)
        result = mywebsite.lambda_handler(event, make_context())
        assert "statusCode" in result
        assert "headers" in result
        assert "body" in result
        assert isinstance(result["statusCode"], int)


class TestNotFound:
    """Unknown paths must 404, not silently serve the contents page.

    The dispatch chain's `else` used to render contents with a 200, so every
    typo, bot probe and missing asset cost a billed invocation and gave
    crawlers another indexable duplicate of the same page.
    """

    UNKNOWN = [
        "/complete-nonsense-path",
        "/wp-login.php",
        "/gardencam/nonexistent-subpage",
        "/skycam/not-a-real-view",
        "/default/no-such-page",  # the legacy stage-prefixed form too
    ]

    @pytest.mark.parametrize("path", UNKNOWN)
    def test_unknown_path_404(self, mywebsite, make_event, make_context, path):
        event = make_event(path)
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 404
        assert "text/html" in result["headers"]["Content-Type"]
        assert "404" in result["body"]

    def test_404_is_edge_cacheable(self, mywebsite, make_event, make_context):
        event = make_event("/no-such-page")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["headers"]["Cache-Control"] == "public, max-age=300"

    def test_404_is_noindex(self, mywebsite, make_event, make_context):
        event = make_event("/no-such-page")
        result = mywebsite.lambda_handler(event, make_context())
        assert 'name="robots" content="noindex"' in result["body"]

    def test_404_escapes_the_path(self, mywebsite, make_event, make_context):
        """The offending path is echoed back — it must not be injectable."""
        event = make_event("/<script>alert(1)</script>")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 404
        assert "<script>alert(1)</script>" not in result["body"]
        assert "&lt;script&gt;" in result["body"]

    def test_404_links_home(self, mywebsite, make_event, make_context):
        event = make_event("/no-such-page")
        result = mywebsite.lambda_handler(event, make_context())
        assert 'href="/contents"' in result["body"]

    @pytest.mark.parametrize("path", ["", "/", "/default", "/default/"])
    def test_root_still_serves_contents(self, mywebsite, make_event, make_context, path):
        """The root is not a 404 — it keeps rendering the contents page."""
        event = make_event(path)
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 200
        assert "Cache-Control" not in result["headers"]
