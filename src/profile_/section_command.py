#section_command.py
"""Module for section command functionality in src.profile_."""

import math
from typing import Dict, List, Tuple

import numpy as np

from core.apdl_block import apdl_block, apdl_comment
from core.apdl_commands import ApdlCommands
from core.parameters.geometry_params import GeometryParams
from core.parameters.profile_params import (
    SolidProfileParams,
    ProfileParams,
)
from core.unit_cell import UnitCell


def build_section_commands_(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
) -> tuple[ApdlCommands, tuple[int, ...]]:
    if isinstance(profile_params, SolidProfileParams):
        return ((), ())

    kappa = profile_params.kappa
    section_map: Dict[Tuple[float, float], int] = {}
    cmds: List[str] = []
    edge_sec_ids: List[int] = []

    for edge, beam_type_id, ratio in zip(
        unit_cell.edges,
        unit_cell.edge_beam_type_ids,
        unit_cell.edge_ratios,
    ):
        radius_ratio = _get_edge_radius_ratio(
            edge,
            int(beam_type_id),
            unit_cell,
        )
        key = (round(radius_ratio, 12), float(ratio))
        sec_id = section_map.get(key)
        if sec_id is None:
            # Allocate one section id per unique (radius_ratio, ratio).
            sec_id = len(section_map) + 1

            # Match solid modeling convention: use physical radius scaled by unit-cell size.
            # Solid uses:
            #   r = profile_params.radius * radius_ratio * min(geometry_params.size)
            radius = float(
                radius_ratio * profile_params.radius * np.min(geometry_params.size)
            )

            a_eff, iyy_eff, izz_eff, j_eff = _circular_section_properties(radius, ratio)

            label = f"D{radius_ratio:.4f}_Q{ratio:.2f}"

            cmds.extend(apdl_block(f"""
{apdl_comment(f"Define reusable beam section {sec_id} for diameter={radius_ratio:.10g}, ratio={ratio:.10g}")}
SECTYPE,{sec_id},BEAM,ASEC,{label},0
SECDATA,{a_eff:.10g},{iyy_eff:.10g},0,{izz_eff:.10g},0,{j_eff:.10g},0,0,0,0,{radius:.10g},{radius:.10g},{kappa:.10g},{kappa:.10g}
"""))

            section_map[key] = sec_id

        edge_sec_ids.append(sec_id)

    return (tuple(cmds), tuple(edge_sec_ids))


def _get_edge_radius_ratio(
    edge: np.ndarray,
    beam_type_id: int,
    unit_cell: UnitCell,
) -> float:
    if len(edge) >= 3:
        return float(edge[2])

    beam_type = unit_cell.beam_types[beam_type_id]
    radius_ratio = beam_type.get("radius_ratio")
    if radius_ratio is None:
        raise KeyError(f"Beam type {beam_type_id} is missing 'radius_ratio'")
    return float(radius_ratio)


# def _shear_correction_factor(nu: float) -> float:
#     """Return the Timoshenko shear-correction factor for a circular section."""
#     return 6.0 * (1.0 + nu) / (7.0 + 6.0 * nu)


def _circular_section_properties(
    radius: float,
    ratio: float,
    *,
    area_factor: float = 1.0,
    bending_factor: float = 1.0,
    torsion_factor: float = 1.0,
) -> Tuple[float, float, float, float]:
    """Return (A, Iyy, Izz, J) for a circular section.

    `ratio` is the existing per-edge scaling used in this project.

    `ratio` scales all section properties consistently for each edge type.
    """

    a = math.pi * radius**2
    iyy = math.pi * radius**4 / 4.0
    izz = iyy
    j = math.pi * radius**4 / 2.0

    return (
        a * ratio * area_factor,
        iyy * ratio * bending_factor,
        izz * ratio * bending_factor,
        j * ratio * torsion_factor,
    )
