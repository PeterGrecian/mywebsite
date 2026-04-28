"""Deterministic GitHub-style pet names from commit hashes.

Same hash → same "<adjective>-<noun>" name forever, so a glance at the
page tells you which build you're seeing without memorising hex.
"""
import hashlib
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    path = os.path.join(_HERE, name)
    with open(path) as f:
        return [w.strip() for w in f if w.strip()]


_ADJ = _load("adjectives.txt")
_NOUN = _load("nouns.txt")


def pet_name(commit_hash):
    """Map a commit hash (or any string) to '<adjective>-<noun>'.

    Uses sha1 of the input so short prefixes still spread across the
    word lists. Same input → same output.
    """
    if not commit_hash:
        return "unknown-build"
    digest = hashlib.sha1(commit_hash.encode("utf-8")).digest()
    a = int.from_bytes(digest[:4], "big") % len(_ADJ)
    n = int.from_bytes(digest[4:8], "big") % len(_NOUN)
    return f"{_ADJ[a]}-{_NOUN[n]}"
