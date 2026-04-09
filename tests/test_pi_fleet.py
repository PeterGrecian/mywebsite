"""Tests for the extracted pi-fleet route handler."""

import pytest
from datetime import datetime, timezone, timedelta


@pytest.fixture
def pi_fleet(mywebsite):
    """Import the pi_fleet route module."""
    from routes import pi_fleet
    return pi_fleet


@pytest.fixture
def helpers(mywebsite):
    """Bundle the utility functions the renderer needs."""
    return {
        "is_pi_online": mywebsite.is_pi_online,
        "format_uptime": mywebsite.format_uptime,
        "format_age": mywebsite.format_age,
        "format_to_sigfigs": mywebsite.format_to_sigfigs,
        "theme_css_js": mywebsite.THEME_CSS_JS,
    }


def _make_pi(hostname, online=True, **overrides):
    """Build a test Pi status dict."""
    now = datetime.now(timezone.utc)
    last_seen = (now - timedelta(seconds=30)).isoformat() if online else (now - timedelta(hours=2)).isoformat()
    pi = {
        "hostname": hostname,
        "last_seen": last_seen,
        "cpu_model": "BCM2711",
        "card_id": "A1B2",
        "local_ip": "192.168.1.10",
        "app_name": "gardencam",
        "uptime_seconds": 86400,
        "cpu_percent": 15,
        "memory_percent": 42,
        "memory_total_mb": 4096,
        "disk_percent": 55,
        "disk_total_gb": 32,
        "os_version": "Debian 12 (bookworm)",
    }
    pi.update(overrides)
    return pi


class TestRenderPiFleetPage:
    def test_empty_fleet(self, pi_fleet, helpers):
        html = pi_fleet.render_pi_fleet_page([], **helpers)
        assert "No Devices Found" in html
        assert "Pi Fleet Status" in html

    def test_single_online_pi(self, pi_fleet, helpers):
        pis = [_make_pi("homepi")]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert "homepi" in html
        assert "Online" in html
        assert "CPU" in html
        assert "Memory" in html

    def test_single_offline_pi(self, pi_fleet, helpers):
        pis = [_make_pi("deskpi", online=False)]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert "deskpi" in html
        assert "Offline" in html

    def test_summary_counts(self, pi_fleet, helpers):
        pis = [
            _make_pi("homepi", online=True),
            _make_pi("deskpi", online=False),
            _make_pi("camerapi", online=True),
        ]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        # Check summary section has correct counts
        assert 'class="summary-value online">2<' in html
        assert 'class="summary-value offline">1<' in html
        assert 'class="summary-value total">3<' in html

    def test_wifi_shown_when_present(self, pi_fleet, helpers):
        pis = [_make_pi("zeropi", wifi_interface="wlan0: RTL8811CU")]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert "WiFi" in html
        assert "RTL8811CU" in html

    def test_wifi_hidden_when_absent(self, pi_fleet, helpers):
        pis = [_make_pi("homepi")]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert "WiFi" not in html

    def test_tunnel_shown_when_active(self, pi_fleet, helpers):
        pis = [_make_pi("camerapi", tunnel_active=True, tunnel_port=2222, bastion_host="homepi")]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert "SSH Tunnel" in html
        assert "Port 2222" in html

    def test_boot_progress_shown(self, pi_fleet, helpers):
        pis = [_make_pi("newpi", boot_progress="boot-stage-2", message="Installing packages...")]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert "Boot Progress" in html
        assert "boot-stage-2" in html

    def test_error_shown(self, pi_fleet, helpers):
        pis = [_make_pi("badpi", error="Disk full")]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert "Disk full" in html

    def test_error_truncated(self, pi_fleet, helpers):
        pis = [_make_pi("badpi", error="x" * 300)]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert "..." in html

    def test_card_id_falls_back_to_sd_cid(self, pi_fleet, helpers):
        pis = [_make_pi("homepi", card_id=None, sd_cid="ABCDEF1234")]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert "1234" in html

    def test_memory_displays_in_gb(self, pi_fleet, helpers):
        pis = [_make_pi("homepi", memory_total_mb=4096)]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert "of 4G" in html

    def test_memory_displays_in_mb(self, pi_fleet, helpers):
        pis = [_make_pi("zeropi", memory_total_mb=512)]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert "of 512M" in html

    def test_is_valid_html(self, pi_fleet, helpers):
        pis = [_make_pi("homepi")]
        html = pi_fleet.render_pi_fleet_page(pis, **helpers)
        assert html.strip().startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_auto_refresh_script(self, pi_fleet, helpers):
        html = pi_fleet.render_pi_fleet_page([], **helpers)
        assert "setInterval(updateCountdown" in html
