#!/usr/bin/env python3
"""Regenerate tests/golden_routes.json — and print what changed.

Never regenerate to make a failing test pass without reading the diff: the
whole point of the snapshot is that an unexplained change is a bug.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from golden_sweep import sweep_all, GOLDEN_PATH  # noqa: E402

old = {}
if os.path.exists(GOLDEN_PATH):
    with open(GOLDEN_PATH) as f:
        old = json.load(f)

paths = sorted(old.keys()) if old else []
if not paths:
    sys.exit("no existing golden file: pass a path list to seed one")

new = sweep_all(paths)
changed = [p for p in new if old.get(p) != new[p]]
for p in changed:
    print(f"CHANGED {p}\n   was {old.get(p)}\n   now {new[p]}")
print(f"\n{len(changed)} of {len(new)} routes changed")

with open(GOLDEN_PATH, "w") as f:
    json.dump(new, f, indent=1, sort_keys=True)
print(f"wrote {GOLDEN_PATH}")
