#solid_section_command.py
"""Module for solid section command functionality in src.profile_."""

from typing import List

import numpy as np

from core.apdl_block import (
    apdl_block,
    apdl_comment,
    apdl_inline_comment,
)
from core.apdl_commands import ApdlCommands
from core.floats.vector import Vector3
from core.geometric.transform import transform_coords
from core.parameters.geometry_params import GeometryParams
from core.parameters.profile_params import (
    BeamProfileParams,
    ProfileParams,
)
from core.unit_cell import UnitCell


def build_solid_section_commands_(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
) -> ApdlCommands:
    if isinstance(profile_params, BeamProfileParams):
        return ()
    orientation_keypoint_start = len(unit_cell.nodes)
    cs_id = 11
    cmds: List[str] = []

    for i, (edge, beam_type_id) in enumerate(
        zip(unit_cell.edges, unit_cell.edge_beam_type_ids),
        start=1,
    ):
        n1_idx, n2_idx = edge
        kb = n1_idx + 1
        kb_t = n2_idx + 1
        kb_n = orientation_keypoint_start + 2 * i - 1
        kb_b = orientation_keypoint_start + 2 * i
        radius = (
            profile_params.radius
            * unit_cell.beam_types[beam_type_id]["radius_ratio"]
            * np.min(geometry_params.size)
        )

        length = np.linalg.norm(
            transform_coords(
                unit_cell.nodes[n2_idx],
                geometry_params.size,
            )
            - transform_coords(
                unit_cell.nodes[n1_idx],
                geometry_params.size,
            )
        )

        cmds.extend(apdl_block(f"""
{apdl_comment(f"Create solid beam for strut {i-1}: e {kb-1} {kb_t-1}")}
CSKP,{cs_id},0,{kb},{kb_b},{kb_n}
CSYS,{cs_id}
WPCSYS, -1
CYL4,0,0,0,0,{radius: .6f},360,{length: .6f} {apdl_inline_comment(f"{beam_type_id}: b {unit_cell.beam_types[beam_type_id]['section_type']} {unit_cell.beam_types[beam_type_id]['radius_ratio']}")}
CSYS,0
WPCSYS, 0
            """))
        cs_id += 1

    return tuple(cmds)


def get_shared_nodes(
    edge: np.ndarray,
    extend_edge: np.ndarray,
) -> set[int]:
    return set(map(int, edge)) & set(map(int, extend_edge))


def build_solid_sphere_commands_(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
    sphere_csys_start: int,
) -> ApdlCommands:
    cmds: List[str] = []
    skipped_node_ids: set[int] = set()

    for edge, edge_extend_id in zip(unit_cell.edges, unit_cell.edge_extend_ids):
        if edge_extend_id == -1:
            continue
        nodes = get_shared_nodes(edge, unit_cell.edges[edge_extend_id])
        for n in nodes:
            skipped_node_ids.add(n)

    for i, node in enumerate(unit_cell.nodes):
        if i in skipped_node_ids:
            continue

        radius_ratio: float = 0

        for edge, beam_type_id in zip(
            unit_cell.edges,
            unit_cell.edge_beam_type_ids,
        ):
            if edge[0] == i or edge[1] == i:
                radius_ratio = max(
                    radius_ratio,
                    unit_cell.beam_types[beam_type_id]["radius_ratio"],
                )
        if radius_ratio <= 0.0:
            continue
        position: Vector3 = transform_coords(
            node,
            geometry_params.size,
        )

        x, y, z = position
        csid = sphere_csys_start + i
        r = radius_ratio * profile_params.radius * np.min(geometry_params.size)

        cmds.extend(apdl_block(f"""
{apdl_comment(f"Create node sphere {i}")}
LOCAL,{csid},0,{x:.6f},{y:.6f},{z:.6f}
CSYS,{csid}
WPCSYS,-1
SPH4,0,0,0,{r:.6f}
CSYS,0
WPCSYS,0
"""))
    return tuple(cmds)


def merge_solid_extending_sections_commands_(
    unit_cell: UnitCell,
    profile_params: ProfileParams,
) -> ApdlCommands:
    if isinstance(profile_params, BeamProfileParams):
        return ()
    cmds: List[str] = []

    for i0, i1 in enumerate(unit_cell.edge_extend_ids):
        if i1 == -1:
            continue
        vol_id_0 = i0 + 1
        vol_id_1 = i1 + 1
        cmds.extend(apdl_block(f"""
                {apdl_comment(f"Merge strut volumes {vol_id_0} and {vol_id_1}")}
                VSEL,S,VOLU,,{vol_id_0}
                VSEL,A,VOLU,,{vol_id_1}
                VGLUE,ALL
                VADD,ALL
                ALLSEL,ALL
            """))

    return tuple(cmds)


def merge_solid_all_commands_(
    profile_params: ProfileParams,
) -> ApdlCommands:
    if isinstance(profile_params, BeamProfileParams):
        return ()
    return apdl_block("""
            ALLSEL,ALL
            NUMMRG,ALL
            VADD,ALL
            NUMMRG,ALL 
            NUMCMP,ALL
            """)


def build_geometry_trim_commands_(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
) -> ApdlCommands:
    if isinstance(profile_params, BeamProfileParams):
        return ()

    x, y, z = geometry_params.size
    hx, hy, hz = x / 2, y / 2, z / 2
    max_radius_ratio = max(
        float(beam_type["radius_ratio"])
        for beam_type in unit_cell.beam_types
    )
    max_physical_radius = (
        float(profile_params.radius) * max_radius_ratio * float(np.min(geometry_params.size))
    )
    trim_offset = max_physical_radius / 2.0

    cmds: list[str] = list(apdl_block(f"""

{apdl_comment("Modify geometry to match periodic condition")}
"""))

    directions = [
        (x, 0, 0, "X"),
        (0, y, 0, "Y"),
        (0, 0, z, "Z"),
    ]

    for i, (dx, dy, dz, axis) in enumerate(directions):
        bx0, bx1 = ((-hx - trim_offset, hx + trim_offset) if axis == "X" else (-x, x))
        by0, by1 = ((-hy - trim_offset, hy + trim_offset) if axis == "Y" else (-y, y))
        bz0, bz1 = ((-hz - trim_offset, hz + trim_offset) if axis == "Z" else (-z, z))

        cmds.extend(apdl_block(f"""
{apdl_comment(f"Step {i+1}: Extend geometry along {axis}-axis and trim with half max physical radius offset")}
ALLSEL
VSEL,S,VOLU,,1
VGEN,2,ALL,,,{ -dx },{ -dy },{ -dz }
VSEL,S,VOLU,,1
VGEN,2,ALL,,,{ dx },{ dy },{ dz }
ALLSEL
VADD,ALL
NUMMRG,ALL
NUMCMP,ALL
BLOCK,{bx0},{bx1},{by0},{by1},{bz0},{bz1}
VINTF,1,2
NUMMRG,ALL
NUMCMP,ALL
            """))

    cmds.extend(apdl_block(f"""
{apdl_comment("Final trim: clip to exact unit cell domain [-hx,hx] x [-hy,hy] x [-hz,hz]")}
BLOCK,{-hx},{hx},{-hy},{hy},{-hz},{hz}
VINTF,1,2
NUMMRG,ALL
NUMCMP,ALL
        """))

    return tuple(cmds)
