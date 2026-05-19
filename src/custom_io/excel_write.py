"""Helpers for writing typed values to Excel tables via xlwings.

Intended counterpart to `custom_io.excel_read`.

Convention:
- Columns are snake_case
- Direction/tensor components are uppercase suffixes: _X,_Y,_Z,_XX,_XY,...
"""

from __future__ import annotations

from typing import Any, Mapping

import time

import numpy as np
import xlwings as xw
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


def _ensure_table_rows(table: Table, n_rows: int) -> None:
    """Ensure a ListObject table has exactly n_rows body rows."""

    api = table.api
    list_rows = api.ListRows

    while list_rows.Count > n_rows:
        list_rows(list_rows.Count).Delete()

    while list_rows.Count < n_rows:
        list_rows.Add()


def _set_cell_value(table: Table, row_idx: int, col_idx: int, value: Any) -> None:
    """Set a single Excel cell value with a small retry for transient COM errors."""

    # Excel sometimes returns 0x800AC472 (application busy) when it's updating.
    # Retrying makes Excel integration much more robust.
    for attempt in range(15):
        try:
            body = table.data_body_range
            if body is None:
                raise RuntimeError("Excel table has no data body range")
            body[row_idx, col_idx].value = value
            return
        except Exception as e:
            # Only retry for known COM error codes.
            try:
                import pywintypes

                if isinstance(e, pywintypes.com_error):
                    # e.args[0] is the HRESULT; e.args[2] may contain the Excel error.
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

    # If we somehow exhausted retries without raising, raise a generic error.
    raise RuntimeError("Failed to write to Excel after retries")


'''
def write_value(
    table: Table,
    row_idx0: int,
    key: str,
    value: Any,
    *,
    ensure_rows: int | None = None,
) -> None:
    """Write a single value into a table row.

    Args:
        table: xlwings Table (Excel ListObject)
        row_idx0: 0-based row index within the table body
        key: column header (snake_case)
        value: value to write
        ensure_rows: if given, first resize table body to exactly this many rows
    """

    if ensure_rows is not None:
        _ensure_table_rows(table, ensure_rows)

    col_idx1 = _ensure_table_column(table, key)

    body = table.data_body_range
    if body is None:
        return

    _set_cell_value(table, row_idx0, col_idx1 - 1, value)
'''


def write_row(
    table: Table,
    row_idx0: int,
    values: Mapping[str, Any],
    *,
    ensure_rows: int | None = None,
) -> None:
    """Write multiple (key,value) pairs into a single table row."""

    if ensure_rows is not None:
        _ensure_table_rows(table, ensure_rows)

    body = table.data_body_range
    if body is None:
        return

    # Ensure all columns first (mutates table), then refresh body.
    col_indices1 = {k: _ensure_table_column(table, k) for k in values.keys()}

    body = table.data_body_range
    if body is None:
        return

    for k, v in values.items():
        _set_cell_value(table, row_idx0, col_indices1[k] - 1, v)


def write_float(
    table: Table,
    row_idx0: int,
    key: str,
    value: float,
    *,
    ensure_rows: int | None = None,
) -> None:
    # Use write_row so callers can batch multiple scalars in one row write.
    write_row(
        table,
        row_idx0,
        {key: float(value)},
        ensure_rows=ensure_rows,
    )


def write_int(
    table: Table,
    row_idx0: int,
    key: str,
    value: int,
    *,
    ensure_rows: int | None = None,
) -> None:
    # Use write_row so callers can batch multiple scalars in one row write.
    write_row(
        table,
        row_idx0,
        {key: int(value)},
        ensure_rows=ensure_rows,
    )


def write_str(
    table: Table,
    row_idx0: int,
    key: str,
    value: str,
    *,
    ensure_rows: int | None = None,
) -> None:
    # Use write_row so callers can batch multiple scalars in one row write.
    write_row(
        table,
        row_idx0,
        {key: str(value)},
        ensure_rows=ensure_rows,
    )


def write_Vector3(
    table: Table,
    row_idx0: int,
    prefix: str,
    value: Vector3,
    *,
    ensure_rows: int | None = None,
) -> None:
    v = np.asarray(value, dtype=float).reshape(3)
    write_row(
        table,
        row_idx0,
        {
            f"{prefix}_X": float(v[0]),
            f"{prefix}_Y": float(v[1]),
            f"{prefix}_Z": float(v[2]),
        },
        ensure_rows=ensure_rows,
    )


def write_Vector6(
    table: Table,
    row_idx0: int,
    prefix: str,
    value: Vector6,
    *,
    ensure_rows: int | None = None,
) -> None:
    v = np.asarray(value, dtype=float).reshape(6)
    # Convention: [XX, YY, ZZ, YZ, XZ, XY]
    write_row(
        table,
        row_idx0,
        {
            f"{prefix}_XX": float(v[0]),
            f"{prefix}_YY": float(v[1]),
            f"{prefix}_ZZ": float(v[2]),
            f"{prefix}_YZ": float(v[3]),
            f"{prefix}_XZ": float(v[4]),
            f"{prefix}_XY": float(v[5]),
        },
        ensure_rows=ensure_rows,
    )


def _values_Vector3(
    prefix: str,
    value: Vector3,
) -> dict[str, float]:
    v = np.asarray(value, dtype=float).reshape(3)
    return {
        f"{prefix}_X": float(v[0]),
        f"{prefix}_Y": float(v[1]),
        f"{prefix}_Z": float(v[2]),
    }


def _values_Vector6(
    prefix: str,
    value: Vector6,
) -> dict[str, float]:
    v = np.asarray(value, dtype=float).reshape(6)
    # Convention: [XX, YY, ZZ, YZ, XZ, XY]
    return {
        f"{prefix}_XX": float(v[0]),
        f"{prefix}_YY": float(v[1]),
        f"{prefix}_ZZ": float(v[2]),
        f"{prefix}_YZ": float(v[3]),
        f"{prefix}_XZ": float(v[4]),
        f"{prefix}_XY": float(v[5]),
    }


def _values_Vector3x3(
    prefix: str,
    value: Vector3x3,
) -> dict[str, float]:
    m = np.asarray(value, dtype=float).reshape(3, 3)
    return {
        f"{prefix}_XX": float(m[0, 0]),
        f"{prefix}_XY": float(m[0, 1]),
        f"{prefix}_XZ": float(m[0, 2]),
        f"{prefix}_YX": float(m[1, 0]),
        f"{prefix}_YY": float(m[1, 1]),
        f"{prefix}_YZ": float(m[1, 2]),
        f"{prefix}_ZX": float(m[2, 0]),
        f"{prefix}_ZY": float(m[2, 1]),
        f"{prefix}_ZZ": float(m[2, 2]),
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
            for c in row.keys():
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

        # Write blocks.
        for r0, r1 in row_blocks:
            n_rows = r1 - r0 + 1
            for block in col_blocks:
                names = [n for n, _ in block]
                c0 = block[0][1]
                c1 = block[-1][1]
                rng = body[r0 : r1 + 1, c0 : c1 + 1]

                data2d: list[list[Any]] = []
                for rr in range(r0, r1 + 1):
                    row = self._rows.get(rr, {})
                    data2d.append([row.get(n) for n in names])

                # Retry for transient Excel busy errors.
                for attempt in range(15):
                    try:
                        rng.value = data2d
                        break
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


def write_Vector3x3(
    table: Table,
    row_idx0: int,
    prefix: str,
    value: Vector3x3,
    *,
    ensure_rows: int | None = None,
) -> None:
    m = np.asarray(value, dtype=float).reshape(3, 3)
    write_row(
        table,
        row_idx0,
        {
            f"{prefix}_XX": float(m[0, 0]),
            f"{prefix}_XY": float(m[0, 1]),
            f"{prefix}_XZ": float(m[0, 2]),
            f"{prefix}_YX": float(m[1, 0]),
            f"{prefix}_YY": float(m[1, 1]),
            f"{prefix}_YZ": float(m[1, 2]),
            f"{prefix}_ZX": float(m[2, 0]),
            f"{prefix}_ZY": float(m[2, 1]),
            f"{prefix}_ZZ": float(m[2, 2]),
        },
        ensure_rows=ensure_rows,
    )
