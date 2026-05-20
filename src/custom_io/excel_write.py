"""Helpers for writing typed values to Excel tables via xlwings.

Intended counterpart to `custom_io.excel_read`.

Convention:
- Columns are snake_case
- Direction/tensor components are uppercase suffixes: _X,_Y,_Z,_XX,_XY,...
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

import numpy as np
from xlwings.main import Table

from core.floats.types import Vector3, Vector3x3, Vector6


def _ensure_table_column(table: Table, column_name: str) -> int:
    """Ensure a ListObject table has a column and return its 1-based index."""

    api = table.api
    list_columns = api.ListColumns

    for i in range(1, list_columns.Count + 1):
        col = list_columns(i)
        if str(col.Name).strip() == column_name:
            return int(i)

    new_col = list_columns.Add()
    new_col.Name = column_name
    return int(new_col.Index)


def _values_Vector3(
    prefix: str,
    value: Vector3,
) -> dict[str, float]:
    x, y, z = (float(v) for v in value)
    return {
        f"{prefix}_X": x,
        f"{prefix}_Y": y,
        f"{prefix}_Z": z,
    }


def _values_Vector6(
    prefix: str,
    value: Vector6,
) -> dict[str, float]:
    # MAPDL sometimes returns (6, 1) or (1, 6); normalize to flat length-6.
    arr = np.asarray(value, dtype=float).reshape(-1)
    if arr.size != 6:
        raise ValueError(
            f"{prefix}: expected Vector6 with 6 elements, got shape {np.shape(value)!r}"
        )

    xx, yy, zz, yz, xz, xy = (float(v) for v in arr)
    # Convention: [XX, YY, ZZ, YZ, XZ, XY]
    return {
        f"{prefix}_XX": xx,
        f"{prefix}_YY": yy,
        f"{prefix}_ZZ": zz,
        f"{prefix}_YZ": yz,
        f"{prefix}_XZ": xz,
        f"{prefix}_XY": xy,
    }


def _values_Vector3x3(
    prefix: str,
    value: Vector3x3,
) -> dict[str, float]:
    r0, r1, r2 = value
    xx, xy, xz = (float(v) for v in r0)
    yx, yy, yz = (float(v) for v in r1)
    zx, zy, zz = (float(v) for v in r2)
    return {
        f"{prefix}_XX": xx,
        f"{prefix}_XY": xy,
        f"{prefix}_XZ": xz,
        f"{prefix}_YX": yx,
        f"{prefix}_YY": yy,
        f"{prefix}_YZ": yz,
        f"{prefix}_ZX": zx,
        f"{prefix}_ZY": zy,
        f"{prefix}_ZZ": zz,
    }


class WriteQueue:
    """Queue table writes and flush them in larger blocks.

    - Keyed by output table row_idx0 (0-based within data_body_range).
    - Only rows present in the queue are written during flush.
    """

    def __init__(self) -> None:
        self._rows: dict[int, dict[str, Any]] = {}

    def add_values(self, row_idx0: int, values: Mapping[str, Any]) -> None:
        row = self._rows.setdefault(int(row_idx0), {})
        row.update(values)

    def add_int(self, row_idx0: int, name: str, value: int) -> None:
        self.add_values(row_idx0, {str(name): int(value)})

    def add_str(self, row_idx0: int, name: str, value: str) -> None:
        self.add_values(row_idx0, {str(name): str(value)})

    def add_Vector3(self, row_idx0: int, prefix: str, value: Vector3) -> None:
        self.add_values(row_idx0, _values_Vector3(prefix, value))

    def add_Vector6(self, row_idx0: int, prefix: str, value: Vector6) -> None:
        self.add_values(row_idx0, _values_Vector6(prefix, value))

    def add_Vector3x3(self, row_idx0: int, prefix: str, value: Vector3x3) -> None:
        self.add_values(row_idx0, _values_Vector3x3(prefix, value))

    def flush(self, table: Table) -> None:
        if not self._rows:
            return

        # Ensure columns exist and map to 0-based indices.
        all_cols: list[str] = []
        seen: set[str] = set()
        for _, row in sorted(self._rows.items()):
            for c in row:
                if c not in seen:
                    seen.add(c)
                    all_cols.append(c)

        col_indices0 = {c: _ensure_table_column(table, c) - 1 for c in all_cols}

        body = table.data_body_range
        if body is None:
            return

        # Sort cols by index and partition into contiguous blocks.
        cols_sorted = sorted(col_indices0.items(), key=lambda t: t[1])  # (name, idx0)
        col_blocks: list[list[tuple[str, int]]] = []
        for name, idx0 in cols_sorted:
            if not col_blocks:
                col_blocks.append([(name, idx0)])
                continue
            if idx0 == col_blocks[-1][-1][1] + 1:
                col_blocks[-1].append((name, idx0))
            else:
                col_blocks.append([(name, idx0)])

        # Partition rows into contiguous blocks.
        row_idxs = sorted(self._rows.keys())
        row_blocks: list[tuple[int, int]] = []
        start = prev = row_idxs[0]
        for r in row_idxs[1:]:
            if r == prev + 1:
                prev = r
                continue
            row_blocks.append((start, prev))
            start = prev = r
        row_blocks.append((start, prev))

        writes: list[tuple[Any, list[list[Any]]]] = []

        # 1) First collect all write ranges and data.
        for r0, r1 in row_blocks:
            for block in col_blocks:
                names = [n for n, _ in block]
                c0 = block[0][1]
                c1 = block[-1][1]

                rng = body[r0 : r1 + 1, c0 : c1 + 1]

                data2d: list[list[Any]] = []
                for rr in range(r0, r1 + 1):
                    row = self._rows.get(rr, {})
                    data2d.append([row.get(n) for n in names])

                writes.append((rng, data2d))

        # 2) Then write to Excel after leaving the nested loop.
        for rng, data2d in writes:
            self._write_range_with_retry(rng, data2d)

        self._rows.clear()

    @staticmethod
    def _write_range_with_retry(rng: Any, data2d: list[list[Any]]) -> None:
        # Retry for transient Excel busy errors.
        for attempt in range(15):
            try:
                rng.value = data2d
                return
            except Exception as e:
                try:
                    import pywintypes

                    if isinstance(e, pywintypes.com_error):
                        hr = e.args[0] if e.args else None
                        excel_hr = None
                        if (
                            len(e.args) >= 3
                            and isinstance(e.args[2], tuple)
                            and len(e.args[2]) >= 6
                        ):
                            excel_hr = e.args[2][5]
                        if hr == -2147352567 and excel_hr in (-2146777998,):
                            time.sleep(0.1 * (attempt + 1))
                            continue
                except Exception:
                    pass
                raise
