from __future__ import annotations

"""JSON cache for post/t_out results.

This cache is stored per case_hash:
  artifacts/case/<case_hash>/post_cache.json

Key convention (string):
  "{category}|{row}|{col}"

We store *all* computed categories, including intermediate outputs.
Excel t_out writing can still be restricted to requested categories.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
POST_LOGIC_VERSION = 1


def make_key(category: str, row: int, col: int) -> str:
    return f"{category}|{int(row)}|{int(col)}"


@dataclass
class PostCache:
    case_hash: str
    sim_case_meta: dict[str, Any]
    rows: dict[str, dict[str, Any]]  # key -> {value, unit}
    schema_version: int = SCHEMA_VERSION
    post_logic_version: int = POST_LOGIC_VERSION

    def upsert(self, *, category: str, row: int, col: int, value: float, unit: str) -> None:
        self.rows[make_key(category, row, col)] = {"value": float(value), "unit": str(unit)}

    def has(self, *, category: str, row: int, col: int) -> bool:
        return make_key(category, row, col) in self.rows


def load_post_cache(path: Path, *, case_hash: str) -> PostCache:
    if not path.exists():
        return PostCache(case_hash=case_hash, sim_case_meta={}, rows={})

    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        return PostCache(case_hash=case_hash, sim_case_meta={}, rows={})

    if int(obj.get("schema_version", 0)) != SCHEMA_VERSION:
        return PostCache(case_hash=case_hash, sim_case_meta={}, rows={})
    if int(obj.get("post_logic_version", 0)) != POST_LOGIC_VERSION:
        return PostCache(case_hash=case_hash, sim_case_meta={}, rows={})

    if str(obj.get("case_hash", "")) != str(case_hash):
        return PostCache(case_hash=case_hash, sim_case_meta={}, rows={})

    sim_case_meta = obj.get("sim_case_meta")
    if not isinstance(sim_case_meta, dict):
        sim_case_meta = {}

    rows = obj.get("rows")
    if not isinstance(rows, dict):
        rows = {}

    # Ensure rows values are dict-like
    rows2: dict[str, dict[str, Any]] = {}
    for k, v in rows.items():
        if isinstance(k, str) and isinstance(v, dict):
            rows2[k] = v

    return PostCache(case_hash=case_hash, sim_case_meta=sim_case_meta, rows=rows2)


def save_post_cache(path: Path, cache: PostCache) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")

    obj = {
        "schema_version": int(cache.schema_version),
        "post_logic_version": int(cache.post_logic_version),
        "case_hash": str(cache.case_hash),
        "sim_case_meta": cache.sim_case_meta,
        "rows": cache.rows,
    }

    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def cache_path_for_case(*, artifacts_case_dir: Path, case_hash: str) -> Path:
    return artifacts_case_dir / case_hash / "post_cache.json"


def required_keys_static(prefix: str, *, sim_type: str, row: int) -> set[str]:
    """Return the required cache keys for a static output prefix.

    sim_type is used for sparse outputs (effective/specific moduli).
    """

    sim_type_l = str(sim_type).strip().lower()

    cols: Iterable[int]
    if prefix in {"boundary_force", "boundary_moment", "boundary_traction", "contact_traction"}:
        cols = range(1, 10)
    elif prefix in {
        "boundary_stress",
        "boundary_modulus",
        "boundary_modulus_ratio",
        "contact_stress",
        "volume_stress",
        "volume_avg_stress",
    }:
        cols = range(1, 7)
    elif prefix in {"boundary_touch_area", "boundary_touch_area_ratio"}:
        cols = range(1, 4)
    elif prefix in {"effective_youngs_modulus", "specific_youngs_modulus"}:
        # Only one of (X,Y,Z) is populated depending on sim_type.
        c = {"xx": 1, "yy": 2, "zz": 3}.get(sim_type_l)
        cols = (c,) if c is not None else ()
    elif prefix in {"effective_shear_modulus", "specific_shear_modulus"}:
        # Shear cols aligned with boundary_stress convention: YZ=4, XZ=5, XY=6
        c = {"yz": 4, "xz": 5, "xy": 6}.get(sim_type_l)
        cols = (c,) if c is not None else ()
    else:
        cols = (1,)

    return {make_key(prefix, row, c) for c in cols if c is not None}


def required_keys_modal(prefix: str, *, mode_index: int) -> set[str]:
    if prefix.startswith("res_freq_"):
        cols = (1,)
    elif prefix.startswith("part_factor_"):
        cols = (1, 2, 3)
    elif prefix.startswith("eff_modal_mass_"):
        cols = (1, 2, 3)
    else:
        cols = (1,)

    return {make_key(prefix, mode_index, c) for c in cols}
