#sim_case_meta.py
"""Module for sim case meta functionality in src.post."""

from __future__ import annotations

"""Flatten :class:`core.parameters.sim_case.SimCase` into row-wise metadata.

The long-format `t_out` table repeats these metadata fields on every record so
Excel pivot tables can filter/group freely without needing joins.

Conventions:
- Keys are snake_case and stable.
- Values are JSON/Excel-friendly scalars (str/int/float).
"""

from dataclasses import asdict, is_dataclass
from typing import Any

import numpy as np

from core.parameters.sim_case import SimCase


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}

    if is_dataclass(obj):
        for k, v in asdict(obj).items():
            out.update(_flatten(v, prefix + k + "_"))
        return out

    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, prefix + str(k) + "_"))
        return out

    if isinstance(obj, (list, tuple, np.ndarray)):
        # Store small vectors with suffixes _0,_1,... (geometry.size is length-3).
        for i, v in enumerate(list(obj)):
            out.update(_flatten(v, prefix + str(i) + "_"))
        return out

    # leaf scalar
    key = prefix[:-1] if prefix.endswith("_") else prefix
    out[key] = obj
    return out


META_COLUMNS: tuple[str, ...] = (
    # Geometry
    "cell_name",
    "cell_size_x",
    "cell_size_y",
    "cell_size_z",
    # Element type
    "element_type",
    # Meshing
    "max_element_size",
    # Profile
    "radius",
    # Material
    "e_mod",
    "nu",
    "density",
    # Setup
    "sim_type",
    "strain",
    "n_substeps",
)


def sim_case_meta(sim_case: SimCase) -> dict[str, Any]:
    """Return a flat dict of sim_case metadata for `t_out` rows.

    Only keys in :data:`META_COLUMNS` are returned (stable schema).
    Missing values are filled with None.
    """

    d: dict[str, Any] = {k: None for k in META_COLUMNS}

    # Geometry
    d["cell_name"] = sim_case.pre_mesh_spec.geometry.cell_name
    sx, sy, sz = (
        float(sim_case.pre_mesh_spec.geometry.size[0]),
        float(sim_case.pre_mesh_spec.geometry.size[1]),
        float(sim_case.pre_mesh_spec.geometry.size[2]),
    )
    d["cell_size_x"], d["cell_size_y"], d["cell_size_z"] = sx, sy, sz

    # Element type
    d["element_type"] = sim_case.pre_mesh_spec.element_type.model

    # Meshing
    d["max_element_size"] = float(sim_case.pre_mesh_spec.meshing.max_element_size)

    # Profile
    prof = sim_case.pre_mesh_spec.profile
    if hasattr(prof, "radius"):
        d["radius"] = float(getattr(prof, "radius"))
    # Material
    d["e_mod"] = float(sim_case.post_mesh_spec.material.e_mod)
    d["nu"] = float(sim_case.post_mesh_spec.material.nu)
    d["density"] = float(sim_case.post_mesh_spec.material.density)

    # Setup
    d["sim_type"] = str(sim_case.post_mesh_spec.setup.sim_type)
    d["strain"] = float(sim_case.post_mesh_spec.setup.strain)
    d["n_substeps"] = int(sim_case.post_mesh_spec.setup.n_substeps)

    return d
