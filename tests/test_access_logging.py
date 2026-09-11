"""Which requests buy a DynamoDB write.

log_connection() used to run before any routing, so every favicon fetch,
robots.txt and bot probe cost one. That meter scales with a flood exactly
as the invocation meter does — it is the cost liability, not the latency.
"""

from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def mod():
    from golden_sweep import _build_module
    return _build_module()


def _call(mod, path, fmt="v1"):
    """Dispatch one request, returning the log_connection call count."""
    import contextlib, io, os
    from golden_sweep import _event, _context, LAMBDA_DIR

    cwd = os.getcwd()
    try:
        os.chdir(LAMBDA_DIR)
        with patch.object(mod, "log_connection") as logged:
            with contextlib.redirect_stdout(io.StringIO()):
                mod.lambda_handler(_event(path, fmt=fmt), _context())
        return logged.call_count
    finally:
        os.chdir(cwd)


LOGGED = ["/", "/contents", "/cv", "/pi-fleet", "/skycam", "/gardencam/stats"]
UNLOGGED = ["/favicon.ico", "/favicon.png", "/favicon.svg", "/tick.png", "/robots.txt"]
PROBES = ["/wp-login.php", "/no-such-page", "/.env", "/admin/config.php"]


@pytest.mark.parametrize("path", LOGGED)
def test_real_pages_are_logged(mod, path):
    assert _call(mod, path) == 1, f"{path} should record a visit"


@pytest.mark.parametrize("path", UNLOGGED)
def test_static_assets_are_not_logged(mod, path):
    """A favicon is not a visit, and it is requested on every page load."""
    assert _call(mod, path) == 0, f"{path} bought a DynamoDB write"


@pytest.mark.parametrize("path", PROBES)
def test_bot_probes_are_not_logged(mod, path):
    """Unclaimed paths 404 without a write — a scanner cannot run up the bill.

    They stay visible: _access_log() still emits a CloudWatch line per
    request with path, status, IP and user-agent.
    """
    assert _call(mod, path) == 0, f"{path} bought a DynamoDB write"


def test_dynamodb_resource_is_cached(mod):
    """Built once per execution environment, not once per invocation.

    boto3.resource() re-parses the service model on every build; doing that
    on the hottest path in the site was the single most expensive instance
    of the mistake s3_client() already fixed.
    """
    a = mod.dynamodb_resource()
    b = mod.dynamodb_resource()
    assert a is b
    assert mod.dynamodb_resource("eu-west-1") is a
