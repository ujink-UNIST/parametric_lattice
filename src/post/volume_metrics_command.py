from __future__ import annotations

"""Volume-related post outputs.

Mirrors legacy :mod:`postprocess.volume_command`.

MAPDL outputs:
  - pp_volume_stress: ARRAY(6) sum over elements: Σ_e (S(e) * VOLU(e))
    ordering: [XX,YY,ZZ,YZ,XZ,XY] via ETABLE items
    NOTE: legacy uses [X,Y,Z,XY,YZ,XZ] in python, but ETABLE collection below
    matches legacy postprocess/volume_command.

  - pp_volume_energy: scalar sum over elements: Σ_e SENE(e)

Derived in Python:
  - volume_avg_stress = pp_volume_stress / pp_volume
  - volume_avg_energy = pp_volume_energy / pp_volume

For t_out:
  - volume_stress/volume_avg_stress use col=1..6 ordering [xx,yy,zz,yz,xz,xy]
  - volume_energy/volume_avg_energy use col=1
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl, apdl_command
from post.boundary_force_command import _SIM_TYPE_TO_ROW
from post.context import PostprocessContext
from post.row import TOutRow


# APDL Vector6 ordering in legacy postprocess.volume_command for pp_volume_stress:
# they build ETABLE: SX,SY,SZ,SYZ,SXZ,SXY then store into array(6) as [X,Y,Z,XY,YZ,XZ]
# Wait: in legacy build_volume_stress_commands_ they set pp_volume_stress(4)=SXY*VOLU,
# (5)=SYZ*VOLU, (6)=SXZ*VOLU.
# So pp_volume_stress indices: 1:XX, 2:YY, 3:ZZ, 4:XY, 5:YZ, 6:XZ.
# We map to t_out col ordering [xx,yy,zz,yz,xz,xy] => (1->1,2->2,3->3,5->4,6->5,4->6)
_COL_FROM_PP_INDEX: dict[int, int] = {1: 1, 2: 2, 3: 3, 5: 4, 6: 5, 4: 6}


def build_volume_stress_commands_(ctx: PostprocessContext) -> ApdlCommands:
    _ = ctx

    cmd: list[str] = [
        apdl_command("", "post: volume_stress (sum S*VOLU)"),
        apdl_command("ETABLE,pp__VOLU,VOLU", "element volume"),
        apdl_command("ETABLE,pp__SX,S,X", "stress XX"),
        apdl_command("ETABLE,pp__SY,S,Y", "stress YY"),
        apdl_command("ETABLE,pp__SZ,S,Z", "stress ZZ"),
        apdl_command("ETABLE,pp__SYZ,S,YZ", "stress YZ"),
        apdl_command("ETABLE,pp__SXZ,S,XZ", "stress XZ"),
        apdl_command("ETABLE,pp__SXY,S,XY", "stress XY"),
        apdl_command("*DIM,pp_volume_stress,ARRAY,6"),
        apdl_command("pp_volume_stress(1)=0"),
        apdl_command("pp_volume_stress(2)=0"),
        apdl_command("pp_volume_stress(3)=0"),
        apdl_command("pp_volume_stress(4)=0"),
        apdl_command("pp_volume_stress(5)=0"),
        apdl_command("pp_volume_stress(6)=0"),
        apdl_command("*GET,pp__eid,ELEM,0,NUM,MIN", "first selected element"),
        apdl_command("*DOWHILE,pp__eid,GT,0"),
        apdl_command("  *GET,pp__evol,ELEM,pp__eid,ETAB,pp__VOLU"),
        apdl_command("  *GET,pp__sx,ELEM,pp__eid,ETAB,pp__SX"),
        apdl_command("  *GET,pp__sy,ELEM,pp__eid,ETAB,pp__SY"),
        apdl_command("  *GET,pp__sz,ELEM,pp__eid,ETAB,pp__SZ"),
        apdl_command("  *GET,pp__syz,ELEM,pp__eid,ETAB,pp__SYZ"),
        apdl_command("  *GET,pp__sxz,ELEM,pp__eid,ETAB,pp__SXZ"),
        apdl_command("  *GET,pp__sxy,ELEM,pp__eid,ETAB,pp__SXY"),
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
    _ = ctx

    cmd: list[str] = [
        apdl_command("", "post: volume_energy (sum SENE)"),
        apdl_command("ETABLE,pp__SENE,SENE", "element strain energy"),
        apdl_command("pp_volume_energy=0", "init total strain energy"),
        apdl_command("*GET,pp__eid,ELEM,0,NUM,MIN", "first selected element"),
        apdl_command("*DOWHILE,pp__eid,GT,0"),
        apdl_command("  *GET,pp__esene,ELEM,pp__eid,ETAB,pp__SENE"),
        apdl_command("  pp_volume_energy=pp_volume_energy+pp__esene"),
        apdl_command("  *GET,pp__eid,ELEM,pp__eid,NXTH"),
        apdl_command("*ENDDO"),
        apdl_command("ALLSEL,ALL"),
    ]

    return tuple(cmd)


def _rows_from_vec6(
    *,
    case_index: int,
    case_hash: str,
    category: str,
    out_row: int,
    vec6: np.ndarray,
    unit: str,
) -> list[TOutRow]:
    rows: list[TOutRow] = []
    for pp_i1 in range(1, 7):
        col = _COL_FROM_PP_INDEX.get(pp_i1)
        if col is None:
            continue
        v = float(vec6[pp_i1 - 1])
        if not np.isfinite(v):
            continue
        rows.append(
            TOutRow(
                index=case_index,
                hash=case_hash,
                category=category,
                row=int(out_row),
                col=int(col),
                value=float(v),
                unit=unit,
            )
        )
    return rows


def extract_volume_stress_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "MPa*mm^3",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    try:
        raw = mapdl.parameters["pp_volume_stress"]
    except Exception:
        return []

    vec6 = np.asarray(raw, dtype=float).reshape(-1)
    if vec6.size != 6:
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    return _rows_from_vec6(
        case_index=case_index,
        case_hash=case_hash,
        category="stress.volume.sum",
        out_row=int(out_row),
        vec6=vec6,
        unit=unit,
    )


def extract_volume_avg_stress_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "MPa",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    try:
        raw = mapdl.parameters["pp_volume_stress"]
        vol = float(mapdl.parameters["pp_volume"])
    except Exception:
        return []

    vec6 = np.asarray(raw, dtype=float).reshape(-1)
    if vec6.size != 6 or vol == 0.0:
        return []

    avg6 = vec6 / vol

    case_index = int(ctx.sim_case.row_idx) + 1
    return _rows_from_vec6(
        case_index=case_index,
        case_hash=case_hash,
        category="stress.volume.avg",
        out_row=int(out_row),
        vec6=avg6,
        unit=unit,
    )


def extract_volume_energy_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mJ",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    try:
        e = float(mapdl.parameters["pp_volume_energy"])
    except Exception:
        return []

    if not np.isfinite(e):
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    return [
        TOutRow(
            index=case_index,
            hash=case_hash,
            category="energy.strain.total",
            row=int(out_row),
            col=1,
            value=float(e),
            unit=unit,
        )
    ]


def extract_volume_avg_energy_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mJ/mm^3",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    try:
        e = float(mapdl.parameters["pp_volume_energy"])
        vol = float(mapdl.parameters["pp_volume"])
    except Exception:
        return []

    if not np.isfinite(e) or vol == 0.0:
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    return [
        TOutRow(
            index=case_index,
            hash=case_hash,
            category="energy.strain_density.avg",
            row=int(out_row),
            col=1,
            value=float(e / vol),
            unit=unit,
        )
    ]
