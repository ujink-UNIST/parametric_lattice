#effective_bulk_modulus_command.py
"""Module for effective bulk modulus command functionality in src.post."""

from __future__ import annotations

"""Effective bulk modulus for sim_type=xyz.

We assume an isotropic volumetric strain loadcase with:
  eps_xx = eps_yy = eps_zz = eps (setup.strain)

Bulk modulus definition:
  K = p / eps_v
  p = (sxx + syy + szz) / 3
  eps_v = eps_xx + eps_yy + eps_zz = 3*eps

Dependencies:
  Requires `pp_boundary_stress` to exist (computed from boundary traction).

t_out:
  category = "effective_bulk_modulus"
  row = 7 (xyz)
  col = 1
  unit = MPa
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl
from post.boundary_force_command import _SIM_TYPE_TO_ROW
from post.context import PostprocessContext
from post.row import TOutRow


def build_effective_bulk_modulus_commands_(_: PostprocessContext) -> ApdlCommands:
    # Derived in Python; no MAPDL commands.
    return ()


def extract_effective_bulk_modulus_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "MPa",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    if sim_type != "xyz":
        return []

    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    eps = float(ctx.sim_case.post_mesh_spec.setup.strain)
    if eps == 0.0:
        return []

    try:
        raw = mapdl.parameters["pp_boundary_stress"]
    except Exception:
        return []

    s = np.asarray(raw, dtype=float).reshape(-1)
    if s.size < 3:
        return []

    sxx, syy, szz = float(s[0]), float(s[1]), float(s[2])
    if not (np.isfinite(sxx) and np.isfinite(syy) and np.isfinite(szz)):
        return []

    p = (sxx + syy + szz) / 3.0
    eps_v = 3.0 * eps
    K = p / eps_v
    if not np.isfinite(K):
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    return [
        TOutRow(
            index=case_index,
            hash=case_hash,
            category="modulus.effective.bulk",
            row=int(out_row),
            col=1,
            value=float(K),
            unit=unit,
        )
    ]
