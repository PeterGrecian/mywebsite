"""Tests for bulk per-date image counts on the gallery year/month/week views.

Those views only ever needed counts, but got them by calling
get_<cam>_images_for_date() once per day — one boto3 client build plus one
S3 round trip each. A year view was ~365 of those and reliably hit the 30s
Lambda timeout, so /starcam/gallery?year=2026 and its skycam and springcam
equivalents returned 503. count_images_by_date() gets the same numbers from
one listing per prefix.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "lambda")))


class TestDateFromKey:
    """Which day a key is counted against."""

    def test_starcam_filename(self, mywebsite):
        assert mywebsite._date_from_key(
            "frames/star_20260517_111057_stacked.jpg") == "2026-05-17"

    def test_springcam_filename(self, mywebsite):
        assert mywebsite._date_from_key(
            "springcam/spring_20260305_185436_stacked.jpg") == "2026-03-05"

    def test_skycam_flat_layout(self, mywebsite):
        assert mywebsite._date_from_key(
            "skycam/sky_20260406_093515.jpg") == "2026-04-06"

    def test_skycam_path_layout(self, mywebsite):
        assert mywebsite._date_from_key(
            "skycam/2026/04/18/sky_20260418_120000.jpg") == "2026-04-18"

    def test_path_wins_over_filename_across_midnight(self, mywebsite):
        # A real key in the bucket: written into the 19th's folder with a
        # post-midnight filename. get_skycam_images_for_date selects by
        # folder prefix, so the day page shows it on the 19th — the count
        # must agree or the month view is off by one against its own link.
        assert mywebsite._date_from_key(
            "skycam/2026/04/19/sky_20260420_000132.jpg") == "2026-04-19"

    def test_unparseable_key(self, mywebsite):
        assert mywebsite._date_from_key("skycam/index.html") is None


class TestPeriodPrefixes:
    """Prefixes must be truncations of what the per-date lookups use, so the
    set of objects counted is identical."""

    def test_starcam_year_and_month(self, mywebsite):
        bucket, prefixes = mywebsite._camera_period_prefixes(
            "starcam", "2026")
        assert bucket == mywebsite.STARCAM_BUCKET
        assert prefixes == ["frames/star_2026"]
        _, prefixes = mywebsite._camera_period_prefixes("starcam", "2026-07")
        assert prefixes == ["frames/star_202607"]

    def test_springcam(self, mywebsite):
        bucket, prefixes = mywebsite._camera_period_prefixes(
            "springcam", "2026-03")
        assert bucket == mywebsite.GARDENCAM_BUCKET
        assert prefixes == ["springcam/spring_202603"]

    def test_skycam_covers_both_layouts(self, mywebsite):
        _, prefixes = mywebsite._camera_period_prefixes("skycam", "2026-04")
        assert prefixes == ["skycam/2026/04/", "skycam/sky_202604"]
        _, prefixes = mywebsite._camera_period_prefixes("skycam", "2026")
        assert prefixes == ["skycam/2026/", "skycam/sky_2026"]

    def test_month_prefix_is_a_truncation_of_the_day_prefix(self, mywebsite):
        # The per-date lookup for starcam uses frames/star_<YYYYMMDD>.
        _, month = mywebsite._camera_period_prefixes("starcam", "2026-07")
        assert "frames/star_20260704".startswith(month[0])

    def test_unknown_camera(self, mywebsite):
        with pytest.raises(ValueError):
            mywebsite._camera_period_prefixes("gardencam", "2026")


@pytest.fixture
def s3_pages(mywebsite):
    """Stub S3 whose paginator yields a fixed set of keys per prefix."""
    from unittest.mock import MagicMock, patch

    keys = {
        "skycam/2026/04/": [
            "skycam/2026/04/18/sky_20260418_120000.jpg",
            "skycam/2026/04/18/sky_20260418_130000.jpg",
            "skycam/2026/04/19/sky_20260419_120000.jpg",
            "skycam/2026/04/19/sky_20260420_000132.jpg",  # midnight crosser
            "skycam/2026/04/19/index.html",               # not a jpg
        ],
        "skycam/sky_202604": [
            "skycam/sky_20260406_093515.jpg",
        ],
    }

    client = MagicMock()
    paginator = MagicMock()
    paginator.paginate.side_effect = lambda **kw: [
        {"Contents": [{"Key": k} for k in keys.get(kw["Prefix"], [])]}]
    client.get_paginator.return_value = paginator

    mywebsite._S3_CLIENTS.clear()
    with patch.object(mywebsite, "boto3") as fake:
        fake.client.return_value = client
        yield client
    mywebsite._S3_CLIENTS.clear()


class TestCountImagesByDate:
    def test_counts_across_both_skycam_layouts(self, mywebsite, s3_pages):
        counts = mywebsite.count_images_by_date("skycam", "2026-04")
        assert counts == {
            "2026-04-06": 1,   # flat layout
            "2026-04-18": 2,
            "2026-04-19": 2,   # includes the midnight crosser
        }

    def test_non_jpg_keys_are_ignored(self, mywebsite, s3_pages):
        counts = mywebsite.count_images_by_date("skycam", "2026-04")
        assert sum(counts.values()) == 5  # 6 keys, one is index.html

    def test_one_listing_per_prefix(self, mywebsite, s3_pages):
        # The whole point: not one round trip per day.
        mywebsite.count_images_by_date("skycam", "2026-04")
        assert s3_pages.get_paginator.return_value.paginate.call_count == 2

    def test_builds_one_client(self, mywebsite, s3_pages):
        mywebsite.count_images_by_date("skycam", "2026-04")
        mywebsite.count_images_by_date("skycam", "2026-04")
        # Cached across calls — the client build was the original 0.14s cost.
        assert mywebsite.boto3.client.call_count == 1

    def test_s3_failure_returns_empty_not_an_exception(self, mywebsite):
        from unittest.mock import patch
        mywebsite._S3_CLIENTS.clear()
        with patch.object(mywebsite, "s3_client",
                          side_effect=Exception("S3 down")):
            assert mywebsite.count_images_by_date("skycam", "2026-04") == {}
        mywebsite._S3_CLIENTS.clear()
