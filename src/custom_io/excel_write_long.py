"""Helpers for writing long-format t_out rows to an Excel table via xlwings."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from xlwings.main import Table




def _require_columns(table: Table, required_columns: Iterable[str]) -> tuple[list[str], dict[str, int]]:
    required = [str(c) for c in required_columns]

    header_range = table.header_row_range
    if header_range is None:
        raise ValueError("Output table has no header row")
    header = [str(v).strip() for v in header_range.options(ndim=1).value]
    header_idx0 = {name: i for i, name in enumerate(header)}

    missing = [c for c in required if c not in header_idx0]
    if missing:
        raise KeyError("t_out is missing required column(s): " + ", ".join(missing))

    return required, header_idx0


def _write_rows_to_table(
    *,
    table: Table,
    row_dicts: list[Mapping[str, Any]],
    columns: list[str],
    header_idx0: dict[str, int],
) -> None:
    # Ensure row count. Prefer resizing the ListObject in one operation over
    # repeated ListRows.Add/Delete calls; Excel COM can fail to add rows one by
    # one when filters are active or when the table is near other content.
    n_rows = len(row_dicts)
    if n_rows == 0:
        body = table.data_body_range
        if body is not None:
            table.api.Resize(table.header_row_range.api.Resize(1, table.range.columns.count))
        return

    table.api.Resize(table.header_row_range.api.Resize(n_rows + 1, table.range.columns.count))

    body = table.data_body_range
    if body is None:
        return

    col_indices0 = {c: header_idx0[c] for c in columns}
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
        for r in row_dicts:
            data2d.append([r.get(n) for n in names])
        rng.value = data2d


def upsert_long_rows(
    *,
    table: Table,
    rows: Iterable[Mapping[str, Any]],
    required_columns: Iterable[str],
    key_columns: tuple[str, ...] = ("index", "hash", "category", "row", "col"),
) -> None:
    """Upsert rows into a long-format t_out table.

    For each incoming row, we search for an existing row with the same key
    (index, hash, category, row, col). If found, we overwrite the values.
    Otherwise, we append a new row.

    Strict mode:
      - `required_columns` must exist in the table header (no auto-create).
      - `key_columns` must be a subset of `required_columns`.
    """

    incoming = list(rows)
    if not incoming:
        return

    required, header_idx0 = _require_columns(table, required_columns)

    for k in key_columns:
        if k not in required:
            raise ValueError(f"key column {k!r} must be included in required_columns")

    body = table.data_body_range
    existing_dicts: list[dict[str, Any]] = []
    if body is not None and body.rows.count > 0:
        # Read only required columns.
        cols_idx0 = [header_idx0[c] for c in required]
        # Group into contiguous blocks for reading.
        sorted_pairs = sorted(zip(required, cols_idx0), key=lambda t: t[1])
        blocks: list[list[tuple[str, int]]] = []
        for name, idx0 in sorted_pairs:
            if not blocks or idx0 != blocks[-1][-1][1] + 1:
                blocks.append([(name, idx0)])
            else:
                blocks[-1].append((name, idx0))

        # Initialize with empty dicts
        n_existing = body.rows.count
        existing_dicts = [dict() for _ in range(n_existing)]
        for block in blocks:
            names = [n for n, _ in block]
            c0 = block[0][1]
            c1 = block[-1][1]
            data = body[0:n_existing, c0 : c1 + 1].options(ndim=2).value
            if data is None:
                continue
            for r_i, row_vals in enumerate(data):
                for n, v in zip(names, row_vals):
                    existing_dicts[r_i][n] = v

    def key_of(d: Mapping[str, Any]) -> tuple[Any, ...]:
        return tuple(d.get(k) for k in key_columns)

    index_map: dict[tuple[Any, ...], int] = {}
    for i, d in enumerate(existing_dicts):
        index_map[key_of(d)] = i

    # Apply upserts
    for d in incoming:
        k = key_of(d)
        hit = index_map.get(k)
        if hit is None:
            existing_dicts.append({c: d.get(c) for c in required})
            index_map[k] = len(existing_dicts) - 1
        else:
            # Overwrite required columns
            for c in required:
                if c in d:
                    existing_dicts[hit][c] = d.get(c)

    _write_rows_to_table(table=table, row_dicts=existing_dicts, columns=required, header_idx0=header_idx0)
