#write_long.py
"""Helpers for writing long-format t_out rows to an Excel table via xlwings."""

from __future__ import annotations

import time
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
    # Always get the current DataBodyRange immediately before reading.
    # Avoid xlwings slice syntax here: ListObject ranges can become stale or
    # produce invalid COM Range calls after previous table row additions.
    body = table.data_body_range
    if body is None or body.rows.count <= 0:
        return []

    n_existing = int(body.rows.count)
    existing = [dict() for _ in range(n_existing)]

    sheet = body.sheet
    abs_r0 = int(body.row)
    abs_r1 = abs_r0 + n_existing - 1
    body_first_col = int(body.column)

    for block in _contiguous_blocks(required, header_idx0):
        names = [n for n, _ in block]
        c0 = block[0][1]
        c1 = block[-1][1]
        abs_c0 = body_first_col + c0
        abs_c1 = body_first_col + c1

        data = None
        last_error: Exception | None = None
        for attempt in range(5):
            try:
                data = sheet.range((abs_r0, abs_c0), (abs_r1, abs_c1)).options(ndim=2).value
                last_error = None
                break
            except Exception as e:  # noqa: BLE001 - preserve Excel COM context
                last_error = e
                time.sleep(0.1 * (attempt + 1))
        if last_error is not None:
            raise RuntimeError(
                "Failed to read existing t_out rows: "
                f"sheet={getattr(sheet, 'name', '<unknown>')}, "
                f"r0={abs_r0}, r1={abs_r1}, c0={abs_c0}, c1={abs_c1}"
            ) from last_error

        if data is None:
            continue
        for r_i, row_vals in enumerate(data):
            for n, v in zip(names, row_vals):
                existing[r_i][n] = v

    return existing


def _write_row_at(sheet, abs_row: int, abs_c0: int, values: list[Any]) -> None:
    """Write a contiguous row block with explicit range validation.

    Reacquire the worksheet by name before each write attempt. Excel COM/xlwings
    sheet/range objects can become stale after ListObject row additions.
    """

    if not values:
        return

    abs_row = int(abs_row)
    abs_c0 = int(abs_c0)
    abs_c1 = abs_c0 + len(values) - 1

    if abs_row < 1 or abs_c0 < 1 or abs_c1 < abs_c0:
        raise ValueError(
            f"Invalid Excel range: row={abs_row}, c0={abs_c0}, c1={abs_c1}, len={len(values)}"
        )

    try:
        book = sheet.book
        sheet_name = str(sheet.name)
    except Exception:
        book = None
        sheet_name = ""

    last_error: Exception | None = None
    for attempt in range(5):
        try:
            target_sheet = book.sheets[sheet_name] if book is not None and sheet_name else sheet
            target_sheet.range((abs_row, abs_c0), (abs_row, abs_c1)).value = [values]
            return
        except Exception as e:  # noqa: BLE001 - preserve Excel COM context
            last_error = e
            time.sleep(0.1 * (attempt + 1))

    raise RuntimeError(
        "Failed to write t_out row block: "
        f"sheet={sheet_name or '<unknown>'}, row={abs_row}, c0={abs_c0}, c1={abs_c1}, "
        f"len={len(values)}"
    ) from last_error


def _write_table_row_at(
    *,
    table: Table,
    row_index0: int,
    row_dict: Mapping[str, Any],
    columns: list[str],
    header_idx0: dict[str, int],
) -> None:
    """Write one logical table row using freshly acquired absolute ranges.

    Excel/xlwings Range objects can become stale immediately after ListObject
    structural changes. Therefore this function reacquires `table.data_body_range`
    and writes via absolute sheet coordinates each time instead of reusing a
    previously sliced row Range.
    """

    body = table.data_body_range
    if body is None or body.rows.count <= row_index0:
        raise RuntimeError(f"t_out row {row_index0} is not available for writing")

    sheet = body.sheet
    abs_row = int(body.row) + int(row_index0)
    body_first_col = int(body.column)

    for block in _contiguous_blocks(columns, header_idx0):
        names = [n for n, _ in block]
        c0 = block[0][1]
        values = [row_dict.get(n) for n in names]
        abs_c0 = body_first_col + c0
        _write_row_at(sheet, abs_row, abs_c0, values)


def _add_table_row(table: Table, *, retries: int = 5) -> int:
    """Append one row and return its 0-based DataBodyRange row index.

    Use AlwaysInsert=True so Excel shifts any below content down instead of
    requiring a pre-empty row under the table. After each structural change, the
    caller must reacquire table ranges before writing.
    """

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            table.api.ListRows.Add(AlwaysInsert=True)
        except TypeError:
            # Some COM wrappers don't expose keyword arguments reliably.
            try:
                table.api.ListRows.Add(None, True)
            except Exception as e:  # noqa: BLE001 - preserve COM error context
                last_error = e
            else:
                last_error = None
        except Exception as e:  # noqa: BLE001 - preserve COM error context
            last_error = e
        else:
            last_error = None

        if last_error is None:
            # Reacquire DataBodyRange after the table structure changed.
            body = table.data_body_range
            if body is not None and body.rows.count > 0:
                return int(body.rows.count) - 1
            last_error = RuntimeError("ListRows.Add succeeded but DataBodyRange is empty")

        time.sleep(0.1 * (attempt + 1))

    assert last_error is not None
    raise last_error


def upsert_long_rows(
    *,
    table: Table,
    rows: Iterable[Mapping[str, Any]],
    required_columns: Iterable[str],
    key_columns: tuple[str, ...] = ("hash", "category", "row", "col"),
) -> None:
    """Upsert rows into a long-format t_out table.

    For each incoming row, we search for an existing row with the same key
    (hash, category, row, col). If found, we overwrite that row in place.
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

    for d in incoming:
        k = key_of(d)
        row_values = {c: d.get(c) for c in required}

        row_index0 = index_map.get(k)
        if row_index0 is None:
            row_index0 = _add_table_row(table)
            index_map[k] = row_index0

        _write_table_row_at(
            table=table,
            row_index0=int(row_index0),
            row_dict=row_values,
            columns=required,
            header_idx0=header_idx0,
        )
