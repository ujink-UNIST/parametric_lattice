from __future__ import annotations

from core.apdl_commands import ApdlCommands, apdl_command
from postprocess.context import PostprocessContext


def build_volume_stress_commands_(ctx: PostprocessContext) -> ApdlCommands:
    """Compute volume-weighted stress sum Σ_e (S(e) * VOLU(e)).

    Output MAPDL parameters:
      - pp_volume_stress: ARRAY(6) with convention [X, Y, Z, XY, YZ, XZ]

    Notes:
      - Uses element stress items via ETABLE: S,X S,Y S,Z S,YZ S,XZ S,XY.
      - Uses element volume item via ETABLE: VOLU.
      - This returns the *sum* (not normalized by total volume).
    """

    _ = ctx

    cmd: list[str] = [
        apdl_command("", "postprocess: volume-weighted stress (sum S*VOLU)"),
        # Per-element quantities
        apdl_command("ETABLE,pp__VOLU,VOLU", "element volume"),
        apdl_command("ETABLE,pp__SX,S,X", "stress XX"),
        apdl_command("ETABLE,pp__SY,S,Y", "stress YY"),
        apdl_command("ETABLE,pp__SZ,S,Z", "stress ZZ"),
        apdl_command("ETABLE,pp__SYZ,S,YZ", "stress YZ"),
        apdl_command("ETABLE,pp__SXZ,S,XZ", "stress XZ"),
        apdl_command("ETABLE,pp__SXY,S,XY", "stress XY"),
        # Accumulate Σ (S * VOLU)
        apdl_command("*DIM,pp_volume_stress,ARRAY,6"),
        apdl_command("pp_volume_stress(1)=0"),
        apdl_command("pp_volume_stress(2)=0"),
        apdl_command("pp_volume_stress(3)=0"),
        apdl_command("pp_volume_stress(4)=0"),
        apdl_command("pp_volume_stress(5)=0"),
        apdl_command("pp_volume_stress(6)=0"),
        apdl_command("*GET,pp__eid,ELEM,0,NUM,MIN", "first selected element"),
        apdl_command("*DOWHILE,pp__eid,GT,0"),
        apdl_command("  *GET,pp__evol,ELEM,pp__eid,ETAB,pp__VOLU", "element volume"),
        apdl_command("  *GET,pp__sx,ELEM,pp__eid,ETAB,pp__SX", "XX"),
        apdl_command("  *GET,pp__sy,ELEM,pp__eid,ETAB,pp__SY", "YY"),
        apdl_command("  *GET,pp__sz,ELEM,pp__eid,ETAB,pp__SZ", "ZZ"),
        apdl_command("  *GET,pp__syz,ELEM,pp__eid,ETAB,pp__SYZ", "YZ"),
        apdl_command("  *GET,pp__sxz,ELEM,pp__eid,ETAB,pp__SXZ", "XZ"),
        apdl_command("  *GET,pp__sxy,ELEM,pp__eid,ETAB,pp__SXY", "XY"),
        apdl_command("  pp_volume_stress(1)=pp_volume_stress(1)+pp__sx*pp__evol"),
        apdl_command("  pp_volume_stress(2)=pp_volume_stress(2)+pp__sy*pp__evol"),
        apdl_command("  pp_volume_stress(3)=pp_volume_stress(3)+pp__sz*pp__evol"),
        apdl_command("  pp_volume_stress(4)=pp_volume_stress(4)+pp__sxy*pp__evol"),
        apdl_command("  pp_volume_stress(5)=pp_volume_stress(5)+pp__syz*pp__evol"),
        apdl_command("  pp_volume_stress(6)=pp_volume_stress(6)+pp__sxz*pp__evol"),
        apdl_command("  *GET,pp__eid,ELEM,pp__eid,NXTH"),
        apdl_command("*ENDDO"),
        apdl_command("ALLSEL,ALL"),
    ]

    return tuple(cmd)


def build_volume_energy_commands_(ctx: PostprocessContext) -> ApdlCommands:
    """Compute total strain energy (sum over elements).

    Output MAPDL parameters:
      - pp_volume_energy: scalar

    Notes:
      - Uses ETABLE item SENE (element strain energy).
      - Despite the name, this is an energy (not multiplied by volume).
        A natural derived quantity is energy density avg:
          volume_avg_energy = pp_volume_energy / pp_volume
    """

    _ = ctx

    cmd: list[str] = [
        apdl_command("", "postprocess: total strain energy"),
        apdl_command("ETABLE,pp__SENE,SENE", "element strain energy"),
        apdl_command("pp_volume_energy=0", "init total strain energy"),
        apdl_command("*GET,pp__eid,ELEM,0,NUM,MIN", "first selected element"),
        apdl_command("*DOWHILE,pp__eid,GT,0"),
        apdl_command("  *GET,pp__esene,ELEM,pp__eid,ETAB,pp__SENE", "element SENE"),
        apdl_command("  pp_volume_energy=pp_volume_energy+pp__esene", "accumulate"),
        apdl_command("  *GET,pp__eid,ELEM,pp__eid,NXTH"),
        apdl_command("*ENDDO"),
        apdl_command("ALLSEL,ALL"),
    ]

    return tuple(cmd)


def build_volume_commands_(ctx: PostprocessContext) -> ApdlCommands:
    """Compute total volume of all selected elements.

    Output MAPDL parameters:
      - pp_volume: scalar

    Notes:
      - Uses ETABLE item VOLU (element volume). This should work for solid
        elements and for element types where MAPDL reports VOLU.
    """

    _ = ctx

    cmd: list[str] = [
        apdl_command("", "postprocess: total volume"),
        apdl_command("ETABLE,pp__VOLU,VOLU", "element volume"),
        apdl_command("pp_volume=0", "init total volume"),
        apdl_command("*GET,pp__eid,ELEM,0,NUM,MIN", "first selected element"),
        apdl_command("*DOWHILE,pp__eid,GT,0"),
        apdl_command("  *GET,pp__evol,ELEM,pp__eid,ETAB,pp__VOLU", "element volume"),
        apdl_command("  pp_volume=pp_volume+pp__evol", "accumulate"),
        apdl_command("  *GET,pp__eid,ELEM,pp__eid,NXTH"),
        apdl_command("*ENDDO"),
        apdl_command("ALLSEL,ALL"),
    ]

    return tuple(cmd)
