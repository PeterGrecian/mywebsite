"""Tests for pure utility functions — no AWS calls, no mocking needed."""

import pytest


class TestFormatToSigfigs:
    def test_zero(self, mywebsite):
        assert mywebsite.format_to_sigfigs(0) == 0

    def test_whole_number(self, mywebsite):
        assert mywebsite.format_to_sigfigs(1234, 3) == 1240

    def test_small_float(self, mywebsite):
        assert mywebsite.format_to_sigfigs(0.001234, 3) == 0.00124

    def test_rounds_up(self, mywebsite):
        # ceil behaviour — 1231 should round up to 1240
        assert mywebsite.format_to_sigfigs(1231, 3) == 1240

    def test_exact_value(self, mywebsite):
        assert mywebsite.format_to_sigfigs(1000, 3) == 1000

    def test_two_sigfigs(self, mywebsite):
        assert mywebsite.format_to_sigfigs(456, 2) == 460

    def test_one_sigfig(self, mywebsite):
        assert mywebsite.format_to_sigfigs(7, 1) == 7

    def test_returns_int_for_whole(self, mywebsite):
        result = mywebsite.format_to_sigfigs(1200, 2)
        assert isinstance(result, int)

    def test_decimal_input(self, mywebsite):
        from decimal import Decimal
        result = mywebsite.format_to_sigfigs(Decimal("123.4"), 3)
        assert result == 124


class TestParseTimestampFromKey:
    def test_standard_key(self, mywebsite):
        result = mywebsite.parse_timestamp_from_key("garden_20260119_185439.jpg")
        assert result == "2026-01-19 18:54:39"

    def test_with_prefix(self, mywebsite):
        result = mywebsite.parse_timestamp_from_key("photos/garden_20260301_120000.jpg")
        # prefix adds an extra part before garden, so garden becomes index 1
        # actually split on _ gives: ['photos/garden', '20260301', '120000']
        assert result == "2026-03-01 12:00:00"

    def test_invalid_key(self, mywebsite):
        assert mywebsite.parse_timestamp_from_key("random_file.txt") is None

    def test_too_few_parts(self, mywebsite):
        assert mywebsite.parse_timestamp_from_key("garden.jpg") is None


class TestFormatUptime:
    def test_minutes_only(self, mywebsite):
        assert mywebsite.format_uptime(300) == "5m"

    def test_hours_and_minutes(self, mywebsite):
        assert mywebsite.format_uptime(3660) == "1h 1m"

    def test_days_hours_minutes(self, mywebsite):
        assert mywebsite.format_uptime(90060) == "1d 1h 1m"

    def test_zero(self, mywebsite):
        assert mywebsite.format_uptime(0) == "Unknown"

    def test_none(self, mywebsite):
        assert mywebsite.format_uptime(None) == "Unknown"

    def test_exact_day(self, mywebsite):
        assert mywebsite.format_uptime(86400) == "1d"

    def test_exact_hour(self, mywebsite):
        assert mywebsite.format_uptime(3600) == "1h"

    def test_under_a_minute(self, mywebsite):
        assert mywebsite.format_uptime(30) == "0m"


class TestCategorizePath:
    def test_root(self, mywebsite):
        assert mywebsite.categorize_path("/") == "root"

    def test_empty(self, mywebsite):
        assert mywebsite.categorize_path("") == "root"

    def test_none(self, mywebsite):
        assert mywebsite.categorize_path(None) == "root"

    def test_gardencam(self, mywebsite):
        assert mywebsite.categorize_path("/gardencam") == "gardencam"

    def test_gardencam_gallery(self, mywebsite):
        assert mywebsite.categorize_path("/gardencam/gallery") == "gardencam"

    def test_t3(self, mywebsite):
        assert mywebsite.categorize_path("/t3") == "t3-bus"

    def test_t3_parklands(self, mywebsite):
        assert mywebsite.categorize_path("/t3?stop=parklands") == "t3-bus"

    def test_lambda_stats(self, mywebsite):
        assert mywebsite.categorize_path("/lambda-stats") == "lambda-stats"

    def test_memspeed(self, mywebsite):
        assert mywebsite.categorize_path("/memspeed") == "memspeed"

    def test_contents(self, mywebsite):
        assert mywebsite.categorize_path("/contents") == "contents"

    def test_gitinfo(self, mywebsite):
        assert mywebsite.categorize_path("/gitinfo") == "gitinfo"

    def test_event(self, mywebsite):
        assert mywebsite.categorize_path("/event") == "debug"

    def test_unknown(self, mywebsite):
        assert mywebsite.categorize_path("/something-else") == "other"

    def test_case_insensitive(self, mywebsite):
        assert mywebsite.categorize_path("/GARDENCAM") == "gardencam"


class TestT3SecondsToQuarterMinutes:
    def test_exact_minutes(self, mywebsite):
        assert mywebsite.t3_seconds_to_quarter_minutes(300) == "5"

    def test_quarter(self, mywebsite):
        assert mywebsite.t3_seconds_to_quarter_minutes(315) == "5\u00bc"

    def test_half(self, mywebsite):
        assert mywebsite.t3_seconds_to_quarter_minutes(330) == "5\u00bd"

    def test_three_quarter(self, mywebsite):
        assert mywebsite.t3_seconds_to_quarter_minutes(345) == "5\u00be"

    def test_zero(self, mywebsite):
        assert mywebsite.t3_seconds_to_quarter_minutes(0) == "0"

    def test_just_under_quarter(self, mywebsite):
        assert mywebsite.t3_seconds_to_quarter_minutes(314) == "5"

    def test_just_under_half(self, mywebsite):
        assert mywebsite.t3_seconds_to_quarter_minutes(329) == "5\u00bc"

    def test_just_under_three_quarter(self, mywebsite):
        assert mywebsite.t3_seconds_to_quarter_minutes(344) == "5\u00bd"

    def test_59_seconds(self, mywebsite):
        assert mywebsite.t3_seconds_to_quarter_minutes(59) == "0\u00be"


class TestCalculateTimeDelta:
    def test_minutes(self, mywebsite):
        result = mywebsite.calculate_time_delta("12:00:00", "12:05:00")
        assert result == "+5m"

    def test_hours_and_minutes(self, mywebsite):
        result = mywebsite.calculate_time_delta("10:00:00", "11:30:00")
        assert result == "+1h 30m"

    def test_exact_hour(self, mywebsite):
        result = mywebsite.calculate_time_delta("10:00:00", "11:00:00")
        assert result == "+1h"

    def test_under_minute(self, mywebsite):
        result = mywebsite.calculate_time_delta("10:00:00", "10:00:30")
        assert result == "+<1m"

    def test_full_datetime(self, mywebsite):
        result = mywebsite.calculate_time_delta(
            "2026-01-19 10:00:00", "2026-01-19 10:15:00"
        )
        assert result == "+15m"

    def test_none_input(self, mywebsite):
        assert mywebsite.calculate_time_delta(None, "12:00:00") == ""
        assert mywebsite.calculate_time_delta("12:00:00", None) == ""

    def test_empty_input(self, mywebsite):
        assert mywebsite.calculate_time_delta("", "12:00:00") == ""


class TestCheckBasicAuth:
    def test_valid_credentials(self, mywebsite):
        import base64
        creds = base64.b64encode(b"user:test-password").decode()
        event = {"headers": {"Authorization": f"Basic {creds}"}}
        assert mywebsite.check_basic_auth(event, "test-password") is True

    def test_wrong_password(self, mywebsite):
        import base64
        creds = base64.b64encode(b"user:wrong").decode()
        event = {"headers": {"Authorization": f"Basic {creds}"}}
        assert mywebsite.check_basic_auth(event, "test-password") is False

    def test_no_auth_header(self, mywebsite):
        event = {"headers": {}}
        assert mywebsite.check_basic_auth(event, "test-password") is False

    def test_lowercase_header(self, mywebsite):
        import base64
        creds = base64.b64encode(b"user:test-password").decode()
        event = {"headers": {"authorization": f"Basic {creds}"}}
        assert mywebsite.check_basic_auth(event, "test-password") is True

    def test_malformed_base64(self, mywebsite):
        event = {"headers": {"Authorization": "Basic not-valid-base64!!!"}}
        assert mywebsite.check_basic_auth(event, "test-password") is False

    def test_no_colon_in_credentials(self, mywebsite):
        import base64
        creds = base64.b64encode(b"no-colon-here").decode()
        event = {"headers": {"Authorization": f"Basic {creds}"}}
        # split(':', 1) with no colon raises ValueError
        assert mywebsite.check_basic_auth(event, "test-password") is False

    def test_empty_headers(self, mywebsite):
        event = {}
        assert mywebsite.check_basic_auth(event, "test-password") is False


class TestFormatStatsForDisplay:
    def test_with_stats(self, mywebsite):
        stats = {"avg_brightness": 128.456, "image_diff": 12.345, "noise_floor": 5.678}
        result = mywebsite.format_stats_for_display(stats)
        assert "B:" in result
        assert "\u0394:" in result  # Δ
        assert "SD:" in result

    def test_empty_stats(self, mywebsite):
        assert mywebsite.format_stats_for_display(None) == ""
        assert mywebsite.format_stats_for_display({}) == ""


class TestTokenCost:
    def test_known_model(self, mywebsite):
        # gpt-4.1-mini: (0.40, 1.60) per million
        cost = mywebsite._token_cost("gpt-4.1-mini", 1_000_000, 1_000_000)
        assert cost == pytest.approx(2.0)

    def test_unknown_model(self, mywebsite):
        assert mywebsite._token_cost("unknown-model", 1000, 1000) == 0.0

    def test_zero_tokens(self, mywebsite):
        assert mywebsite._token_cost("gpt-4.1-mini", 0, 0) == 0.0
