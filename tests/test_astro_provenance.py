"""Every astro image says which camera took it and when (Peter 2026-10-11).

camera_label is the one name table; provenance is the stamp line.
"""


def _astro():
    # conftest puts lambda/ on sys.path after collection, so import late.
    from routes import astro
    return astro


def test_cameras_use_their_real_names():
    assert _astro().camera_label("eclipticam") == "eclipticam v3w"
    assert _astro().camera_label("eclipticam-v3w") == "eclipticam v3w"
    assert _astro().camera_label("eclipticam-v1") == "eclipticam v1"
    assert _astro().camera_label("astrocam") == "astrocam v3"
    assert _astro().camera_label("xoverpi") == "xoverpi"  # unknown passes through


def test_date_spans():
    assert _astro().date_span("2026-10-09", night=True) == "night of 9 Oct 2026"
    assert _astro().date_span("2026-09-17", "2026-10-09", 9) == "17 Sep to 9 Oct 2026 (9 nights)"
    assert _astro().date_span("2026-10-01", "2026-10-09") == "1 to 9 Oct 2026"
    assert _astro().date_span("2025-12-30", "2026-01-02") == "30 Dec 2025 to 2 Jan 2026"


def test_provenance_empty_when_nothing_known():
    assert _astro().provenance(None) == ""


def test_note_figure_is_stamped_and_falls_back_to_instrument():
    item = {"title": "t", "instrument": "eclipticam", "figures": [
        {"url": "a", "caption": "c", "camera": "eclipticam-v3w",
         "taken_start": "2026-09-17", "taken_end": "2026-10-09", "nights": 9},
        {"url": "b", "caption": "d"}]}
    html = _astro().render_astro_note_detail(theme_css_js="", item=item)
    assert "eclipticam v3w &middot; 17 Sep to 9 Oct 2026 (9 nights)" in html
    # No date of its own: camera from the instrument, and no invented date.
    assert '<div class="prov">eclipticam v3w</div>d' in html


def test_hub_renders():
    # 2026-10-10: a second _card in this module shadowed the hub's and /astro
    # 500'd on every request.
    assert "Field Notes" in _astro().render_astro_hub(theme_css_js="")
