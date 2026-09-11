"""Golden-master characterisation of the dispatcher.

Why this exists: `_dispatch` is a long if/elif chain being converted to a
route table. A table lookup can silently change *which* branch claims a
path — precedence that `elif` order encoded implicitly is easy to lose —
and the failure is invisible in unit tests that only check the routes they
name. So this pins the observable response for EVERY route at once.

It records, per path: status, Content-Type, Cache-Control, isBase64Encoded,
the header key set, body length, and a sha of the normalised body. Bodies
are normalised (timestamps, mock addresses, durations) because those vary
per run; `test_snapshot_is_deterministic` proves the normalisation is
sufficient, so a diff here means a real behaviour change.

Regenerate deliberately (and read the diff) with:
    python3 tests/regen_golden.py
"""

import json
import os
import pytest

from golden_sweep import sweep_all, GOLDEN_PATH

GOLDEN_V1_PATH = GOLDEN_PATH.replace("golden_routes.json", "golden_routes_v1.json")


@pytest.fixture(scope="module")
def golden():
    with open(GOLDEN_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def current(golden):
    return sweep_all(sorted(golden.keys()))


def test_golden_file_covers_every_route(golden):
    """Guard against the snapshot quietly shrinking.

    Both URL forms (bare and /{stage}/-prefixed) are covered for every route,
    because the dispatcher strips the stage prefix and a regression there
    would otherwise only show on one of the two.
    """
    assert len(golden) >= 949, f"golden file only covers {len(golden)} paths"


@pytest.mark.parametrize("field", ["status", "ct", "cache", "b64", "hdrs", "sha", "len"])
def test_dispatch_matches_golden(golden, current, field):
    """Every route's response must be byte-identical to the snapshot."""
    drift = {
        p: (golden[p].get(field), current[p].get(field))
        for p in golden
        if golden[p].get(field) != current[p].get(field)
    }
    assert not drift, (
        f"{len(drift)} route(s) changed `{field}`:\n"
        + "\n".join(f"  {p}: golden={g!r} now={n!r}" for p, (g, n) in sorted(drift.items())[:20])
    )


def test_exceptions_match_golden(golden, current):
    """Routes that raise must keep raising the same type — and no new ones appear."""
    g = {p: v["exception"] for p, v in golden.items() if "exception" in v}
    c = {p: v["exception"] for p, v in current.items() if "exception" in v}
    assert c == g, f"exception drift:\n  golden={g}\n  now={c}"


def test_snapshot_is_deterministic(golden):
    """The normalisation must remove everything that varies run to run.

    Without this, a flaky golden file would be worse than none: it would
    train you to regenerate on every failure.
    """
    a = sweep_all(sorted(golden.keys()))
    b = sweep_all(sorted(golden.keys()))
    unstable = [p for p in a if a[p] != b[p]]
    assert not unstable, f"non-deterministic paths: {unstable[:10]}"


# --- the production payload shape -------------------------------------------
# The API is an HTTP API but pinned to payload_format_version "1.0"
# (terraform/api-gateway.tf:43), so live requests arrive in the v1 shape:
# `path` rather than `rawPath`, and a capitalised `Host`. The sweep above
# uses the v2 shape, which exercises the OTHER arm of the dispatcher's
# format check — so without these the live path would be unpinned.


@pytest.fixture(scope="module")
def golden_v1():
    with open(GOLDEN_V1_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def current_v1(golden_v1):
    return sweep_all(sorted(golden_v1.keys()), fmt="v1")


@pytest.mark.parametrize("field", ["status", "ct", "cache", "b64", "hdrs", "sha", "len"])
def test_v1_payload_matches_golden(golden_v1, current_v1, field):
    drift = {
        p: (golden_v1[p].get(field), current_v1[p].get(field))
        for p in golden_v1
        if golden_v1[p].get(field) != current_v1[p].get(field)
    }
    assert not drift, (
        f"{len(drift)} route(s) changed `{field}` under the production payload shape:\n"
        + "\n".join(f"  {p}: golden={g!r} now={n!r}" for p, (g, n) in sorted(drift.items())[:20])
    )


def test_both_payload_shapes_agree_except_event_debug(golden, golden_v1):
    """v1 and v2 must route identically.

    /event is the one legitimate exception: it renders the raw event, so its
    body necessarily differs between the two shapes.
    """
    differing = {p for p in golden if golden[p] != golden_v1.get(p)}
    assert differing <= {"/event", "/default/event"}, (
        f"payload shape changes routing for: {sorted(differing - {'/event', '/default/event'})[:20]}"
    )
