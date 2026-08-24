"""Tests for the astro camera calendar windowing.

The calendar renders one window of nights at a time (last 7 days by default)
instead of the whole history — the page used to presign a thumbnail per night
and so got slower with every night published.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "lambda")))

from routes.astro import astro_calendar_window  # noqa: E402


# 2026-06-09 .. 2026-08-23 inclusive, one night per day, newest first.
def _nights(start="2026-06-09", end="2026-08-23"):
    import datetime as dt
    a, b = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    return [(b - dt.timedelta(days=i)).isoformat()
            for i in range((b - a).days + 1)]


class TestDefaultWindow:
    def test_shows_last_seven_days(self):
        selected, label, _, _ = astro_calendar_window(_nights())
        assert len(selected) == 7
        assert selected[0] == "2026-08-23"
        assert selected[-1] == "2026-08-17"
        assert label == "last 7 days"

    def test_newest_first(self):
        selected, _, _, _ = astro_calendar_window(_nights())
        assert selected == sorted(selected, reverse=True)

    def test_input_order_does_not_matter(self):
        shuffled = sorted(_nights())  # oldest first
        selected, _, _, _ = astro_calendar_window(shuffled)
        assert selected[0] == "2026-08-23"

    def test_gaps_do_not_pad_the_window(self):
        # A 7-day window is 7 calendar days, not the 7 most recent nights:
        # a cloudy gap shows fewer cards rather than reaching further back.
        nights = ["2026-08-23", "2026-08-22", "2026-08-01", "2026-07-15"]
        selected, _, _, _ = astro_calendar_window(nights)
        assert selected == ["2026-08-23", "2026-08-22"]


class TestExplicitWindows:
    def test_week_block(self):
        selected, label, _, _ = astro_calendar_window(
            _nights(), week="2026-08-10")
        assert selected[0] == "2026-08-16"
        assert selected[-1] == "2026-08-10"
        assert label == "10 Aug–16 Aug"

    def test_month(self):
        selected, label, _, months = astro_calendar_window(
            _nights(), month="2026-07")
        assert len(selected) == 31
        assert all(n.startswith("2026-07-") for n in selected)
        assert label == "July 2026"
        assert [m["key"] for m in months if m["current"]] == ["2026-07"]

    def test_show_all(self):
        nights = _nights()
        selected, label, _, _ = astro_calendar_window(nights, show_all=True)
        assert selected == nights
        assert label == "all nights"


class TestNav:
    def test_weeks_tile_backwards_from_newest_night(self):
        _, _, weeks, _ = astro_calendar_window(_nights())
        starts = [w["start"] for w in weeks]
        assert starts[0] == "2026-08-17"
        assert starts[1] == "2026-08-10"
        # Every published night falls inside some week block.
        assert starts[-1] <= "2026-06-09"

    def test_week_links_round_trip(self):
        # Following a week link must select exactly that block — the nav
        # is useless if the link lands on a different set of nights.
        nights = _nights()
        _, _, weeks, _ = astro_calendar_window(nights)
        for w in weeks:
            selected, _, _, _ = astro_calendar_window(nights, week=w["start"])
            assert all(n >= w["start"] for n in selected)
            assert len(selected) <= 7

    def test_default_window_marks_current_week(self):
        _, _, weeks, _ = astro_calendar_window(_nights())
        current = [w["start"] for w in weeks if w["current"]]
        assert current == ["2026-08-17"]

    def test_months_present_newest_first(self):
        _, _, _, months = astro_calendar_window(_nights())
        assert [m["key"] for m in months] == ["2026-08", "2026-07", "2026-06"]


class TestEdges:
    def test_no_nights(self):
        assert astro_calendar_window([]) == ([], "", [], [])

    def test_ignores_empty_entries(self):
        selected, _, _, _ = astro_calendar_window(
            ["2026-08-23", None, "", "2026-08-22"])
        assert selected == ["2026-08-23", "2026-08-22"]

    def test_single_night(self):
        selected, label, weeks, months = astro_calendar_window(["2026-08-23"])
        assert selected == ["2026-08-23"]
        assert label == "last 7 days"
        assert len(weeks) == 1 and len(months) == 1

    def test_empty_window_is_not_an_error(self):
        # A month with no published nights renders an empty grid, not a crash.
        selected, label, _, _ = astro_calendar_window(
            _nights(), month="2026-01")
        assert selected == []
        assert label == "January 2026"


@pytest.fixture
def astro_s3(mywebsite):
    """Stub S3 serving an astrocam manifest of one night per day."""
    import io
    import json
    from unittest.mock import MagicMock, patch

    manifest = {"nights": [
        {"night": n, "thumb_key": f"astrocam/nights/{n}/thumb.jpg",
         "n_frames": 400, "n_stacked": 300, "verdict": "clear"}
        for n in _nights()]}

    client = MagicMock()
    # A fresh Body per call — a single BytesIO is exhausted after one read,
    # which silently drops later calls onto the no-manifest fallback path.
    client.get_object.side_effect = lambda *a, **kw: {
        "Body": io.BytesIO(json.dumps(manifest).encode())}
    client.head_object.side_effect = Exception("no combined plot")
    client.generate_presigned_url.side_effect = (
        lambda *a, **kw: f"https://signed/{kw['Params']['Key']}")

    mywebsite._S3_CLIENTS.clear()
    with patch.object(mywebsite, "boto3") as fake:
        fake.client.return_value = client
        yield client
    mywebsite._S3_CLIENTS.clear()


class TestCalendarRoute:
    """The new calendar URLs reach the handler and render their window."""

    def test_default_page_shows_seven_nights(self, mywebsite, astro_s3,
                                             make_event, make_context):
        result = mywebsite.lambda_handler(
            make_event("/astro/astrocam"), make_context())
        assert result["statusCode"] == 200
        body = result["body"]
        assert body.count('class="night-card"') == 7
        assert "2026-08-23" in body
        assert "2026-08-16" not in body  # outside the window
        assert "last 7 days" in body

    def test_default_page_presigns_only_the_window(self, mywebsite, astro_s3,
                                                   make_event, make_context):
        # The whole point of the change: 7 presigns, not one per published
        # night. Each presign is a ~0.14s boto3 client build on a 128MB
        # Lambda when the client is not cached.
        mywebsite.lambda_handler(make_event("/astro/astrocam"), make_context())
        assert astro_s3.generate_presigned_url.call_count == 7

    def test_week_link_renders_that_block(self, mywebsite, astro_s3,
                                          make_event, make_context):
        result = mywebsite.lambda_handler(
            make_event("/astro/astrocam/week/2026-08-10"), make_context())
        assert result["statusCode"] == 200
        assert result["body"].count('class="night-card"') == 7
        assert "2026-08-16" in result["body"]
        assert "2026-08-23" not in result["body"]

    def test_month_link_renders_that_month(self, mywebsite, astro_s3,
                                           make_event, make_context):
        result = mywebsite.lambda_handler(
            make_event("/astro/astrocam/month/2026-07"), make_context())
        assert result["statusCode"] == 200
        assert result["body"].count('class="night-card"') == 31

    def test_all_renders_full_history(self, mywebsite, astro_s3,
                                      make_event, make_context):
        result = mywebsite.lambda_handler(
            make_event("/astro/astrocam/all"), make_context())
        assert result["statusCode"] == 200
        assert result["body"].count('class="night-card"') == len(_nights())

    def test_calendar_links_out_compactly(self, mywebsite, astro_s3,
                                          make_event, make_context):
        # The week/month lists moved to /nights; the calendar carries a
        # single link to it, not two rows of chips that grow forever.
        body = mywebsite.lambda_handler(
            make_event("/astro/astrocam"), make_context())["body"]
        assert '/astro/astrocam/nights' in body
        assert body.count('/astro/astrocam/week/') == 0
        assert body.count('/astro/astrocam/month/') == 0

    def test_window_label_shown_on_every_window(self, mywebsite, astro_s3,
                                                make_event, make_context):
        for path, label in (("/astro/astrocam", "last 7 days"),
                            ("/astro/astrocam/week/2026-08-10",
                             "10 Aug–16 Aug"),
                            ("/astro/astrocam/month/2026-07", "July 2026"),
                            ("/astro/astrocam/all", "all nights")):
            body = mywebsite.lambda_handler(
                make_event(path), make_context())["body"]
            assert label in body, path
            assert '/astro/astrocam/nights' in body, path


class TestNightsIndex:
    """/astro/<cam>/nights — the week/month index."""

    def test_lists_every_week_and_month(self, mywebsite, astro_s3,
                                        make_event, make_context):
        result = mywebsite.lambda_handler(
            make_event("/astro/astrocam/nights"), make_context())
        assert result["statusCode"] == 200
        body = result["body"]
        _, _, weeks, months = astro_calendar_window(_nights())
        for w in weeks:
            assert f'/astro/astrocam/week/{w["start"]}' in body
        for m in months:
            assert f'/astro/astrocam/month/{m["key"]}' in body
        assert '/astro/astrocam/all' in body

    def test_costs_no_presigns(self, mywebsite, astro_s3,
                               make_event, make_context):
        # It is a page of links; thumbnails are what made the calendar slow.
        mywebsite.lambda_handler(
            make_event("/astro/astrocam/nights"), make_context())
        assert astro_s3.generate_presigned_url.call_count == 0

    def test_shows_night_counts(self, mywebsite, astro_s3,
                                make_event, make_context):
        body = mywebsite.lambda_handler(
            make_event("/astro/astrocam/nights"), make_context())["body"]
        assert "7 nights" in body        # a full week block
        assert "31 nights" in body       # July
        assert f"{len(_nights())} nights across 3 months" in body

    def test_links_back_to_the_calendar(self, mywebsite, astro_s3,
                                        make_event, make_context):
        body = mywebsite.lambda_handler(
            make_event("/astro/astrocam/nights"), make_context())["body"]
        assert 'href="/astro/astrocam"' in body

    def test_counts_are_accurate_with_gaps(self):
        nights = ["2026-08-23", "2026-08-22", "2026-08-01"]
        _, _, weeks, months = astro_calendar_window(nights)
        assert weeks[0]["count"] == 2
        assert sum(w["count"] for w in weeks) == len(nights)
        assert [m["count"] for m in months] == [3]


class TestS3ClientCache:
    def test_client_is_reused_per_region(self, mywebsite):
        from unittest.mock import patch
        mywebsite._S3_CLIENTS.clear()
        with patch.object(mywebsite, "boto3") as fake:
            a = mywebsite.s3_client()
            b = mywebsite.s3_client()
            assert a is b
            assert fake.client.call_count == 1
        mywebsite._S3_CLIENTS.clear()
