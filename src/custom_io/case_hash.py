#case_hash.py
"""Module for case hash functionality in src.custom_io."""

from __future__ import annotations

from core.hashing import sha1_hex


def build_case_hash(key: str) -> str:
    """Build the stable hash used for case artifact and result folders.

    Parameters
    ----------
    key : str
        Canonical simulation case key.

    Returns
    -------
    str
        SHA-1 hexadecimal digest of ``key``.
    """

    return sha1_hex(key)
