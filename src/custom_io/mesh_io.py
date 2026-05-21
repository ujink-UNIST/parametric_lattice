# mesh_io.py

from __future__ import annotations

import json
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any

import numpy as np

from core.apdl_block import apdl_section
from core.apdl_commands import ApdlCommands
from core.hashing import sha1_hex
from core.parameters.sim_case import SimCase

from custom_io.path_config import get_path_config

_MESH_DB_ROOT = "mesh_db"
_MESH_DB_BASENAME = "mesh"
_MESH_DB_SUFFIX = ".db"
_MESH_CDB_EXT = "cdb"


def _get_mesh_key(sim_case: SimCase) -> str:
    """Return a stable string key identifying *pre-mesh* inputs.

    This includes element type, geometry, profile, and meshing parameters.
    """

    return sim_case.pre_mesh_spec.to_string()


def _get_mesh_hash(sim_case: SimCase) -> str:
    key = _get_mesh_key(sim_case)
    return sha1_hex(key)


def mesh_hash(sim_case: SimCase) -> str:
    """Public wrapper for the stable mesh hash."""

    return _get_mesh_hash(sim_case)


def _mesh_db_dir(sim_case: SimCase) -> Path:
    artifacts_root = get_path_config().artifacts_root
    return artifacts_root / _MESH_DB_ROOT / _get_mesh_hash(sim_case)


def _mesh_db_path(sim_case: SimCase) -> Path:
    return _mesh_db_dir(sim_case) / f"{_MESH_DB_BASENAME}{_MESH_DB_SUFFIX}"


def import_mesh_db(sim_case: SimCase) -> ApdlCommands:
    """APDL commands to restore a previously exported mesh database."""

    db_dir = _mesh_db_dir(sim_case)
    db_path = _mesh_db_path(sim_case)
    if not db_path.exists():
        raise FileNotFoundError(
            f"Mesh DB not found for mesh_hash={_get_mesh_hash(sim_case)}: {db_path}"
        )

    return (
        "",
        apdl_section("IMPORT MESH DB"),
        "/CLEAR",
        f"RESUME,'{_MESH_DB_BASENAME}','db','{db_dir.as_posix()}'",
    )


def _to_jsonable(obj: Any) -> Any:
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


def export_mesh_db(sim_case: SimCase) -> ApdlCommands:
    """APDL commands to export (SAVE) the current database after meshing.

    Also writes `sim_case.json` next to the database containing the pre-mesh
    defining inputs for traceability.
    """

    db_dir = _mesh_db_dir(sim_case)
    db_dir.mkdir(parents=True, exist_ok=True)

    meta_path = db_dir / "sim_case.json"
    meta = {
        "mesh_key": _get_mesh_key(sim_case),
        "mesh_hash": _get_mesh_hash(sim_case),
        "pre_mesh_spec": sim_case.pre_mesh_spec,
        "element_type": sim_case.pre_mesh_spec.element_type,
        "profile": sim_case.pre_mesh_spec.profile,
        "geometry": sim_case.pre_mesh_spec.geometry,
        "meshing": sim_case.pre_mesh_spec.meshing,
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
        apdl_section("EXPORT MESH DB"),
        f"SAVE,'{_MESH_DB_BASENAME}','db','{db_dir.as_posix()}'",
    )


def export_mesh_cdb(sim_case: SimCase) -> ApdlCommands:
    """APDL commands to export a mesh archive (.cdb).

    Output path:
      artifacts/mesh_db/<mesh_hash>/mesh.cdb

    We use CDWRITE,GEOM to write nodal/element geometry (mesh) in a portable
    archive format.
    """

    out_dir = _mesh_db_dir(sim_case)
    out_dir.mkdir(parents=True, exist_ok=True)

    # CDWRITE takes (Option, Fname, Ext). Fname may include a directory path.
    fname = (out_dir / _MESH_DB_BASENAME).as_posix()

    return (
        "",
        apdl_section("EXPORT MESH CDB"),
        f"CDWRITE,GEOM,'{fname}','{_MESH_CDB_EXT}',,'','',BLOCKED",
    )
