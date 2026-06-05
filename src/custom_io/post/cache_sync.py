#cache_sync.py
"""Module for cache sync functionality in src.custom_io.post."""

from __future__ import annotations

"""Sync/upgrade post_cache.json into Excel t_out.

This macro reads per-case JSON caches and upserts their contents into the
`t_out` table, resolving units at runtime.

It is intended to be called from an Excel button via custom_io.excel actions.
"""

from contextlib import suppress
from pathlib import Path
from typing import Any

import xlwings as xw  # type: ignore[import-not-found]
from xlwings.main import Table  # type: ignore[import-not-found]

from custom_io.case_hash import build_case_hash
from custom_io.excel.cases import get_simulation_cases
from custom_io.excel.config import apply_path_config_from_book
from custom_io.excel.status import (
    set_status_done,
    set_status_fail,
    set_status_pending,
    set_status_running,
    status_range_for_input_row,
)
from custom_io.excel.tables import find_table, get_table_data
from custom_io.excel.write_long import upsert_long_rows
from custom_io.excel.ui_heartbeat import UIHeartbeat
from post.post_cache import cache_path_for_case, load_post_cache_lenient, parse_key, save_post_cache
from post.row import T_OUT_COLUMNS
from post.sim_case_meta import sim_case_meta
from post.unit_resolver import unit_for_category
from core.parameters.sim_case import SimCase


def sync_post_cache_to_t_out(book: xw.Book) -> None:
    """Sync all cases' post_cache.json into the Excel t_out table."""

    apply_path_config_from_book(book)

    hb = UIHeartbeat(book)

    input_table: Table = find_table(book, "t_input")
    input_header, input_body = get_table_data(input_table)
    inputs: tuple[SimCase, ...] = get_simulation_cases(input_header, input_body)

    output_table: Table = find_table(book, "t_out")

    from custom_io.path_config import get_path_config

    cfg = get_path_config()
    artifacts_case_root: Path = cfg.artifacts_root / "case"

    try:
        for sim_case in inputs:
            set_status_pending(book, status_range_for_input_row(book, int(sim_case.row_idx)))
            hb.tick()

        for sim_case in inputs:
            status_cell = status_range_for_input_row(book, int(sim_case.row_idx))
            set_status_running(book, status_cell)
            hb.tick()

            case_hash = build_case_hash(sim_case.to_string())
            p = cache_path_for_case(artifacts_case_dir=artifacts_case_root, case_hash=case_hash)
            cache = load_post_cache_lenient(p, case_hash=case_hash)

            meta = sim_case_meta(sim_case)
            cache.sim_case_meta = meta

            sync_rows: list[dict[str, Any]] = []
            for k, v in cache.rows.items():
                with suppress(Exception):
                    cat, r_i, c_i = parse_key(k)
                    d = {
                        "hash": case_hash,
                        "category": str(cat),
                        "row": int(r_i),
                        "col": int(c_i),
                        "value": float(v),
                        "unit": unit_for_category(str(cat)),
                    }
                    sync_rows.append(d)

            # Upsert to Excel
            if sync_rows:
                upsert_long_rows(
                    table=output_table,
                    rows=sync_rows,
                    required_columns=T_OUT_COLUMNS,
                )
                hb.tick(force=True)

            # Save upgraded cache (rewrite)
            save_post_cache(p, cache)

            set_status_done(book, status_cell)
            hb.tick()

    except Exception:
        # Best-effort mark all as fail
        for sim_case in inputs:
            set_status_fail(book, status_range_for_input_row(book, int(sim_case.row_idx)))
        raise
