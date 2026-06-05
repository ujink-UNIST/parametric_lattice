#hashing.py
"""Hash utilities.

This module centralizes all stable hashing used for artifact keys (case hashes,
geometry hashes, mesh hashes, etc.).

Convention:
- We use SHA-1 for stable, short-ish hex identifiers suitable for folder names.
- Inputs must be *stable strings* (callers are responsible for deterministic
  serialization via `.to_string()` or equivalent).
"""

from __future__ import annotations

import hashlib


def sha1_hex(text: str) -> str:
    """Return SHA-1 hex digest for a string (utf-8)."""

    return hashlib.sha1(text.encode("utf-8")).hexdigest()


__all__ = [
    "sha1_hex",
]
