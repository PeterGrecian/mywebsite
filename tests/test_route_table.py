"""Structural invariants of the route table.

The golden master proves the table behaves like the old if/elif chain *today*.
These tests protect the properties a future edit could quietly break, which a
response snapshot would not explain even when it caught them.
"""

import re

import pytest


@pytest.fixture(scope="module")
def mod():
    from golden_sweep import _build_module
    return _build_module()


# Exact routes that also match a pattern. In the original if/elif chain each of
# these appeared BEFORE its competing prefix, so exact won there too and
# exact-first preserves behaviour. A new entry appearing here means someone
# added an overlap whose ordering has not been checked against the old chain.
KNOWN_OVERLAPS = {
    ("/skycam/player", "_route_skycam_play"),
    ("/skycam/player-poc", "_route_skycam_play"),
    ("/starcam/player", "_route_starcam_play"),
}


def test_exact_beats_pattern_and_overlaps_are_known(mod):
    """Exact routes always win; the set that even competes is fixed."""
    overlaps = set()
    for key, exact_handler in mod._ROUTES_EXACT.items():
        for kind, matcher, handler in mod._ROUTES_PATTERN:
            hit = key.startswith(matcher) if kind is mod._PREFIX else bool(matcher(key))
            if hit:
                overlaps.add((key, handler.__name__))
                # the documented rule: the exact route is the one that answers
                assert mod._resolve_route(key) is exact_handler, (
                    f"{key} resolved to the pattern handler, not its exact one"
                )
    assert overlaps == KNOWN_OVERLAPS, (
        "route overlap set changed — check the new one against the old chain "
        f"order before updating this test.\n  new: {overlaps - KNOWN_OVERLAPS}"
        f"\n  gone: {KNOWN_OVERLAPS - overlaps}"
    )


def test_every_route_resolves_to_a_callable(mod):
    for key, handler in mod._ROUTES_EXACT.items():
        assert callable(handler), f"{key} maps to a non-callable"
    for kind, matcher, handler in mod._ROUTES_PATTERN:
        assert kind in (mod._PREFIX, mod._PRED)
        assert callable(handler)
        if kind is mod._PREFIX:
            assert matcher.startswith("/"), f"prefix {matcher!r} must start with /"


def test_unknown_route_resolves_to_none(mod):
    for path in ("/definitely-not-a-route", "/wp-login.php", "/cv/extra/segments"):
        assert mod._resolve_route(path) is None, f"{path} unexpectedly claimed"


def test_known_routes_resolve(mod):
    """Spot-check the precedence cases that motivated the two-structure design."""
    cases = {
        "/cv": "_route_cv",
        "/contents": "_route_contents",
        "/favicon.ico": "_route_favicon_ico",
        "/skycam/player": "_route_skycam_player",      # exact wins...
        "/skycam/play/anything": "_route_skycam_play",  # ...over the prefix
        "/starcam/player": "_route_starcam_player",
        "/starcam/play/x": "_route_starcam_play",
        "/gardencam/gallery/x": "_route_gardencam_gallery",
    }
    for path, expected in cases.items():
        handler = mod._resolve_route(path)
        assert handler is not None, f"{path} resolved to nothing"
        assert handler.__name__ == expected, f"{path} -> {handler.__name__}, want {expected}"


def test_handlers_return_dict_or_str(mod):
    """The two calling conventions the epilogue depends on."""
    import inspect
    names = {h.__name__ for h in mod._ROUTES_EXACT.values()}
    names |= {h.__name__ for _, _, h in mod._ROUTES_PATTERN}
    assert len(names) >= 70, f"only {len(names)} distinct handlers"
    for name in names:
        fn = getattr(mod, name)
        sig = inspect.signature(fn)
        assert list(sig.parameters) == ["rq"], f"{name}{sig} — handlers take rq only"
