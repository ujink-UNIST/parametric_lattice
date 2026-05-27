from __future__ import annotations

"""Modal outputs.

Mirrors legacy :mod:`postprocess.modal_command` behavior, but emits long-format
`t_out` records.

Row convention:
  row = mode index (1..20)

Col convention:
  - resonant frequency: col=1
  - participation factor (vector): col=1..3 -> X,Y,Z
  - effective modal mass (vector): col=1..3 -> X,Y,Z
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl, apdl_command
from post.context import PostprocessContext
from post.row import TOutRow


def build_resonant_frequency_command_(ctx: PostprocessContext, *, mode_index: int) -> ApdlCommands:
    _ = ctx

    i = int(mode_index)
    if i <= 0:
        raise ValueError("mode_index must be >= 1")

    return (
        apdl_command("", f"post: res_freq_{i}"),
        apdl_command(f"SET,1,{i}", "select mode"),
        apdl_command(f"*GET,pp_res_freq_{i},MODE,{i},FREQ", "mode frequency"),
        apdl_command("SET,LAST", "restore"),
    )


def build_modal_participation_commands_(ctx: PostprocessContext, *, mode_index: int) -> ApdlCommands:
    _ = ctx

    i = int(mode_index)
    if i <= 0:
        raise ValueError("mode_index must be >= 1")

    return (
        apdl_command("", f"post: part_factor_{i}"),
        apdl_command(f"SET,1,{i}", "select mode"),
        apdl_command(f"*GET,pp_part_factor_{i}_X,MODE,{i},PFACT,X", "PX"),
        apdl_command(f"*GET,pp_part_factor_{i}_Y,MODE,{i},PFACT,Y", "PY"),
        apdl_command(f"*GET,pp_part_factor_{i}_Z,MODE,{i},PFACT,Z", "PZ"),
        apdl_command("SET,LAST", "restore"),
    )


def build_modal_effective_mass_commands_(ctx: PostprocessContext, *, mode_index: int) -> ApdlCommands:
    _ = ctx

    i = int(mode_index)
    if i <= 0:
        raise ValueError("mode_index must be >= 1")

    return (
        apdl_command("", f"post: eff_modal_mass_{i}"),
        apdl_command(f"SET,1,{i}", "select mode"),
        apdl_command(f"*GET,pp_eff_modal_mass_{i}_X,MODE,{i},EFFM,X", "MX"),
        apdl_command(f"*GET,pp_eff_modal_mass_{i}_Y,MODE,{i},EFFM,Y", "MY"),
        apdl_command(f"*GET,pp_eff_modal_mass_{i}_Z,MODE,{i},EFFM,Z", "MZ"),
        apdl_command("SET,LAST", "restore"),
    )


def extract_resonant_frequency_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    mode_index: int,
    unit: str = "Hz",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    cat = "modal_ff.res_freq" if sim_type == "modal_ff" else "modal.res_freq"
    i = int(mode_index)
    try:
        f = float(mapdl.parameters[f"pp_res_freq_{i}"])
    except Exception:
        return []
    if not np.isfinite(f):
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    return [
        TOutRow(
            index=case_index,
            hash=case_hash,
            category=cat,
            row=i,
            col=1,
            value=float(f),
            unit=unit,
        )
    ]


def extract_participation_factor_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    mode_index: int,
    unit: str = "-",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    cat = "modal_ff.part_factor" if sim_type == "modal_ff" else "modal.part_factor"
    i = int(mode_index)
    try:
        x = float(mapdl.parameters[f"pp_part_factor_{i}_X"])
        y = float(mapdl.parameters[f"pp_part_factor_{i}_Y"])
        z = float(mapdl.parameters[f"pp_part_factor_{i}_Z"])
    except Exception:
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    out: list[TOutRow] = []
    for col, v in [(1, x), (2, y), (3, z)]:
        if not np.isfinite(v):
            continue
        out.append(
            TOutRow(
                index=case_index,
                hash=case_hash,
                category=cat,
                row=i,
                col=col,
                value=float(v),
                unit=unit,
            )
        )
    return out


def extract_effective_modal_mass_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    mode_index: int,
    unit: str = "kg",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    cat = "modal_ff.eff_modal_mass" if sim_type == "modal_ff" else "modal.eff_modal_mass"
    i = int(mode_index)
    try:
        x = float(mapdl.parameters[f"pp_eff_modal_mass_{i}_X"])
        y = float(mapdl.parameters[f"pp_eff_modal_mass_{i}_Y"])
        z = float(mapdl.parameters[f"pp_eff_modal_mass_{i}_Z"])
    except Exception:
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    out: list[TOutRow] = []
    for col, v in [(1, x), (2, y), (3, z)]:
        if not np.isfinite(v):
            continue
        out.append(
            TOutRow(
                index=case_index,
                hash=case_hash,
                category=cat,
                row=i,
                col=col,
                value=float(v),
                unit=unit,
            )
        )
    return out
