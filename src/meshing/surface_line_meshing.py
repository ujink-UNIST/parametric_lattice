#surface_line_meshing.py
"""Surface line meshing command builders for solid unit-cell boundaries."""

from __future__ import annotations

from core.apdl_block import apdl_block, apdl_section
from core.apdl_commands import ApdlCommands
from core.parameters.geometry_params import GeometryParams
from core.parameters.meshing_params import MeshingParams
from core.parameters.profile_params import (
    BeamProfileParams,
    ProfileParams,
)
from meshing.surface_common import (
    Axis,
    Translation,
    half_sizes,
    surface_matching_tolerance,
    translation_from_axes,
)


def _surface_line_header_commands() -> ApdlCommands:
    """Return the top-level surface-line meshing header."""
    return (
        apdl_section("SURFACE LINE MESHING"),
        "! Mesh one source edge set on each boundary-edge family first.",
        "! Then copy that line mesh to the other matching edge sets.",
        "! Matching is based on line midpoints translated across the unit cell.",
        "ET,2,200,2",
        "TYPE,2",
    )


def _source_line_mesh_commands(
    a0: Axis,
    h0: float,
    a1: Axis,
    h1: float,
    eps: float,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    """Mesh the source edge family for one pair of boundary axes."""
    return (apdl_section(f"SOURCE LINE MESHING -{a0}/-{a1} EDGE"),) + apdl_block(
        f"""
! Select the source edge family at {a0}=-half and {a1}=-half.
! This edge is meshed once and reused for the translated edge copies.
NSRC=0
LSEL,S,LOC,{a0},{-h0-eps},{-h0+eps}
LSEL,R,LOC,{a1},{-h1-eps},{-h1+eps}
*GET,NSRC,LINE,0,COUNT
*IF,NSRC,GT,0,THEN
  ! Save the source line set before meshing because selections change later.
  CM,EDGE_SRC,LINE
  LESIZE,ALL,{meshing_params.max_element_size}
  LMESH,ALL
*ENDIF
ALLSEL
"""
    )


def _copy_line_mesh_commands(
    a0: Axis,
    h0: float,
    a1: Axis,
    h1: float,
    target_signs: tuple[int, int],
    translation: Translation,
    eps: float,
) -> ApdlCommands:
    """Copy the source line mesh to one translated target edge family."""
    s0, s1 = target_signs
    tx, ty, tz = translation

    return (
        apdl_section(f"COPY LINE MESH TO {s0:+d}{a0}/{s1:+d}{a1} EDGE"),
    ) + apdl_block(
        f"""
*IF,NSRC,GT,0,THEN
  ! Select candidate target lines on the translated boundary edge.
  NTGT=0
  LSEL,S,LOC,{a0},{s0*h0-eps},{s0*h0+eps}
  LSEL,R,LOC,{a1},{s1*h1-eps},{s1*h1+eps}
  *GET,NTGT,LINE,0,COUNT
  *IF,NTGT,GT,0,THEN
    ! Store target lines separately because the loop changes selection state.
    CM,EDGE_TGT,LINE
  *ENDIF
  ALLSEL

  *IF,NTGT,GT,0,THEN
    ! Create a mutable source-line work list.
    ! Each copied source line is removed so NUM,MIN advances deterministically.
    CM,_SRC_WORK_,LINE
    CMSEL,S,EDGE_SRC
    CM,_SRC_WORK_,LINE

    *DO,_II_,1,NSRC
      ! Pick the next source line from the work list.
      CMSEL,S,_SRC_WORK_
      *GET,_LSRC_,LINE,0,NUM,MIN

      ! Calculate the source line midpoint from its two keypoints.
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

      ! Find the unique target line whose midpoint equals the source midpoint
      ! translated by one cell length along the required axis or axes.
      CMSEL,S,EDGE_TGT
      LSEL,R,LOC,X,_XM_+{tx}-{eps:.16g},_XM_+{tx}+{eps:.16g}
      LSEL,R,LOC,Y,_YM_+{ty}-{eps:.16g},_YM_+{ty}+{eps:.16g}
      LSEL,R,LOC,Z,_ZM_+{tz}-{eps:.16g},_ZM_+{tz}+{eps:.16g}
      *GET,_NMATCH_,LINE,0,COUNT
      *IF,_NMATCH_,EQ,1,THEN
        ! Exactly one target was found, so copy the existing line mesh.
        *GET,_LTGT_,LINE,0,NUM,MIN
        ALLSEL
        MSHCOPY,LINE,_LSRC_,_LTGT_,0,{tx},{ty},{tz}
      *ELSE
        ! Keep solving possible, but report ambiguous or missing matches.
        /COM,WARNING: line match failed src=%_LSRC_% matched=%_NMATCH_%
      *ENDIF

      ! Remove the processed source and update the work component.
      CMSEL,S,_SRC_WORK_
      LSEL,U,LINE,,_LSRC_
      CM,_SRC_WORK_,LINE
      ALLSEL
    *ENDDO

    ! Delete temporary components for this target edge copy.
    CMDELE,_SRC_WORK_
    CMDELE,EDGE_TGT
  *ENDIF
*ENDIF
ALLSEL
"""
    )


def _cleanup_line_mesh_commands(a0: Axis, a1: Axis) -> ApdlCommands:
    """Delete temporary source-line components for one edge family."""
    return (apdl_section(f"CLEAN SURFACE LINE COMPONENTS {a0}/{a1}"),) + apdl_block(
        """
*IF,NSRC,GT,0,THEN
  ! Remove the source component before moving to the next edge family.
  CMDELE,EDGE_SRC
*ENDIF
ALLSEL
"""
    )


def _line_target_specs(
    a0: Axis,
    h0: float,
    a1: Axis,
    h1: float,
) -> tuple[tuple[tuple[int, int], Translation], ...]:
    """Return target edge signs and translations for one source edge family."""
    return (
        ((-1, 1), translation_from_axes({a1: 2 * h1})),
        ((1, -1), translation_from_axes({a0: 2 * h0})),
        ((1, 1), translation_from_axes({a0: 2 * h0, a1: 2 * h1})),
    )


def build_surface_line_meshing_commands_(
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    if isinstance(profile_params, BeamProfileParams):
        return ()

    eps = surface_matching_tolerance(geometry_params)
    hx, hy, hz = half_sizes(geometry_params)
    edge_families = (
        ("X", hx, "Y", hy),
        ("Y", hy, "Z", hz),
        ("Z", hz, "X", hx),
    )

    cmds: list[str] = list(_surface_line_header_commands())

    for a0, h0, a1, h1 in edge_families:
        cmds.extend(
            _source_line_mesh_commands(a0, h0, a1, h1, eps, meshing_params)
        )

        for target_signs, translation in _line_target_specs(a0, h0, a1, h1):
            cmds.extend(
                _copy_line_mesh_commands(
                    a0,
                    h0,
                    a1,
                    h1,
                    target_signs,
                    translation,
                    eps,
                )
            )

        cmds.extend(_cleanup_line_mesh_commands(a0, a1))

    return tuple(cmds)
