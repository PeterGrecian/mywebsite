#!/usr/bin/env python3
"""Regenerate both golden snapshots — and print what changed.

Never regenerate to make a failing test pass without reading the diff: the
whole point of the snapshot is that an unexplained change is a bug.

Both shapes are rewritten. The API is an HTTP API pinned to
payload_format_version = "1.0", so production sends v1 (`path`, capitalised
`Host`) while the v2 sweep builds `rawPath`; `test_dispatch_golden.py` pins
each separately. Regenerating only v2 leaves the v1 file stale and the suite
red for a reason that looks unrelated to the change being made.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from golden_sweep import sweep_all, GOLDEN_PATH  # noqa: E402

GOLDEN_V1_PATH = GOLDEN_PATH.replace("golden_routes.json", "golden_routes_v1.json")


def regen(path, fmt):
    old = {}
    if os.path.exists(path):
        with open(path) as f:
            old = json.load(f)

    paths = sorted(old.keys())
    if not paths:
        sys.exit(f"no existing golden file at {path}: seed one first")

    new = sweep_all(paths, fmt=fmt)
    changed = [p for p in new if old.get(p) != new[p]]
    for p in changed:
        print(f"CHANGED [{fmt}] {p}\n   was {old.get(p)}\n   now {new[p]}")
    print(f"\n{len(changed)} of {len(new)} routes changed ({fmt})")

    with open(path, "w") as f:
        json.dump(new, f, indent=1, sort_keys=True)
    print(f"wrote {path}\n")


regen(GOLDEN_PATH, "v2")
regen(GOLDEN_V1_PATH, "v1")
