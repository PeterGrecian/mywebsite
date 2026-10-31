"""FirstScope is named for the telescope on the site, but its nights live under
the camera's config name in S3 (xoverpi/). These pin that mapping and the
Results link at the top of the telescope page."""

import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "lambda")))

import mywebsite  # noqa: E402
from routes.astro import (CAMERA_LABELS, render_astro_camera_page,  # noqa: E402
                          render_astro_instrument)


def test_instrument_page_stays_on_bare_path():
    route = mywebsite._resolve_route("/astro/firstscope")
    assert route is mywebsite._resolve_route("/astro/firstscope/")
    assert route is not mywebsite._resolve_route(
        "/astro/firstscope/night/2026-10-30")


def test_night_routes_exist():
    night = mywebsite._resolve_route("/astro/firstscope/night/2026-10-30")
    assert night is mywebsite._resolve_route("/astro/astrocam/night/2026-10-30")
    assert night is mywebsite._resolve_route("/astro/firstscope/all")
    player = mywebsite._resolve_route(
        "/astro/firstscope/night/2026-10-30/player")
    assert player is mywebsite._resolve_route(
        "/astro/astrocam/night/2026-10-30/player")


def test_stamp_names_the_camera():
    assert CAMERA_LABELS["xoverpi"] == "firstscope fshq"


def test_results_route_is_the_calendar():
    assert (mywebsite._resolve_route("/astro/firstscope/results")
            is mywebsite._resolve_route("/astro/astrocam/nights"))


def test_instrument_page_links_results():
    html = render_astro_instrument(theme_css_js="", slug="firstscope")
    assert 'href="/astro/firstscope/results"' in html
    assert html.index("/astro/firstscope/results") < html.index("i-sub\">")


def test_night_page_shows_the_still_first_and_links_back():
    html = render_astro_camera_page(
        theme_css_js="", title="FirstScope", camera="firstscope",
        night="2026-10-30", nights=["2026-10-30"], is_dashboard=False, sections=[{
            "label": None, "anchor": None, "summary": None,
            "urls": {"night-still.jpg": "https://x/s.jpg",
                     "max.jpg": "https://x/m.jpg"},
            "stamp_camera": "xoverpi", "stamp_night": "2026-10-30"}])
    assert html.index("https://x/s.jpg") < html.index("https://x/m.jpg")
    assert 'href="/astro/firstscope/results"' in html


def test_sky_text_mag_and_bits():
    from routes.astro import sky_text
    # measured zero point, no approximation mark
    assert sky_text("astrocam", "2026-09-21", 4.15).startswith("18.1 mag")
    # zero point revised when the glass came off, and provisional
    assert sky_text("astrocam", "2026-10-20", 4.27).startswith("&asymp;18.1 mag")
    assert sky_text("eclipticam-hq16", "2026-10-20", 5.49).startswith("&asymp;17.8")
    assert sky_text("canon", "2026-08-12", 8.80).startswith("&asymp;18.1")
    # uncalibrated, or before the zero point starts: bits only
    assert sky_text("xoverpi", "2026-10-30", 1.72) == "1.7 bits"
    assert sky_text("eclipticam-v3w", "2026-09-01", 3.12) == "3.1 bits"


def test_night_page_prefers_annotated_still_and_shows_star_charts():
    html = render_astro_camera_page(
        theme_css_js="", title="FirstScope", camera="firstscope",
        night="2026-10-30", nights=["2026-10-30"], is_dashboard=False, sections=[{
            "label": None, "anchor": None, "summary": None,
            "urls": {"night-still.jpg": "https://x/plain.jpg",
                     "night-still-annotated.jpg": "https://x/ann.jpg",
                     "star-counts.png": "https://x/counts.png",
                     "star-colours.png": "https://x/colours.png",
                     "star-crops.jpg": "https://x/crops.jpg"},
            "stamp_camera": "xoverpi", "stamp_night": "2026-10-30"}])
    assert "https://x/ann.jpg" in html and "https://x/plain.jpg" not in html
    for u in ("counts.png", "colours.png", "crops.jpg"):
        assert f"https://x/{u}" in html
