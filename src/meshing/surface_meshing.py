# File: c:\Users\USER\Documents\parametric_lattice\src\meshing\beam_surface_meshing.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


"""Beam surface meshing command builders."""

from __future__ import annotations

import numpy as np

from core.apdl_block import apdl_block
from core.apdl_commands import ApdlCommands
from core.parameters.geometry_params import GeometryParams
from core.parameters.meshing_params import MeshingParams
from core.parameters.profile_params import (
    BeamProfileParams,
    ProfileParams,
)


def build_surface_line_meshing_commands_(
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    if isinstance(profile_params, BeamProfileParams):
        return ()

    cmds: list[str] = []
    cmds.extend(
        [
            "ET,2,200,2",
            "TYPE,2",
        ]
    )

    eps = np.linalg.norm(geometry_params.size) * 0.005
    hx, hy, hz = geometry_params.size / 2

    cmd_pairs = [
        ("X", hx, "Y", hy),
        ("Y", hy, "Z", hz),
        ("Z", hz, "X", hx),
    ]

    for a0, h0, a1, h1 in cmd_pairs:
        cmds.extend(
            apdl_block(
                f"""
LSEL,S,LOC,{a0},{-h0-eps},{-h0+eps}
LSEL,R,LOC,{a1},{-h1-eps},{-h1+eps}
CM,EDGE_SRC,LINE
CMSEL,S,EDGE_SRC
*GET,SRC_LINE,LINE,0,NUM,MIN
LESIZE,ALL,{meshing_params.max_element_size}
LMESH,ALL
"""
            )
        )

        targets = [
            ((-1, 1), {a1: 2 * h1}),
            ((1, -1), {a0: 2 * h0}),
            ((1, 1), {a0: 2 * h0, a1: 2 * h1}),
        ]

        for (s0, s1), trans_dict in targets:
            tx = ty = tz = 0.0
            if "X" in trans_dict:
                tx = trans_dict["X"]
            if "Y" in trans_dict:
                ty = trans_dict["Y"]
            if "Z" in trans_dict:
                tz = trans_dict["Z"]

            cmds.extend(
                apdl_block(
                    f"""
LSEL,S,LOC,{a0},{s0*h0-eps},{s0*h0+eps}
LSEL,R,LOC,{a1},{s1*h1-eps},{s1*h1+eps}
CM,EDGE_TGT,LINE
CMSEL,S,EDGE_TGT
*GET,TGT_LINE,LINE,0,NUM,MIN
ALLSEL
CMSEL,S,EDGE_SRC
CMSEL,A,EDGE_TGT
MSHCOPY,LINE,SRC_LINE,TGT_LINE,0,{tx},{ty},{tz}
CMDELE,EDGE_TGT
"""
                )
            )
        cmds.extend(
            [
                "CMDELE,EDGE_SRC",
                "ALLSEL",
            ]
        )

    return tuple(cmds)


def build_surface_area_meshing_commands_(
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    if isinstance(profile_params, BeamProfileParams):
        return ()
    cmds: list[str] = []
    cmds.extend(
        [
            "ET,3,200,4",
            "TYPE,3",
        ]
    )
    eps = np.linalg.norm(geometry_params.size) * 0.005
    hx, hy, hz = geometry_params.size / 2
    face_pairs = [
        ("X", hx, "Y", hy, "Z", hz),
        ("Y", hy, "Z", hz, "X", hx),
        ("Z", hz, "X", hx, "Y", hy),
    ]
    for a0, h0, a1, h1, a2, h2 in face_pairs:
        cmds.extend(
            apdl_block(
                f"""
ASEL,S,LOC,{a0},{-h0-eps},{-h0+eps}
CM,FACE_SRC,AREA
CMSEL,S,FACE_SRC
*GET,SRC_AREA,AREA,0,NUM,MIN
AESIZE,ALL,{meshing_params.max_element_size}
AMESH,ALL
"""
            )
        )
        targets = [
            (1, {a0: 2 * h0}),
        ]
        for sign, trans_dict in targets:
            tx = ty = tz = 0.0
            if "X" in trans_dict:
                tx = trans_dict["X"]
            if "Y" in trans_dict:
                ty = trans_dict["Y"]
            if "Z" in trans_dict:
                tz = trans_dict["Z"]
            cmds.extend(
                apdl_block(
                    f"""
ASEL,S,LOC,{a0},{sign*h0-eps},{sign*h0+eps}
CM,FACE_TGT,AREA
CMSEL,S,FACE_TGT
*GET,TGT_AREA,AREA,0,NUM,MIN
ALLSEL
CMSEL,S,FACE_SRC
CMSEL,A,FACE_TGT
MSHCOPY,AREA,SRC_AREA,TGT_AREA,0,{tx},{ty},{tz}
CMDELE,FACE_TGT
"""
                )
            )
        cmds.extend(
            [
                "CMDELE,FACE_SRC",
                "ALLSEL",
            ]
        )
    return tuple(cmds)
