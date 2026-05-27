from __future__ import annotations

"""JSON cache for post/t_out results.

This cache is stored per case_hash:
  artifacts/case/<case_hash>/post_cache.json

Key convention (string):
  "{category}|{row}|{col}"

Cache stores numeric values only (no unit). Units are resolved at runtime.
We store *all* computed categories, including intermediate outputs.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
# Increment this whenever category naming / post semantics change in a way that
# should invalidate old cached numeric results.
POST_LOGIC_VERSION = 2


def make_key(category: str, row: int, col: int) -> str:
    return f"{category}|{int(row)}|{int(col)}"


@dataclass
class PostCache:
    case_hash: str
    sim_case_meta: dict[str, Any]
    rows: dict[str, float]  # key -> value
    schema_version: int = SCHEMA_VERSION
    post_logic_version: int = POST_LOGIC_VERSION

    def upsert(self, *, category: str, row: int, col: int, value: float) -> None:
        self.rows[make_key(category, row, col)] = float(value)

    def has(self, *, category: str, row: int, col: int) -> bool:
        return make_key(category, row, col) in self.rows


def parse_key(key: str) -> tuple[str, int, int]:
    """Parse a cache key into (category,row,col)."""

    parts = str(key).split("|")
    if len(parts) != 3:
        raise ValueError(f"Invalid cache key: {key!r}")
    cat = parts[0]
    row = int(parts[1])
    col = int(parts[2])
    return cat, row, col


def _parse_post_cache_obj(obj: Any, *, case_hash: str) -> PostCache:
    if not isinstance(obj, dict):
        return PostCache(case_hash=case_hash, sim_case_meta={}, rows={})

    sim_case_meta = obj.get("sim_case_meta")
    if not isinstance(sim_case_meta, dict):
        sim_case_meta = {}

    rows = obj.get("rows")
    if not isinstance(rows, dict):
        rows = {}

    rows2: dict[str, float] = {}
    for k, v in rows.items():
        if not isinstance(k, str):
            continue
        # Backward-compatible: accept {value, unit} dict from older caches.
        if isinstance(v, dict) and "value" in v:
            try:
                rows2[k] = float(v.get("value"))
            except Exception:
                continue
        else:
            try:
                rows2[k] = float(v)
            except Exception:
                continue

    return PostCache(case_hash=case_hash, sim_case_meta=sim_case_meta, rows=rows2)


def load_post_cache(path: Path, *, case_hash: str) -> PostCache:
    """Strict loader: enforces schema_version/post_logic_version match."""

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

    return _parse_post_cache_obj(obj, case_hash=case_hash)


def _migrate_legacy_category_names(rows: dict[str, float]) -> dict[str, float]:
    """Migrate legacy category names to the current naming convention."""

    rename = {
        "volume_stress": "stress_vol_sum",
        "volume_avg_stress": "stress_vol_avg",
        "volume_energy": "energy_sum",
        "volume_avg_energy": "energy_vol_avg",
    }

    out: dict[str, float] = {}
    for k, v in rows.items():
        try:
            cat, r, c = parse_key(k)
        except Exception:
            continue
        cat2 = rename.get(cat, cat)
        out[make_key(cat2, r, c)] = float(v)
    return out


def load_post_cache_lenient(path: Path, *, case_hash: str) -> PostCache:
    """Lenient loader: ignores version fields and attempts best-effort parse.

    Intended for a "sync/upgrade" macro that rewrites old caches into the latest
    schema.
    """

    if not path.exists():
        return PostCache(case_hash=case_hash, sim_case_meta={}, rows={})

    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return PostCache(case_hash=case_hash, sim_case_meta={}, rows={})

    c = _parse_post_cache_obj(obj, case_hash=case_hash)

    # Migrate legacy category names (e.g., volume_* -> stress/energy naming).
    c.rows = _migrate_legacy_category_names(c.rows)

    # Upgrade versions
    c.schema_version = SCHEMA_VERSION
    c.post_logic_version = POST_LOGIC_VERSION
    return c


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
        "stress_vol_sum",
        "stress_vol_avg",
    }:
        cols = range(1, 7)
    elif prefix in {"boundary_touch_area", "boundary_touch_area_ratio"}:
        cols = range(1, 4)
    elif prefix in {"energy_sum", "energy_vol_avg"}:
        cols = (1,)
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


def required_keys_modal(prefix: str, *, sim_type: str, mode_index: int) -> set[str]:
    """Return required keys for a modal prefix (res_freq_*, part_factor_*, eff_modal_mass_*).

    Cache category is stored without the trailing _<mode> because row encodes the
    mode index. For modal_ff, we append suffix '_ff' to the category.
    """

    p = str(prefix)
    sim_type_l = str(sim_type).strip().lower()
    suf = "_ff" if sim_type_l == "modal_ff" else ""

    if p.startswith("res_freq_"):
        cat = f"res_freq{suf}"
        cols = (1,)
    elif p.startswith("part_factor_"):
        cat = f"part_factor{suf}"
        cols = (1, 2, 3)
    elif p.startswith("eff_modal_mass_"):
        cat = f"eff_modal_mass{suf}"
        cols = (1, 2, 3)
    else:
        cat = p
        cols = (1,)

    return {make_key(cat, mode_index, c) for c in cols}
