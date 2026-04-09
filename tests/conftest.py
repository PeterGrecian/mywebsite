"""Shared fixtures for mywebsite tests.

The Lambda module calls boto3 SSM at import time (get_parameter for passwords/keys).
We must patch boto3 before importing the module.
"""

import sys
import types
from unittest.mock import MagicMock
import pytest


@pytest.fixture(scope="session", autouse=True)
def _mock_boto3():
    """Replace boto3 with a stub before mywebsite is imported."""
    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = MagicMock(return_value=MagicMock(
        get_parameter=MagicMock(return_value={
            "Parameter": {"Value": "test-password"}
        })
    ))
    fake_boto3.resource = MagicMock()
    fake_boto3.dynamodb = MagicMock()
    sys.modules["boto3"] = fake_boto3
    sys.modules["boto3.dynamodb"] = fake_boto3.dynamodb
    sys.modules["boto3.dynamodb.conditions"] = MagicMock()


@pytest.fixture(scope="session")
def mywebsite():
    """Import the Lambda module (with boto3 already mocked)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mywebsite", "lambda/mywebsite.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_event(path, method="GET", headers=None, body=None, stage="default"):
    """Build a minimal API Gateway v2 event."""
    h = {
        "host": "www.petergrecian.co.uk",
        "X-Forwarded-For": "127.0.0.1",
        "user-agent": "pytest",
    }
    if headers:
        h.update(headers)
    event = {
        "rawPath": path,
        "requestContext": {"stage": stage, "http": {"method": method}},
        "headers": h,
    }
    if body is not None:
        event["body"] = body
    return event


def _make_context():
    """Build a minimal Lambda context object."""

    class Ctx:
        log_group_name = "test-group"
        log_stream_name = "test-stream"
        aws_request_id = "test-request-id"
        function_name = "mywebsite-test"
        memory_limit_in_mb = 128

    return Ctx()


@pytest.fixture(scope="session")
def make_event():
    return _make_event


@pytest.fixture(scope="session")
def make_context():
    return _make_context
