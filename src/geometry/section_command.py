# File: c:\Users\USER\Documents\parametric_lattice\src\geometry\section_command.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


import math
from typing import Dict, List, Tuple

from core.apdl_commands import ApdlCommands
from core.parameters.material_params import MaterialParams
from core.unit_cell import UnitCell


def build_section_commands_(
    unit_cell: UnitCell, material_params: MaterialParams
) -> Tuple[ApdlCommands, Tuple[int, ...]]:
    kappa = _shear_correction_factor(material_params.nu)
    section_map: Dict[Tuple[float, float], int] = {}
    cmds: List[str] = []
    edge_sec_ids: List[int] = []

    for (_, _, diameter), ratio in zip(
        unit_cell.edges, unit_cell.edge_ratios
    ):
        key = (round(diameter, 12), float(ratio))
        sec_id = section_map.get(key)
        if sec_id is None:
            sec_id = len(section_map) + 1
            radius = diameter / 2.0
            a_eff, iyy_eff, izz_eff, j_eff = (
                _circular_section_properties(radius, ratio)
            )
            label = f"D{diameter:.4f}_Q{ratio:.2f}"
            cmds.append(
                f"! Define reusable beam section {sec_id} for diameter={diameter:.10g}, ratio={ratio:.10g}"
            )
            cmds.append(
                f"SECTYPE,{sec_id},BEAM,ASEC,{label},0"
            )
            cmds.append(
                f"SECDATA,"
                f"{a_eff:.10g},"
                f"{iyy_eff:.10g},"
                f"0,"
                f"{izz_eff:.10g},"
                f"0,"
                f"{j_eff:.10g},"
                f"0,0,0,0,"
                f"{radius:.10g},"
                f"{radius:.10g},"
                f"{kappa:.10g},"
                f"{kappa:.10g}"
            )
            section_map[key] = sec_id
        edge_sec_ids.append(sec_id)

    return tuple(cmds), tuple(edge_sec_ids)


def _shear_correction_factor(nu: float) -> float:
    """Return the Timoshenko shear-correction factor for a circular section."""
    return 6.0 * (1.0 + nu) / (7.0 + 6.0 * nu)


def _circular_section_properties(
    radius: float, ratio: float
) -> Tuple[float, float, float, float]:
    """Return effective circular beam section properties scaled by ``ratio``."""
    a = math.pi * radius**2
    iyy = math.pi * radius**4 / 4.0
    izz = iyy
    j = math.pi * radius**4 / 2.0
    return (a * ratio, iyy * ratio, izz * ratio, j * ratio)
