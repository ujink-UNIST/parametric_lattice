# surface_meshing.py

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
    cmds.extend(["ET,2,200,2", "TYPE,2"])

    eps = np.linalg.norm(geometry_params.size) * 0.005
    hx, hy, hz = geometry_params.size / 2

    cmd_pairs = [
        ("X", hx, "Y", hy),
        ("Y", hy, "Z", hz),
        ("Z", hz, "X", hx),
    ]

    for a0, h0, a1, h1 in cmd_pairs:
        # Source 메시
        cmds.extend(apdl_block(f"""
NSRC=0
LSEL,S,LOC,{a0},{-h0-eps},{-h0+eps}
LSEL,R,LOC,{a1},{-h1-eps},{-h1+eps}
*GET,NSRC,LINE,0,COUNT
*IF,NSRC,GT,0,THEN
  CM,EDGE_SRC,LINE
  LESIZE,ALL,{meshing_params.max_element_size}
  LMESH,ALL
*ENDIF
ALLSEL
"""))

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

            cmds.extend(apdl_block(f"""
*IF,NSRC,GT,0,THEN
  NTGT=0
  LSEL,S,LOC,{a0},{s0*h0-eps},{s0*h0+eps}
  LSEL,R,LOC,{a1},{s1*h1-eps},{s1*h1+eps}
  *GET,NTGT,LINE,0,COUNT
  *IF,NTGT,GT,0,THEN
    CM,EDGE_TGT,LINE
  *ENDIF
  ALLSEL

  *IF,NTGT,GT,0,THEN
    CM,_SRC_WORK_,LINE  
    CMSEL,S,EDGE_SRC
    CM,_SRC_WORK_,LINE

    *DO,_II_,1,NSRC
      ! Source line 하나 꺼내기
      CMSEL,S,_SRC_WORK_
      *GET,_LSRC_,LINE,0,NUM,MIN

      ! Source midpoint 계산
      *GET,_KP1_,LINE,_LSRC_,KP,1
      *GET,_KP2_,LINE,_LSRC_,KP,2
      *GET,_X1_,KP,_KP1_,LOC,X
      *GET,_Y1_,KP,_KP1_,LOC,Y
      *GET,_Z1_,KP,_KP1_,LOC,Z
      *GET,_X2_,KP,_KP2_,LOC,X
      *GET,_Y2_,KP,_KP2_,LOC,Y
      *GET,_Z2_,KP,_KP2_,LOC,Z
      _XM_=(_X1_+_X2_)/2
      _YM_=(_Y1_+_Y2_)/2
      _ZM_=(_Z1_+_Z2_)/2

      ! Target에서 midpoint+translation으로 매칭
      CMSEL,S,EDGE_TGT
      LSEL,R,LOC,X,_XM_+{tx}-{eps:.16g},_XM_+{tx}+{eps:.16g}
      LSEL,R,LOC,Y,_YM_+{ty}-{eps:.16g},_YM_+{ty}+{eps:.16g}
      LSEL,R,LOC,Z,_ZM_+{tz}-{eps:.16g},_ZM_+{tz}+{eps:.16g}
      *GET,_NMATCH_,LINE,0,COUNT
      *IF,_NMATCH_,EQ,1,THEN
        *GET,_LTGT_,LINE,0,NUM,MIN
        ALLSEL
        MSHCOPY,LINE,_LSRC_,_LTGT_,0,{tx},{ty},{tz}
      *ELSE
        /COM,WARNING: line match failed src=%_LSRC_% matched=%_NMATCH_%
      *ENDIF

      ! 처리된 source 제거 후 컴포넌트 갱신
      CMSEL,S,_SRC_WORK_
      LSEL,U,LINE,,_LSRC_
      CM,_SRC_WORK_,LINE
      ALLSEL
    *ENDDO

    CMDELE,_SRC_WORK_
    CMDELE,EDGE_TGT
  *ENDIF
*ENDIF
ALLSEL
"""))

        cmds.extend(apdl_block("""
*IF,NSRC,GT,0,THEN
  CMDELE,EDGE_SRC
*ENDIF
ALLSEL
"""))

    return tuple(cmds)


def build_surface_area_meshing_commands_(
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    """Mesh one face (source) and copy to the opposite face by matching
    (area centroid) == (source centroid + translation).

    This mirrors the midpoint+translation matching strategy used in
    build_surface_line_meshing_commands_.
    """

    if isinstance(profile_params, BeamProfileParams):
        return ()

    cmds: list[str] = []
    cmds.extend(["ET,3,200,4", "TYPE,3"])

    eps = np.linalg.norm(geometry_params.size) * 0.005
    hx, hy, hz = geometry_params.size / 2

    face_pairs = [
        ("X", hx),
        ("Y", hy),
        ("Z", hz),
    ]

    for a0, h0 in face_pairs:
        # Source faces meshing
        cmds.extend(
            apdl_block(
                f"""
NSRC=0
ASEL,S,LOC,{a0},{-h0-eps},{-h0+eps}
*GET,NSRC,AREA,0,COUNT
*IF,NSRC,GT,0,THEN
  CM,FACE_SRC,AREA
  AESIZE,ALL,{meshing_params.max_element_size}
  AMESH,ALL
*ENDIF
ALLSEL
"""
            )
        )

        # Only opposite face copy (translation along a0)
        tx = ty = tz = 0.0
        if a0 == "X":
            tx = 2 * h0
        elif a0 == "Y":
            ty = 2 * h0
        elif a0 == "Z":
            tz = 2 * h0

        cmds.extend(
            apdl_block(
                f"""
*IF,NSRC,GT,0,THEN
  NTGT=0
  ASEL,S,LOC,{a0},{h0-eps},{h0+eps}
  *GET,NTGT,AREA,0,COUNT
  *IF,NTGT,GT,0,THEN
    CM,FACE_TGT,AREA
  *ENDIF
  ALLSEL

  *IF,NTGT,GT,0,THEN
    CM,_SRC_WORK_,AREA
    CMSEL,S,FACE_SRC
    CM,_SRC_WORK_,AREA

    *DO,_II_,1,NSRC
      ! Source area 하나 꺼내기
      CMSEL,S,_SRC_WORK_
      *GET,_ASRC_,AREA,0,NUM,MIN

      ! Source centroid 계산 (CENT는 ASUM 결과를 사용함)
      ASEL,S,AREA,,_ASRC_
      ASUM
      *GET,_XC_,AREA,0,CENT,X
      *GET,_YC_,AREA,0,CENT,Y
      *GET,_ZC_,AREA,0,CENT,Z

      ! Target에서 centroid+translation으로 매칭
      CMSEL,S,FACE_TGT
      ASEL,R,LOC,X,_XC_+{tx}-{eps:.16g},_XC_+{tx}+{eps:.16g}
      ASEL,R,LOC,Y,_YC_+{ty}-{eps:.16g},_YC_+{ty}+{eps:.16g}
      ASEL,R,LOC,Z,_ZC_+{tz}-{eps:.16g},_ZC_+{tz}+{eps:.16g}
      *GET,_NMATCH_,AREA,0,COUNT
      *IF,_NMATCH_,EQ,1,THEN
        *GET,_ATGT_,AREA,0,NUM,MIN
        ALLSEL
        MSHCOPY,AREA,_ASRC_,_ATGT_,0,{tx},{ty},{tz}
      *ELSE
        /COM,WARNING: area match failed src=%_ASRC_% matched=%_NMATCH_%
      *ENDIF

      ! 처리된 source 제거 후 컴포넌트 갱신
      CMSEL,S,_SRC_WORK_
      ASEL,U,AREA,,_ASRC_
      CM,_SRC_WORK_,AREA
      ALLSEL
    *ENDDO

    CMDELE,_SRC_WORK_
    CMDELE,FACE_TGT
  *ENDIF
*ENDIF
ALLSEL
"""
            )
        )

        cmds.extend(apdl_block("""
*IF,NSRC,GT,0,THEN
  CMDELE,FACE_SRC
*ENDIF
ALLSEL
"""))

    return tuple(cmds)
