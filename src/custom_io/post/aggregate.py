#aggregate.py
"""Module for aggregate functionality in src.custom_io.post."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from xlwings.main import Table  # type: ignore[import-not-found]

from core.parameters.sim_case import SimCase
from custom_io.case_hash import build_case_hash
from custom_io.excel.write_long import upsert_long_rows
from post.post_cache import (
    PostCache,
    cache_path_for_case,
    load_post_cache,
    make_key,
    parse_key,
    save_post_cache,
)
from post.row import T_OUT_COLUMNS
from post.sim_case_meta import sim_case_meta
from post.unit_resolver import unit_for_category


def canonical_sim_type(sim_type: object) -> str:
    """Normalize user-facing simulation type labels.

    Parameters
    ----------
    sim_type : object
        Raw simulation type from Excel or a ``SimCase``.

    Returns
    -------
    str
        Canonical simulation type. Aggregate aliases ``static`` and ``total``
        become ``"100"`` and ``"101"`` respectively.
    """

    s = str(sim_type).strip().lower()
    if s in {"100", "100.0", "static"}:
        return "100"
    if s in {"101", "101.0", "total"}:
        return "101"
    if s == "zx":
        return "xz"
    return s


def is_aggregate_sim_type(sim_type: object) -> bool:
    """Return whether a simulation type is an aggregate postprocess row.

    Parameters
    ----------
    sim_type : object
        Raw simulation type value.

    Returns
    -------
    bool
        ``True`` for static/100 and total/101 aggregate rows.
    """

    return canonical_sim_type(sim_type) in {"100", "101"}


def write_aggregate_rows(
    *,
    aggregate_case: SimCase,
    source_cases: tuple[SimCase, ...],
    case_artifacts_root: Path,
    output_table: Table,
) -> None:
    """Build and write static/total aggregate postprocess rows.

    Parameters
    ----------
    aggregate_case : SimCase
        Aggregate row case whose simulation type is static/100 or total/101.
    source_cases : tuple[SimCase, ...]
        Candidate component cases used to load post caches.
    case_artifacts_root : Path
        Root directory containing per-case artifact folders and post caches.
    output_table : Table
        Excel ``t_out`` table to upsert aggregate rows into.

    Raises
    ------
    RuntimeError
        If required component cases or cache values are missing.
    """

    aggregate_type = canonical_sim_type(aggregate_case.post_mesh_spec.setup.sim_type)
    if aggregate_type == "100":
        required_types = ("xx", "yy", "zz", "xy", "yz", "xz")
    elif aggregate_type == "101":
        required_types = ("xx", "yy", "zz", "xy", "yz", "xz", "modal", "modal_ff")
    else:
        raise ValueError(
            f"Not an aggregate sim_type: {aggregate_case.post_mesh_spec.setup.sim_type!r}"
        )

    source_by_group_and_type = _source_case_lookup(source_cases)
    group_key = aggregate_case.to_string_without_sim_type()
    aggregate_hash = build_case_hash(aggregate_case.to_string())

    out_rows: list[dict[str, Any]] = []
    aggregate_cache = PostCache(
        case_hash=aggregate_hash,
        sim_case_meta=sim_case_meta(aggregate_case),
        rows={},
    )
    missing: list[str] = []
    static_tensor_values: dict[tuple[int, int], float] = {}

    for required_type in required_types:
        src_case = source_by_group_and_type.get((group_key, required_type))
        if src_case is None:
            missing.append(required_type)
            continue

        _merge_source_cache(
            src_case=src_case,
            required_type=required_type,
            case_artifacts_root=case_artifacts_root,
            aggregate_hash=aggregate_hash,
            aggregate_cache=aggregate_cache,
            out_rows=out_rows,
            static_tensor_values=static_tensor_values,
            missing=missing,
        )

    _add_elastic_tensors(
        aggregate_type=aggregate_type,
        aggregate_hash=aggregate_hash,
        aggregate_cache=aggregate_cache,
        out_rows=out_rows,
        static_tensor_values=static_tensor_values,
        missing=missing,
    )

    if missing:
        label = "static=100" if aggregate_type == "100" else "total=101"
        raise RuntimeError(
            f"Cannot build {label} aggregate for hash={aggregate_hash}: "
            f"missing required case/cache(s): {', '.join(missing)}"
        )

    save_post_cache(
        cache_path_for_case(artifacts_case_dir=case_artifacts_root, case_hash=aggregate_hash),
        aggregate_cache,
    )
    upsert_long_rows(table=output_table, rows=out_rows, required_columns=T_OUT_COLUMNS)


def _source_case_lookup(source_cases: tuple[SimCase, ...]) -> dict[tuple[str, str], SimCase]:
    """Index non-aggregate source cases by group key and simulation type.

    Parameters
    ----------
    source_cases : tuple[SimCase, ...]
        Cases available for aggregate construction.

    Returns
    -------
    dict[tuple[str, str], SimCase]
        Lookup keyed by ``(case_without_sim_type, canonical_sim_type)``.
    """

    lookup: dict[tuple[str, str], SimCase] = {}
    for src_case in source_cases:
        src_type = canonical_sim_type(src_case.post_mesh_spec.setup.sim_type)
        if is_aggregate_sim_type(src_type):
            continue
        lookup[(src_case.to_string_without_sim_type(), src_type)] = src_case
    return lookup


def _merge_source_cache(
    *,
    src_case: SimCase,
    required_type: str,
    case_artifacts_root: Path,
    aggregate_hash: str,
    aggregate_cache: PostCache,
    out_rows: list[dict[str, Any]],
    static_tensor_values: dict[tuple[int, int], float],
    missing: list[str],
) -> None:
    """Merge one component case post cache into an aggregate cache.

    Parameters
    ----------
    src_case : SimCase
        Component case whose post cache is loaded.
    required_type : str
        Canonical simulation type label used for missing-cache diagnostics.
    case_artifacts_root : Path
        Root directory containing per-case artifact folders.
    aggregate_hash : str
        Hash assigned to the aggregate case.
    aggregate_cache : PostCache
        Aggregate cache object to update.
    out_rows : list[dict[str, Any]]
        Excel output rows populated from the source cache.
    static_tensor_values : dict[tuple[int, int], float]
        Mutable stiffness tensor accumulator.
    missing : list[str]
        Mutable diagnostics list for missing required data.
    """

    src_hash = build_case_hash(src_case.to_string())
    cache_path = cache_path_for_case(
        artifacts_case_dir=case_artifacts_root,
        case_hash=src_hash,
    )
    cache = load_post_cache(cache_path, case_hash=src_hash)
    if not cache.rows:
        missing.append(f"{required_type}:post_cache")
        return

    for k, v in cache.rows.items():
        try:
            cat, r_i, c_i = parse_key(k)
        except Exception:
            continue

        category = str(cat)
        row = int(r_i)
        col = int(c_i)
        value = float(v)
        aggregate_cache.rows[make_key(category, row, col)] = value

        if category == "modulus.boundary.value":
            static_tensor_values[(row, col)] = value

        out_rows.append(
            {
                "hash": aggregate_hash,
                "category": category,
                "row": row,
                "col": col,
                "value": value,
                "unit": unit_for_category(category),
            }
        )


def _add_elastic_tensors(
    *,
    aggregate_type: str,
    aggregate_hash: str,
    aggregate_cache: PostCache,
    out_rows: list[dict[str, Any]],
    static_tensor_values: dict[tuple[int, int], float],
    missing: list[str],
) -> None:
    """Add stiffness and compliance tensors to an aggregate cache.

    Parameters
    ----------
    aggregate_type : str
        Canonical aggregate simulation type, either ``"100"`` or ``"101"``.
    aggregate_hash : str
        Hash assigned to the aggregate case.
    aggregate_cache : PostCache
        Cache object that receives tensor entries.
    out_rows : list[dict[str, Any]]
        Excel output rows to append compliance values to.
    static_tensor_values : dict[tuple[int, int], float]
        Stiffness tensor entries collected from component static load cases.
    missing : list[str]
        Mutable list that receives missing tensor entry labels.
    """

    stiffness = np.empty((6, 6), dtype=float)
    for r_i in range(1, 7):
        for c_i in range(1, 7):
            v = static_tensor_values.get((r_i, c_i))
            if v is None:
                missing.append(f"stiffness.elastic.tensor[{r_i},{c_i}]")
                stiffness[r_i - 1, c_i - 1] = np.nan
                continue
            stiffness[r_i - 1, c_i - 1] = float(v)
            aggregate_cache.rows[make_key("stiffness.elastic.tensor", r_i, c_i)] = float(v)

    if missing:
        return

    try:
        compliance = np.linalg.inv(stiffness)
    except np.linalg.LinAlgError as e:
        label = "static=100" if aggregate_type == "100" else "total=101"
        raise RuntimeError(
            f"Cannot build compliance.elastic.tensor for {label} aggregate "
            f"hash={aggregate_hash}: stiffness tensor is singular"
        ) from e

    if not np.all(np.isfinite(compliance)):
        label = "static=100" if aggregate_type == "100" else "total=101"
        raise RuntimeError(
            f"Cannot build compliance.elastic.tensor for {label} aggregate "
            f"hash={aggregate_hash}: non-finite inverse values"
        )

    for r_i in range(1, 7):
        for c_i in range(1, 7):
            v = float(compliance[r_i - 1, c_i - 1])
            aggregate_cache.rows[make_key("compliance.elastic.tensor", r_i, c_i)] = v
            out_rows.append(
                {
                    "hash": aggregate_hash,
                    "category": "compliance.elastic.tensor",
                    "row": r_i,
                    "col": c_i,
                    "value": v,
                    "unit": unit_for_category("compliance.elastic.tensor"),
                }
            )
