"""Helpers for writing long-format t_out rows to an Excel table via xlwings."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from xlwings.main import Table




def write_long_rows(
    *,
    table: Table,
    rows: Iterable[Mapping[str, Any]],
    required_columns: Iterable[str],
) -> None:
    """Overwrite the table body with the given sequence of row dicts.

    Strict mode: all `required_columns` must already exist in the table header.
    No columns are auto-created.
    """

    row_list = list(rows)

    required = [str(c) for c in required_columns]

    header_range = table.header_row_range
    if header_range is None:
        raise ValueError("Output table has no header row")
    header = [str(v).strip() for v in header_range.options(ndim=1).value]
    header_idx0 = {name: i for i, name in enumerate(header)}

    missing = [c for c in required if c not in header_idx0]
    if missing:
        raise KeyError("t_out is missing required column(s): " + ", ".join(missing))

    # Only write required columns (stable order)
    all_cols = required
    col_indices0 = {c: header_idx0[c] for c in all_cols}

    # Ensure row count.
    api = table.api
    list_rows = api.ListRows
    n_rows = len(row_list)
    while list_rows.Count > n_rows:
        list_rows(list_rows.Count).Delete()
    while list_rows.Count < n_rows:
        list_rows.Add()

    body = table.data_body_range
    if body is None:
        return
    if n_rows == 0:
        return

    # Write potentially non-contiguous columns as individual blocks.
    cols_sorted = sorted(col_indices0.items(), key=lambda t: t[1])  # (name, idx0)

    # Partition into contiguous blocks
    blocks: list[list[tuple[str, int]]] = []
    for name, idx0 in cols_sorted:
        if not blocks or idx0 != blocks[-1][-1][1] + 1:
            blocks.append([(name, idx0)])
        else:
            blocks[-1].append((name, idx0))

    for block in blocks:
        names = [n for n, _ in block]
        c0 = block[0][1]
        c1 = block[-1][1]
        rng = body[0:n_rows, c0 : c1 + 1]
        data2d: list[list[Any]] = []
        for r in row_list:
            data2d.append([r.get(n) for n in names])
        rng.value = data2d
