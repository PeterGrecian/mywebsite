"""Shared sweep used by the golden test and the regeneration script.

Kept out of conftest.py deliberately: it builds its OWN module instance and
chdirs into lambda/, because several routes (cv, gitinfo) read files
relative to the working directory exactly as they do in /var/task. Doing
that in a session fixture would leak the chdir into every other test.
"""

import contextlib
import hashlib
import json
import os
import re
import sys
import types
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
LAMBDA_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "lambda"))
GOLDEN_PATH = os.path.join(TESTS_DIR, "golden_routes.json")


def _install_boto3_stub():
    """Mirror conftest's stub so this module also works standalone."""
    if isinstance(sys.modules.get("boto3"), types.ModuleType) and hasattr(
        sys.modules["boto3"], "_is_golden_stub"
    ):
        return

    def _get_parameters(Names, **kwargs):
        return {
            "Parameters": [{"Name": n, "Value": "test-password"} for n in Names],
            "InvalidParameters": [],
        }

    fake = types.ModuleType("boto3")
    fake._is_golden_stub = True
    fake.client = MagicMock(
        return_value=MagicMock(
            get_parameter=MagicMock(return_value={"Parameter": {"Value": "test-password"}}),
            get_parameters=MagicMock(side_effect=_get_parameters),
        )
    )
    fake.resource = MagicMock()
    fake.dynamodb = MagicMock()
    sys.modules["boto3"] = fake
    sys.modules["boto3.dynamodb"] = fake.dynamodb
    sys.modules["boto3.dynamodb.conditions"] = MagicMock()


# ---------------------------------------------------------------------------
# Build stamps are pinned, not normalised.
#
# `./deploy` writes two files that nothing tracks in git: build_info.py (the
# version, commit, commit time, deploy counter and deploy time) and
# gitinfo.html (the origin, the commit subject and the commit date). Most
# pages render some of it -- /skycam's top bar carries the pet name, which is
# seeded from "<commit>#<deploy>" precisely so that it changes on EVERY
# deploy.
#
# Left alone, that meant every deploy reddened ~129 routes on both payload
# shapes whether or not any behaviour had moved, and the only way back to
# green was a regen whose diff was then too noisy to read -- which defeats
# the point of a golden master. So the sweep supplies its own fixed versions
# of both artefacts and puts the real ones back afterwards. A build stamp
# then cannot drift, and a `sha`/`len` change means the RENDERING changed.
#
# Pinning rather than post-hoc normalising also keeps `len` honest: the
# snapshot records the raw body length, and a regex that rewrites the body
# after the fact cannot fix a length. The stamp is constant in the body, so
# the length is constant too.
_PINNED_BUILD_INFO = {
    "VERSION": "0.0.0-golden",
    "COMMIT": "0000000",
    "COMMIT_TIME": "2000-01-01T00:00:00+00:00",
    "DEPLOY_COUNT": 0,
    "DEPLOY_TIME": 946684800,
    "GARDENCAM_VERSION": "0.0.0-golden",
    "GARDENCAM_COMMIT": "0000000",
    "GARDENCAM_COMMIT_TIME": "2000-01-01T00:00:00+00:00",
}

_PINNED_GITINFO = (
    "<title>Peter Grecian - Git Info</title>\n"
    "<body>\n"
    "git@github.com:PeterGrecian/mywebsite.git<br>"
    "0000000 golden<br>Sat Jan 1 00:00:00 GMT 2000<br>\n"
    '<a href="https://github.com/PeterGrecian/mywebsite/commit/0000000">'
    "https://github.com/PeterGrecian/mywebsite/commit/0000000</a>\n"
    "</body></html>\n"
)


def _install_build_info_stub():
    """Put a fixed `build_info` in sys.modules before anything imports it.

    routes/gardencam.py binds its values at import time, so this has to be in
    place before the module is built -- and it stays installed, because the
    module cache is shared with any later sweep in the same process.
    """
    existing = sys.modules.get("build_info")
    if isinstance(existing, types.ModuleType) and getattr(existing, "_is_golden_stub", False):
        return
    stub = types.ModuleType("build_info")
    stub._is_golden_stub = True
    for k, v in _PINNED_BUILD_INFO.items():
        setattr(stub, k, v)
    sys.modules["build_info"] = stub


def _with_pinned_gitinfo(paths):
    """Iterate `paths` with the fixed gitinfo.html in place.

    A generator so the swap is undone by the sweep's own teardown, however
    the loop ends -- an exception mid-sweep must not leave a stub file where
    the deploy artefact belongs.
    """
    with _pinned_gitinfo():
        yield from paths


@contextlib.contextmanager
def _pinned_gitinfo():
    """Swap in a fixed gitinfo.html for the duration of the sweep.

    /gitinfo serves the file verbatim, and deploy regenerates it with the
    current commit subject -- prose no regex could normalise. The real file
    (or its absence, on a tree that has never deployed) is restored on the
    way out.
    """
    path = os.path.join(LAMBDA_DIR, "gitinfo.html")
    had = os.path.exists(path)
    original = open(path, "rb").read() if had else None
    try:
        with open(path, "w") as f:
            f.write(_PINNED_GITINFO)
        yield
    finally:
        if had:
            with open(path, "wb") as f:
                f.write(original)
        elif os.path.exists(path):
            os.remove(path)


# ---------------------------------------------------------------------------
# The clock is pinned, for the same reason the build stamps are.
#
# Several camera pages build a date list that runs from a fixed start date to
# TODAY (mywebsite.py's gallery sweeps) or anchor a calendar on today
# (routes/camera.py's `_date.today()`). Those pages therefore grow by a row a
# day, so a snapshot taken on Monday is red on Tuesday with nothing having
# changed. Measured 2026-09-23: 107 of 979 routes drifted purely on the
# calendar, and freezing both `datetime` and `date` took it to zero against
# the SAME golden file — the snapshot was right and the sweep was wrong.
#
# Note it takes both classes. Freezing `datetime` alone still left the six
# starcam routes red, because that calendar asks `date.today()`, not
# `datetime.utcnow()`.
#
# GOLDEN_DAY must not be moved casually: it is the day the snapshot describes,
# so changing it is a regen, not a tidy-up.
_GOLDEN_DAY = (2026, 9, 21)


def _frozen_datetime_module():
    import datetime as real

    frozen_date = real.date(*_GOLDEN_DAY)
    frozen_dt = real.datetime(*_GOLDEN_DAY, 12, 0, 0)

    class _DateTime(real.datetime):
        @classmethod
        def utcnow(cls):
            return frozen_dt

        @classmethod
        def now(cls, tz=None):
            return frozen_dt if tz is None else frozen_dt.replace(tzinfo=tz)

        @classmethod
        def today(cls):
            return frozen_dt

    class _Date(real.date):
        @classmethod
        def today(cls):
            return frozen_date

    stub = types.ModuleType("datetime")
    for name in dir(real):
        if not name.startswith("__"):
            setattr(stub, name, getattr(real, name))
    stub.datetime = _DateTime
    stub.date = _Date
    stub._is_golden_stub = True
    return stub


@contextlib.contextmanager
def _pinned_clock():
    """Freeze the clock for the sweep, then put the real module back.

    It stays installed for the WHOLE sweep, not just the import: routes are
    imported lazily inside handlers, so a stub removed after _build_module()
    would leave the late arrivals (routes/camera.py among them) on the real
    clock.
    """
    real = sys.modules.get("datetime")
    sys.modules["datetime"] = _frozen_datetime_module()
    try:
        yield
    finally:
        if real is not None:
            sys.modules["datetime"] = real
        else:
            del sys.modules["datetime"]


def _build_module():
    import importlib.util

    _install_boto3_stub()
    _install_build_info_stub()
    if LAMBDA_DIR not in sys.path:
        sys.path.insert(0, LAMBDA_DIR)
    spec = importlib.util.spec_from_file_location(
        "mywebsite_golden", os.path.join(LAMBDA_DIR, "mywebsite.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Everything here legitimately varies between runs; the determinism test
# proves this list is sufficient.
_NORMALISERS = [
    (re.compile(r"0x[0-9a-f]{6,}"), "0xADDR"),
    (re.compile(r"id='?\d{6,}'?"), "id=NNN"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*"), "TIMESTAMP"),
    (re.compile(r"\d{4}-\d{2}-\d{2}"), "DATE"),
    (re.compile(r"\b\d+\.\d+\s*(ms|s|seconds)\b"), "DUR"),
    (re.compile(r"MagicMock[^>]*>"), "MAGICMOCK>"),
    (re.compile(r"\d{2}:\d{2}(:\d{2})?"), "TIME"),
    # /event prints the working directory and its listing, as a deploy-time
    # sanity check. The listing's ORDER is filesystem order, which changes
    # whenever a file is written next to it -- __pycache__ and the deploy
    # artefacts move around -- and the path itself differs between a laptop
    # and /var/task.
    (re.compile(r"pwd = [^<]*<br>[^<]*<br>"), "pwd = PWD<br>LISTING<br>"),
    # /lambda-stats/data labels its histogram in days-ago, computed from the
    # clock, so the bucket boundaries slide through the day. Only a list made
    # entirely of one-decimal numbers is masked: a chart with real category
    # labels stays pinned.
    (re.compile(r'"labels": \["\d+\.\d"(?:, "\d+\.\d")*\]'), '"labels": [AGES]'),
]


def _normalise(body):
    for rx, repl in _NORMALISERS:
        body = rx.sub(repl, body)
    return body


def _event(path, stage="default", fmt="v2"):
    """Build an API Gateway event.

    Two shapes, because the dispatcher handles two and they are NOT
    interchangeable. The API is an HTTP API but with
    payload_format_version = "1.0" (terraform/api-gateway.tf:43), so
    PRODUCTION sends the v1 shape: `path`, and a capitalised `Host` header.
    The v2 shape (`rawPath`) is what the dispatcher's other arm reads.
    Sweeping only one of them leaves the live path untested.
    """
    headers = {
        "X-Forwarded-For": "127.0.0.1",
        "user-agent": "pytest",
    }
    if fmt == "v1":
        headers["Host"] = "www.petergrecian.co.uk"
        return {
            "path": path,
            "requestContext": {"stage": stage, "httpMethod": "GET"},
            "headers": headers,
        }
    headers["host"] = "www.petergrecian.co.uk"
    return {
        "rawPath": path,
        "requestContext": {"stage": stage, "http": {"method": "GET"}},
        "headers": headers,
    }


def _context():
    class Ctx:
        log_group_name = "test-group"
        log_stream_name = "test-stream"
        aws_request_id = "test-request-id"
        function_name = "mywebsite-test"
        memory_limit_in_mb = 128

    return Ctx()


def sweep_all(paths, fmt="v2"):
    """Dispatch every path and return a normalised snapshot dict."""
    with _pinned_clock():
        return _sweep_all_inner(paths, fmt)


def _sweep_all_inner(paths, fmt):
    mod = _build_module()
    old_cwd = os.getcwd()
    old_stdout = sys.stdout
    results = {}
    try:
        os.chdir(LAMBDA_DIR)
        devnull = open(os.devnull, "w")
        for path in _with_pinned_gitinfo(paths):
            sys.stdout = devnull          # routes print freely; keep test output readable
            try:
                resp = mod.lambda_handler(_event(path, fmt=fmt), _context())
                body = resp.get("body") or ""
                headers = resp.get("headers") or {}
                results[path] = {
                    "status": resp.get("statusCode"),
                    "ct": headers.get("Content-Type", ""),
                    "cache": headers.get("Cache-Control", ""),
                    "b64": bool(resp.get("isBase64Encoded")),
                    "hdrs": sorted(headers.keys()),
                    "sha": hashlib.sha256(_normalise(body).encode()).hexdigest()[:16],
                    "len": len(body),
                }
            except Exception as exc:
                results[path] = {"exception": type(exc).__name__}
            finally:
                sys.stdout = old_stdout
        devnull.close()
    finally:
        sys.stdout = old_stdout
        os.chdir(old_cwd)
    return results
