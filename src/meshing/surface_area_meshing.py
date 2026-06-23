#surface_area_meshing.py
"""Surface area meshing command builders for solid unit-cell boundaries."""

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


def _surface_area_header_commands() -> ApdlCommands:
    """Return the top-level surface-area meshing header."""
    return (
        apdl_section("SURFACE AREA MESHING"),
        "! Mesh the negative boundary face first, then copy that mesh to",
        "! the matching positive face. Matching is based on area centroids",
        "! translated by one full cell length along the current axis.",
        "ET,3,200,4",
        "TYPE,3",
        "pp_touch_ax=0",
        "pp_touch_ay=0",
        "pp_touch_az=0",
    )


def _source_area_mesh_commands(
    axis: Axis,
    half_size: float,
    eps: float,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    """Mesh source areas on the negative face and record touch area."""
    axis_lower = axis.lower()

    return (apdl_section(f"SOURCE AREA MESHING -{axis} FACE"),) + apdl_block(
        f"""
! Select all geometric areas located on the negative {axis} boundary.
NSRC=0
ASEL,S,LOC,{axis},{-half_size-eps},{-half_size+eps}
*GET,NSRC,AREA,0,COUNT
*IF,NSRC,GT,0,THEN
  ! Record the total touch area for this boundary direction.
  ! ASUM updates AREA summary values used by the following *GET command.
  ASUM
  *GET,pp__touch_a{axis_lower},AREA,0,AREA
  pp_touch_a{axis_lower}=pp__touch_a{axis_lower}

  ! Save the selected source areas before meshing them.
  ! FACE_SRC is later used as the list of areas to copy from.
  CM,FACE_SRC,AREA
  AESIZE,ALL,{meshing_params.max_element_size}
  AMESH,ALL
*ENDIF
ALLSEL
"""
    )


def _copy_area_mesh_commands(
    axis: Axis,
    half_size: float,
    translation: Translation,
    eps: float,
) -> ApdlCommands:
    """Copy source area meshes to the positive face on one axis."""
    tx, ty, tz = translation

    return (apdl_section(f"COPY AREA MESH TO +{axis} FACE"),) + apdl_block(
        f"""
*IF,NSRC,GT,0,THEN
  ! Select all candidate target areas on the positive {axis} boundary.
  NTGT=0
  ASEL,S,LOC,{axis},{half_size-eps},{half_size+eps}
  *GET,NTGT,AREA,0,COUNT
  *IF,NTGT,GT,0,THEN
    ! Store target areas separately because the loop repeatedly changes selection.
    CM,FACE_TGT,AREA
  *ENDIF
  ALLSEL

  *IF,NTGT,GT,0,THEN
    ! Create a mutable work list of source areas.
    ! Each copied source is removed so NUM,MIN advances deterministically.
    CM,_SRC_WORK_,AREA
    CMSEL,S,FACE_SRC
    CM,_SRC_WORK_,AREA

    *DO,_II_,1,NSRC
      ! Pick the next source area from the work list.
      CMSEL,S,_SRC_WORK_
      *GET,_ASRC_,AREA,0,NUM,MIN

      ! Calculate the source centroid.
      ! ASUM refreshes centroid summary values for the currently selected area.
      ASEL,S,AREA,,_ASRC_
      ASUM
      *GET,_XC_,AREA,0,CENT,X
      *GET,_YC_,AREA,0,CENT,Y
      *GET,_ZC_,AREA,0,CENT,Z

      ! Find the unique target area whose centroid equals the source centroid
      ! translated by one full cell length along {axis}.
      CMSEL,S,FACE_TGT
      ASEL,R,LOC,X,_XC_+{tx}-{eps:.16g},_XC_+{tx}+{eps:.16g}
      ASEL,R,LOC,Y,_YC_+{ty}-{eps:.16g},_YC_+{ty}+{eps:.16g}
      ASEL,R,LOC,Z,_ZC_+{tz}-{eps:.16g},_ZC_+{tz}+{eps:.16g}
      *GET,_NMATCH_,AREA,0,COUNT
      *IF,_NMATCH_,EQ,1,THEN
        ! Exactly one target was found, so copy the existing source mesh.
        *GET,_ATGT_,AREA,0,NUM,MIN
        ALLSEL
        MSHCOPY,AREA,_ASRC_,_ATGT_,0,{tx},{ty},{tz}
      *ELSE
        ! Keep solving possible, but report ambiguous or missing matches.
        /COM,WARNING: area match failed src=%_ASRC_% matched=%_NMATCH_%
      *ENDIF

      ! Remove the processed source and update the work component.
      CMSEL,S,_SRC_WORK_
      ASEL,U,AREA,,_ASRC_
      CM,_SRC_WORK_,AREA
      ALLSEL
    *ENDDO

    ! Delete temporary components created for this axis.
    CMDELE,_SRC_WORK_
    CMDELE,FACE_TGT
  *ENDIF
*ENDIF
ALLSEL
"""
    )


def _cleanup_area_mesh_commands(axis: Axis) -> ApdlCommands:
    """Delete temporary source-area components for one face pair."""
    return (apdl_section(f"CLEAN SURFACE AREA COMPONENTS {axis}"),) + apdl_block(
        """
*IF,NSRC,GT,0,THEN
  ! Remove the source component before moving to the next face pair.
  CMDELE,FACE_SRC
*ENDIF
ALLSEL
"""
    )


def build_surface_area_meshing_commands_(
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    """Mesh negative source faces and copy them to opposite positive faces."""

    if isinstance(profile_params, BeamProfileParams):
        return ()

    eps = surface_matching_tolerance(geometry_params)
    hx, hy, hz = half_sizes(geometry_params)
    face_pairs = (
        ("X", hx),
        ("Y", hy),
        ("Z", hz),
    )

    cmds: list[str] = list(_surface_area_header_commands())

    for axis, half_size in face_pairs:
        cmds.extend(
            _source_area_mesh_commands(axis, half_size, eps, meshing_params)
        )
        cmds.extend(
            _copy_area_mesh_commands(
                axis,
                half_size,
                translation_from_axes({axis: 2 * half_size}),
                eps,
            )
        )
        cmds.extend(_cleanup_area_mesh_commands(axis))

    return tuple(cmds)
