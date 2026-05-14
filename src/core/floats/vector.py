# vector.py

"""Backwards-compatible re-exports for vector/matrix type aliases."""

from __future__ import annotations

from core.floats.types import (
    OutputNumericValue,
    Vector3,
    Vector3Int,
    Vector6,
    Vector3x3,
)

__all__ = [
    "Vector3",
    "Vector3Int",
    "Vector6",
    "Vector3x3",
    "OutputNumericValue",
]
