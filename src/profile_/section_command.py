# section_command.py

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
) -> tuple[ApdlCommands, tuple[int, ...], tuple[int, ...]]:
    if isinstance(profile_params, SolidProfileParams):
        return ((), (), ())

    kappa = profile_params.kappa
    section_map: Dict[Tuple[float, float], int] = {}
    cmds: List[str] = []
    edge_sec_ids: List[int] = []
    edge_joint_sec_ids: List[int] = []

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
        sec_id_pair = section_map.get(key)
        if sec_id_pair is None:
            # Allocate two section ids per unique (radius_ratio, ratio):
            #   - normal section
            #   - joint-strengthened section (same area, modified I/J)
            sec_id_normal = len(section_map) * 2 + 1
            sec_id_joint = len(section_map) * 2 + 2

            # Match solid modeling convention: use physical radius scaled by unit-cell size.
            # Solid uses:
            #   r = profile_params.radius * radius_ratio * min(geometry_params.size)
            radius = float(
                radius_ratio * profile_params.radius * np.min(geometry_params.size)
            )

            a_eff, iyy_eff, izz_eff, j_eff = _circular_section_properties(
                radius,
                ratio,
                area_factor=1.0,
                bending_factor=1.0,
                torsion_factor=1.0,
            )

            # Joint section: optionally force "rigid" bending/torsion to mimic solid-like joints.
            area_factor = float(getattr(profile_params, "joint_area_factor", 1.0))
            bending_factor = float(getattr(profile_params, "joint_bending_factor", 1.0))
            torsion_factor = float(getattr(profile_params, "joint_torsion_factor", 1.0))

            a_j, iyy_j, izz_j, j_j = _circular_section_properties(
                radius,
                ratio,
                area_factor=area_factor,
                bending_factor=bending_factor,
                torsion_factor=torsion_factor,
            )

            label = f"D{radius_ratio:.4f}_Q{ratio:.2f}"
            label_joint = f"{label}_JOINT"

            cmds.extend(apdl_block(f"""
{apdl_comment(f"Define reusable beam section {sec_id_normal} (normal) for diameter={radius_ratio:.10g}, ratio={ratio:.10g}")}
SECTYPE,{sec_id_normal},BEAM,ASEC,{label},0
SECDATA,{a_eff:.10g},{iyy_eff:.10g},0,{izz_eff:.10g},0,{j_eff:.10g},0,0,0,0,{radius:.10g},{radius:.10g},{kappa:.10g},{kappa:.10g}

{apdl_comment(f"Define reusable beam section {sec_id_joint} (joint) for diameter={radius_ratio:.10g}, ratio={ratio:.10g}")}
SECTYPE,{sec_id_joint},BEAM,ASEC,{label_joint},0
SECDATA,{a_j:.10g},{iyy_j:.10g},0,{izz_j:.10g},0,{j_j:.10g},0,0,0,0,{radius:.10g},{radius:.10g},{kappa:.10g},{kappa:.10g}
"""))

            section_map[key] = (sec_id_normal, sec_id_joint)
        else:
            sec_id_normal, sec_id_joint = sec_id_pair

        edge_sec_ids.append(sec_id_normal)
        edge_joint_sec_ids.append(sec_id_joint)

    return (tuple(cmds), tuple(edge_sec_ids), tuple(edge_joint_sec_ids))


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

    The *_factor knobs allow joint strengthening experiments where bending/torsion
    stiffness is scaled without necessarily scaling axial area the same way.
    Defaults keep current behavior.
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
