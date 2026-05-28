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


def _contiguous_blocks(columns: list[str], header_idx0: dict[str, int]) -> list[list[tuple[str, int]]]:
    pairs = sorted(((c, header_idx0[c]) for c in columns), key=lambda t: t[1])
    blocks: list[list[tuple[str, int]]] = []
    for name, idx0 in pairs:
        if not blocks or idx0 != blocks[-1][-1][1] + 1:
            blocks.append([(name, idx0)])
        else:
            blocks[-1].append((name, idx0))
    return blocks


def _read_existing_required_rows(
    *,
    table: Table,
    required: list[str],
    header_idx0: dict[str, int],
) -> list[dict[str, Any]]:
    body = table.data_body_range
    if body is None or body.rows.count <= 0:
        return []

    n_existing = body.rows.count
    existing = [dict() for _ in range(n_existing)]

    for block in _contiguous_blocks(required, header_idx0):
        names = [n for n, _ in block]
        c0 = block[0][1]
        c1 = block[-1][1]
        data = body[0:n_existing, c0 : c1 + 1].options(ndim=2).value
        if data is None:
            continue
        for r_i, row_vals in enumerate(data):
            for n, v in zip(names, row_vals):
                existing[r_i][n] = v

    return existing


def _write_row_to_range(
    *,
    row_range,
    row_dict: Mapping[str, Any],
    columns: list[str],
    header_idx0: dict[str, int],
) -> None:
    for block in _contiguous_blocks(columns, header_idx0):
        names = [n for n, _ in block]
        c0 = block[0][1]
        c1 = block[-1][1]
        row_range[0, c0 : c1 + 1].value = [[row_dict.get(n) for n in names]]


def _add_table_row(table: Table):
    """Append one row to a ListObject and return the new row range.

    Use AlwaysInsert=True so Excel shifts any below content down instead of
    requiring a pre-empty row under the table. This avoids fragile ListObject
    Resize calls.
    """

    try:
        list_row = table.api.ListRows.Add(AlwaysInsert=True)
    except TypeError:
        # Some COM wrappers don't expose keyword arguments reliably.
        list_row = table.api.ListRows.Add(None, True)
    return list_row.Range


def upsert_long_rows(
    *,
    table: Table,
    rows: Iterable[Mapping[str, Any]],
    required_columns: Iterable[str],
    key_columns: tuple[str, ...] = ("index", "hash", "category", "row", "col"),
) -> None:
    """Upsert rows into a long-format t_out table.

    For each incoming row, we search for an existing row with the same key
    (index, hash, category, row, col). If found, we overwrite that row in place.
    Otherwise, we append exactly one new ListObject row with
    ``ListRows.Add(AlwaysInsert=True)`` and write the row values.

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

    existing = _read_existing_required_rows(table=table, required=required, header_idx0=header_idx0)

    def key_of(d: Mapping[str, Any]) -> tuple[Any, ...]:
        return tuple(d.get(k) for k in key_columns)

    index_map: dict[tuple[Any, ...], int] = {}
    for i, d in enumerate(existing):
        index_map[key_of(d)] = i

    n_rows_current = len(existing)

    for d in incoming:
        k = key_of(d)
        hit = index_map.get(k)
        row_values = {c: d.get(c) for c in required}

        if hit is not None:
            body = table.data_body_range
            if body is None:
                # Should not happen if we had an existing hit, but be defensive.
                row_range = _add_table_row(table)
                index_map[k] = n_rows_current
                n_rows_current += 1
            else:
                row_range = body[hit, :]
            _write_row_to_range(row_range=row_range, row_dict=row_values, columns=required, header_idx0=header_idx0)
            continue

        row_range = _add_table_row(table)
        _write_row_to_range(row_range=row_range, row_dict=row_values, columns=required, header_idx0=header_idx0)
        index_map[k] = n_rows_current
        n_rows_current += 1
