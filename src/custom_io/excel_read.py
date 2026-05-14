"""Helpers for reading typed values from Excel table rows.

These functions operate on a row mapping produced by
`custom_io.excel_io._map_header_to_row_values`.

Convention:
- Columns are snake_case
- Direction/tensor components are uppercase suffixes: _X,_Y,_Z,_XX,_XY,...
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from core.floats.types import Vector3, Vector3x3, Vector6


def read_required(row: Dict[str, Any], key: str) -> Any:
    if key not in row:
        raise KeyError(
            f"Missing Excel column {key!r}. Available: {sorted(row.keys())}"
        )
    v = row[key]
    if v is None or (isinstance(v, str) and not v.strip()):
        raise ValueError(f"Excel cell for {key!r} is empty")
    return v


def read_optional(row: Dict[str, Any], key: str) -> Any | None:
    if key not in row:
        return None
    v = row[key]
    if v is None:
        return None
    if isinstance(v, str) and not v.strip():
        return None
    return v


def read_str(row: Dict[str, Any], key: str) -> str:
    return str(read_required(row, key)).strip()


def read_float(row: Dict[str, Any], key: str) -> float:
    v = read_required(row, key)
    try:
        return float(v)
    except Exception as e:
        raise ValueError(f"Excel value for {key!r} is not a float: {v!r}") from e


def read_optional_float(row: Dict[str, Any], key: str) -> float | None:
    v = read_optional(row, key)
    if v is None:
        return None
    try:
        return float(v)
    except Exception as e:
        raise ValueError(f"Excel value for {key!r} is not a float: {v!r}") from e


def read_int(row: Dict[str, Any], key: str) -> int:
    v = read_required(row, key)
    try:
        # Excel often provides numbers as floats.
        return int(v)
    except Exception as e:
        raise ValueError(f"Excel value for {key!r} is not an int: {v!r}") from e


def read_Vector3(row: Dict[str, Any], prefix: str) -> Vector3:
    return np.array(
        [
            read_float(row, f"{prefix}_X"),
            read_float(row, f"{prefix}_Y"),
            read_float(row, f"{prefix}_Z"),
        ],
        dtype=float,
    )


def read_Vector6(row: Dict[str, Any], prefix: str) -> Vector6:
    return np.array(
        [
            read_float(row, f"{prefix}_XX"),
            read_float(row, f"{prefix}_YY"),
            read_float(row, f"{prefix}_ZZ"),
            read_float(row, f"{prefix}_YZ"),
            read_float(row, f"{prefix}_XZ"),
            read_float(row, f"{prefix}_XY"),
        ],
        dtype=float,
    )


def read_Vector3x3(row: Dict[str, Any], prefix: str) -> Vector3x3:
    return np.array(
        [
            read_float(row, f"{prefix}_XX"),
            read_float(row, f"{prefix}_XY"),
            read_float(row, f"{prefix}_XZ"),
            read_float(row, f"{prefix}_YX"),
            read_float(row, f"{prefix}_YY"),
            read_float(row, f"{prefix}_YZ"),
            read_float(row, f"{prefix}_ZX"),
            read_float(row, f"{prefix}_ZY"),
            read_float(row, f"{prefix}_ZZ"),
        ],
        dtype=float,
    )
