"""Tests for /astro/eclipticam subpages:
- /astro/eclipticam (overview + 3 links to new pages)
- /astro/eclipticam/v3w (v3w wide view)
- /astro/eclipticam/hq16 (hq16 narrow view)
- /astro/eclipticam/history (history of the cameras)
"""

import pytest


class TestEclipticamSubpages:
    def test_eclipticam_overview_has_subnav_links(self, mywebsite, make_event, make_context):
        resp = mywebsite.lambda_handler(make_event("/astro/eclipticam"), make_context())
        assert resp["statusCode"] == 200
        body = resp["body"]
        assert 'href="/astro/eclipticam/v3w"' in body
        assert 'href="/astro/eclipticam/hq16"' in body
        assert 'href="/astro/eclipticam/history"' in body
        assert "v3w Wide View" in body
        assert "HQ16 Narrow View" in body
        assert "History of the Cameras" in body
        # Backlink to /astro
        assert '&larr; Astro' in body

    def test_eclipticam_v3w_page(self, mywebsite, make_event, make_context):
        resp = mywebsite.lambda_handler(make_event("/astro/eclipticam/v3w"), make_context())
        assert resp["statusCode"] == 200
        body = resp["body"]
        assert "v3w Wide View" in body
        assert "Sony IMX708" in body
        assert "4608 &times; 2592" in body
        assert "105.4 arcsec/photosite" in body
        # Subnav links to sibling pages
        assert 'href="/astro/eclipticam"' in body
        assert 'href="/astro/eclipticam/hq16"' in body
        assert 'href="/astro/eclipticam/history"' in body
        # Backlink to /astro/eclipticam
        assert '&larr; Eclipticam' in body

    def test_eclipticam_hq16_page(self, mywebsite, make_event, make_context):
        resp = mywebsite.lambda_handler(make_event("/astro/eclipticam/hq16"), make_context())
        assert resp["statusCode"] == 200
        body = resp["body"]
        assert "HQ16 Narrow View" in body
        assert "Sony IMX477" in body
        assert "16 mm C-mount" in body
        assert "19.9 arcsec per photosite" in body
        assert "22.41&deg; horizontal" in body
        # Subnav links to sibling pages
        assert 'href="/astro/eclipticam"' in body
        assert 'href="/astro/eclipticam/v3w"' in body
        assert 'href="/astro/eclipticam/history"' in body
        # Backlink to /astro/eclipticam
        assert '&larr; Eclipticam' in body

    def test_eclipticam_history_page(self, mywebsite, make_event, make_context):
        resp = mywebsite.lambda_handler(make_event("/astro/eclipticam/history"), make_context())
        assert resp["statusCode"] == 200
        body = resp["body"]
        assert "History of the Cameras" in body
        assert "Era 1: The Original v1 Camera" in body
        assert "OV5647" in body
        assert "Era 2: The v3 Wide Camera" in body
        assert "IMX708" in body
        assert "Era 3: Dual-Camera Rig with the HQ 16 mm" in body
        assert "IMX477" in body
        assert "Hardware Comparison" in body
        assert "The Old Rig: with the v1 Camera" in body
        assert "The New Rig: with the 16 mm Big Lens" in body
        assert "blue accent ring" in body
        # Subnav links to sibling pages
        assert 'href="/astro/eclipticam"' in body
        assert 'href="/astro/eclipticam/v3w"' in body
        assert 'href="/astro/eclipticam/hq16"' in body
        # Backlink to /astro/eclipticam
        assert '&larr; Eclipticam' in body

    def test_eclipticam_rig_photo_config(self):
        from routes.astro import CAMERA_PHOTOS, render_eclipticam_history_page
        assert CAMERA_PHOTOS["eclipticam"]["key"] == "site/eclipticam-rig-20261014.jpg"
        html = render_eclipticam_history_page(
            theme_css_js="", title="Test",
            rig_old_url="https://example.com/old.jpg",
            rig_new_url="https://example.com/new.jpg")
        assert 'src="https://example.com/old.jpg"' in html
        assert 'src="https://example.com/new.jpg"' in html
        assert "The Old Rig: with the v1 Camera" in html
        assert "The New Rig: with the 16 mm Big Lens" in html
        assert "rig-grid" in html
        assert "blue accent ring" in html
