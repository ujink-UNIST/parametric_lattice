"""Helpers for writing long-format t_out rows to an Excel table via xlwings."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from xlwings.main import Table

from custom_io.excel_write import _ensure_table_column


def write_long_rows(
    *,
    table: Table,
    rows: Iterable[Mapping[str, Any]],
) -> None:
    """Overwrite the table body with the given sequence of row dicts.

    - Ensures all keys exist as table columns.
    - Resizes the table to exactly len(rows) body rows.
    - Writes values in a single 2D block per contiguous column range.

    This is intended for the new long-format t_out.
    """

    row_list = list(rows)

    # Ensure columns exist (and record 0-based indices).
    all_cols: list[str] = []
    seen: set[str] = set()
    for r in row_list:
        for c in r.keys():
            c = str(c)
            if c not in seen:
                seen.add(c)
                all_cols.append(c)

    col_indices0 = {c: _ensure_table_column(table, c) - 1 for c in all_cols}

    # Ensure row count.
    api = table.api
    list_rows = api.ListRows
    n_rows = len(row_list)
    while list_rows.Count > n_rows:
        list_rows(list_rows.Count).Delete()
    while list_rows.Count < n_rows:
        list_rows.Add()

    body = table.data_body_range
    if body is None or n_rows == 0 or not all_cols:
        return

    # Sort columns by index and write one block.
    cols_sorted = sorted(col_indices0.items(), key=lambda t: t[1])
    names = [n for n, _ in cols_sorted]
    c0 = cols_sorted[0][1]
    c1 = cols_sorted[-1][1]

    rng = body[0:n_rows, c0 : c1 + 1]
    data2d: list[list[Any]] = []
    for r in row_list:
        data2d.append([r.get(n) for n in names])

    rng.value = data2d
