"""Shared sweep used by the golden test and the regeneration script.

Kept out of conftest.py deliberately: it builds its OWN module instance and
chdirs into lambda/, because several routes (cv, gitinfo) read files
relative to the working directory exactly as they do in /var/task. Doing
that in a session fixture would leak the chdir into every other test.
"""

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


def _build_module():
    import importlib.util

    _install_boto3_stub()
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
    mod = _build_module()
    old_cwd = os.getcwd()
    old_stdout = sys.stdout
    results = {}
    try:
        os.chdir(LAMBDA_DIR)
        devnull = open(os.devnull, "w")
        for path in paths:
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
