from __future__ import annotations

"""Sync/upgrade post_cache.json into Excel t_out.

This macro reads per-case JSON caches and upserts their contents into the
`t_out` table, resolving units at runtime.

It is intended to be called from an Excel button via excel_integration actions.
"""

from contextlib import suppress
from pathlib import Path
from typing import Any

import xlwings as xw  # type: ignore[import-not-found]
from xlwings.main import Table  # type: ignore[import-not-found]

from custom_io.excel_io import (
    _apply_path_config_from_book,
    build_case_hash,
    find_table,
    get_table_data,
    _INPUT_TABLE,
    _OUTPUT_TABLE,
    _set_status_done,
    _set_status_fail,
    _set_status_pending,
    _set_status_running,
    _status_range_for_input_row,
)
from custom_io.excel_write_long import upsert_long_rows
from custom_io.ui_heartbeat import UIHeartbeat
from post.post_cache import cache_path_for_case, load_post_cache_lenient, parse_key, save_post_cache
from post.row import T_OUT_COLUMNS
from post.sim_case_meta import META_COLUMNS, sim_case_meta
from post.unit_resolver import unit_for_category
from core.parameters.sim_case import SimCase


def _get_simulation_cases(input_header, input_body) -> tuple[SimCase, ...]:
    # Import locally to avoid circular imports with excel_io
    from custom_io.excel_io import _get_simulation_cases as _g

    return _g(input_header, input_body)


def sync_post_cache_to_t_out(book: xw.Book) -> None:
    """Sync all cases' post_cache.json into the Excel t_out table."""

    _apply_path_config_from_book(book)

    hb = UIHeartbeat(book)

    input_table: Table = find_table(book, _INPUT_TABLE)
    input_header, input_body = get_table_data(input_table)
    inputs: tuple[SimCase, ...] = _get_simulation_cases(input_header, input_body)

    output_table: Table = find_table(book, _OUTPUT_TABLE)

    from custom_io.path_config import get_path_config

    cfg = get_path_config()
    artifacts_case_root: Path = cfg.artifacts_root / "case"

    try:
        for sim_case in inputs:
            _set_status_pending(book, _status_range_for_input_row(book, int(sim_case.row_idx)))
            hb.tick()

        for sim_case in inputs:
            status_cell = _status_range_for_input_row(book, int(sim_case.row_idx))
            _set_status_running(book, status_cell)
            hb.tick()

            case_hash = build_case_hash(sim_case.to_string())
            p = cache_path_for_case(artifacts_case_dir=artifacts_case_root, case_hash=case_hash)
            cache = load_post_cache_lenient(p, case_hash=case_hash)

            meta = sim_case_meta(sim_case)
            cache.sim_case_meta = meta

            case_index = int(sim_case.row_idx) + 1
            sync_rows: list[dict[str, Any]] = []
            for k, v in cache.rows.items():
                with suppress(Exception):
                    cat, r_i, c_i = parse_key(k)
                    d = {
                        "index": case_index,
                        "hash": case_hash,
                        "category": str(cat),
                        "row": int(r_i),
                        "col": int(c_i),
                        "value": float(v),
                        "unit": unit_for_category(str(cat)),
                    }
                    d.update(meta)
                    sync_rows.append(d)

            # Upsert to Excel
            if sync_rows:
                upsert_long_rows(
                    table=output_table,
                    rows=sync_rows,
                    required_columns=T_OUT_COLUMNS + META_COLUMNS,
                )
                hb.tick(force=True)

            # Save upgraded cache (rewrite)
            save_post_cache(p, cache)

            _set_status_done(book, status_cell)
            hb.tick()

    except Exception:
        # Best-effort mark all as fail
        for sim_case in inputs:
            _set_status_fail(book, _status_range_for_input_row(book, int(sim_case.row_idx)))
        raise
