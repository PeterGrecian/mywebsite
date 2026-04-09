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


class TestAuthProtectedRoutes:
    """Routes that require Basic Auth should 401 without credentials."""

    @pytest.fixture
    def auth_header(self, mywebsite):
        """Valid auth header using the test password from conftest."""
        creds = base64.b64encode(b"user:test-password").decode()
        return {"Authorization": f"Basic {creds}"}

    def test_gardencam_no_auth(self, mywebsite, make_event, make_context):
        event = make_event("/gardencam")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 401
        assert "WWW-Authenticate" in result["headers"]

    def test_gardencam_capture_no_auth(self, mywebsite, make_event, make_context):
        event = make_event("/gardencam/capture")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 401

    def test_gardencam_stats_no_auth(self, mywebsite, make_event, make_context):
        event = make_event("/gardencam/stats")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 401

    def test_gardencam_gallery_no_auth(self, mywebsite, make_event, make_context):
        event = make_event("/gardencam/gallery")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 401

    def test_gardencam_s3_stats_no_auth(self, mywebsite, make_event, make_context):
        event = make_event("/gardencam/s3-stats")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 401

    def test_gardencam_videos_no_auth(self, mywebsite, make_event, make_context):
        event = make_event("/gardencam/videos")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 401

    def test_gardencam_timelapse_no_auth(self, mywebsite, make_event, make_context):
        event = make_event("/gardencam/timelapse")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 401

    def test_gardencam_fullres_no_auth(self, mywebsite, make_event, make_context):
        event = make_event("/gardencam/fullres/some-image.jpg")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 401

    def test_gardencam_display_no_auth(self, mywebsite, make_event, make_context):
        event = make_event("/gardencam/display/some-image.jpg")
        result = mywebsite.lambda_handler(event, make_context())
        assert result["statusCode"] == 401


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
