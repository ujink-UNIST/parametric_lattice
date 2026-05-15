# geometry_io.py

from __future__ import annotations

import hashlib
import json
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any

import numpy as np

from core.apdl_block import apdl_section
from core.apdl_commands import ApdlCommands
from core.parameters.sim_case import SimCase

_GEOMETRY_DB_ROOT = "artifacts/geometry_db"
_GEOMETRY_DB_BASENAME = "geometry"
_GEOMETRY_DB_SUFFIX = ".db"
_GEOMETRY_IGES_EXT = "iges"


def _get_geometry_key(sim_case: SimCase) -> str:
    """Return a stable string key identifying *geometry-only* inputs.

    This intentionally excludes meshing/material/setup so the same geometry can
    be reused across multiple simulation cases.
    """

    return (
        sim_case.pre_mesh_spec.element_type.to_string()
        + "__"
        + sim_case.pre_mesh_spec.profile.to_string()
        + "__"
        + sim_case.pre_mesh_spec.geometry.to_string()
    )


def _get_geometry_hash(sim_case: SimCase) -> str:
    key = _get_geometry_key(sim_case)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _geometry_db_dir(sim_case: SimCase) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return (
        repo_root
        / _GEOMETRY_DB_ROOT
        / _get_geometry_hash(sim_case)
    )


def _geometry_db_path(sim_case: SimCase) -> Path:
    return (
        _geometry_db_dir(sim_case)
        / f"{_GEOMETRY_DB_BASENAME}{_GEOMETRY_DB_SUFFIX}"
    )


def import_geometry_db(sim_case: SimCase) -> ApdlCommands:
    """APDL commands to restore a previously exported geometry database."""

    db_dir = _geometry_db_dir(sim_case)
    db_path = _geometry_db_path(sim_case)
    if not db_path.exists():
        raise FileNotFoundError(
            f"Geometry DB not found for geometry_hash={_get_geometry_hash(sim_case)}: {db_path}"
        )

    # RESUME reads the .db file (ANSYS database). We clear first to avoid
    # contaminating the session with existing entities.
    return (
        "",
        apdl_section("IMPORT GEOMETRY DB"),
        "/CLEAR",
        f"RESUME,'{_GEOMETRY_DB_BASENAME}','db','{db_dir.as_posix()}'",
    )


def _to_jsonable(obj: Any) -> Any:
    """Best-effort conversion for project dataclasses / numpy into JSON."""

    def conv(x: Any) -> Any:
        if is_dataclass(x):
            return {k: conv(v) for k, v in vars(x).items()}
        if isinstance(x, dict):
            return {str(k): conv(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [conv(v) for v in x]
        if isinstance(x, Path):
            return str(x)
        if isinstance(x, np.ndarray):
            return x.tolist()
        return x

    return conv(obj)


def export_geometry_db(sim_case: SimCase) -> ApdlCommands:
    """APDL commands to export (SAVE) the current geometry database.

    Also writes a small `sim_case.json` next to the database containing the
    geometry-defining inputs (element_type/profile/geometry) for traceability.
    """

    db_dir = _geometry_db_dir(sim_case)
    db_dir.mkdir(parents=True, exist_ok=True)

    # Persist minimal metadata next to the DB for reproducibility.
    meta_path = db_dir / "sim_case.json"
    meta = {
        "geometry_key": _get_geometry_key(sim_case),
        "geometry_hash": _get_geometry_hash(sim_case),
        "element_type": sim_case.pre_mesh_spec.element_type,
        "profile": sim_case.pre_mesh_spec.profile,
        "geometry": sim_case.pre_mesh_spec.geometry,
    }
    meta_path.write_text(
        json.dumps(
            _to_jsonable(meta),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return (
        "",
        apdl_section("EXPORT GEOMETRY DB"),
        f"SAVE,'{_GEOMETRY_DB_BASENAME}','db','{db_dir.as_posix()}'",
    )


def export_geometry_iges(sim_case: SimCase) -> ApdlCommands:
    """APDL commands to export the solid model as an IGES file.

    Output path:
      artifacts/geometry_db/<geometry_hash>/geometry.iges

    Notes:
      - IGESOUT requires that lower-level entities are selected; we issue
        ALLSEL,BELOW,ALL for safety.
    """

    out_dir = _geometry_db_dir(sim_case)
    out_dir.mkdir(parents=True, exist_ok=True)

    # IGESOUT takes (Fname, Ext). Fname may include an absolute/relative path.
    fname = (out_dir / _GEOMETRY_DB_BASENAME).as_posix()

    return (
        "",
        apdl_section("EXPORT GEOMETRY IGES"),
        "ALLSEL,BELOW,ALL",
        f"IGESOUT,'{fname}','{_GEOMETRY_IGES_EXT}',,1",
    )
