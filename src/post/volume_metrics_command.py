from __future__ import annotations

"""Volume-related post outputs.

Mirrors legacy :mod:`postprocess.volume_command`.

MAPDL outputs:
  - pp_volume_stress: ARRAY(6) sum over elements: Σ_e (S(e) * VOLU(e))
    ordering: [XX,YY,ZZ,YZ,XZ,XY] via ETABLE items
    NOTE: legacy uses [X,Y,Z,XY,YZ,XZ] in python, but ETABLE collection below
    matches legacy postprocess/volume_command.

  - pp_volume_energy: scalar sum over elements: Σ_e SENE(e)
  - pp_volume_energy_sq: scalar sum over elements: Σ_e SENE(e)^2
  - pp_volume_energy_count: number of selected elements with SENE
  - pp_volume_energy_elem: ARRAY of per-element strain energy SENE(e)
  - pp_volume_strain_density: ARRAY of per-element strain-energy density SENE(e)/VOLU(e)
  - pp_volume_strain_density_vol: ARRAY of corresponding element volume weights VOLU(e)

Derived in Python:
  - volume_avg_stress = pp_volume_stress / pp_volume
  - strain-density mean/std/median = volume-weighted statistics of SENE(e)/VOLU(e)
  - strain-density min/max/range = min/max/range of SENE(e)/VOLU(e)
  - strain-density p95/p99 = volume-weighted percentiles of SENE(e)/VOLU(e)
  - strain-density cv = weighted std / weighted mean
  - strain-density skewness/kurtosis = volume-weighted central moment statistics

For t_out:
  - volume_stress/volume_avg_stress use col=1..6 ordering [xx,yy,zz,yz,xz,xy]
  - energy.strain.total and energy.strain_density.* stats use col=1
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
        apdl_command("ETABLE,pp__VOLU,VOLU", "element volume"),
        apdl_command("pp_volume_energy=0", "init total strain energy"),
        apdl_command("pp_volume_energy_sq=0", "init sum of squared element strain energy"),
        apdl_command("pp_volume_energy_count=0", "init element energy count"),
        apdl_command("pp_volume_strain_density_count=0", "init valid strain-density count"),
        apdl_command("*GET,pp__nelem,ELEM,0,COUNT", "selected element count"),
        apdl_command("*DIM,pp_volume_energy_elem,ARRAY,pp__nelem"),
        apdl_command("*DIM,pp_volume_strain_density,ARRAY,pp__nelem"),
        apdl_command("*DIM,pp_volume_strain_density_vol,ARRAY,pp__nelem"),
        apdl_command("pp__i=0"),
        apdl_command("pp__j=0"),
        apdl_command("*GET,pp__eid,ELEM,0,NUM,MIN", "first selected element"),
        apdl_command("*DOWHILE,pp__eid,GT,0"),
        apdl_command("  *GET,pp__esene,ELEM,pp__eid,ETAB,pp__SENE"),
        apdl_command("  *GET,pp__evol,ELEM,pp__eid,ETAB,pp__VOLU"),
        apdl_command("  pp__i=pp__i+1"),
        apdl_command("  pp_volume_energy_elem(pp__i)=pp__esene"),
        apdl_command("  pp_volume_energy=pp_volume_energy+pp__esene"),
        apdl_command("  pp_volume_energy_sq=pp_volume_energy_sq+pp__esene*pp__esene"),
        apdl_command("  pp_volume_energy_count=pp_volume_energy_count+1"),
        apdl_command("  *IF,pp__evol,GT,0,THEN"),
        apdl_command("    pp__j=pp__j+1"),
        apdl_command("    pp_volume_strain_density(pp__j)=pp__esene/pp__evol"),
        apdl_command("    pp_volume_strain_density_vol(pp__j)=pp__evol"),
        apdl_command("    pp_volume_strain_density_count=pp_volume_strain_density_count+1"),
        apdl_command("  *ENDIF"),
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


def extract_reference_strain_density_rows(
    *,
    ctx: PostprocessContext,
    case_hash: str,
    unit: str = "mJ/mm^3",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    value = reference_strain_density(ctx)
    if not np.isfinite(value):
        return []

    return [
        TOutRow(
            index=int(ctx.sim_case.row_idx) + 1,
            hash=case_hash,
            category="energy.strain_density.reference",
            row=int(out_row),
            col=1,
            value=float(value),
            unit=unit,
        )
    ]


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


def _finite_values(values: np.ndarray) -> np.ndarray | None:
    values = np.asarray(values, dtype=float).reshape(-1)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return None
    return values


def _strain_density_count(mapdl: Mapdl, fallback: int) -> int:
    try:
        return max(int(float(mapdl.parameters["pp_volume_strain_density_count"])), 0)
    except Exception:
        return int(fallback)


def _strain_density_values_weights(mapdl: Mapdl) -> tuple[np.ndarray, np.ndarray] | None:
    try:
        raw_values = np.asarray(mapdl.parameters["pp_volume_strain_density"], dtype=float).reshape(-1)
        raw_weights = np.asarray(mapdl.parameters["pp_volume_strain_density_vol"], dtype=float).reshape(-1)
    except Exception:
        return None

    count = min(_strain_density_count(mapdl, raw_values.size), raw_values.size, raw_weights.size)
    values = raw_values[:count]
    weights = raw_weights[:count]
    mask = np.isfinite(values) & np.isfinite(weights) & (weights > 0.0)
    values = values[mask]
    weights = weights[mask]
    if values.size == 0:
        return None
    return values, weights


def extract_strain_density_array(mapdl: Mapdl) -> np.ndarray:
    """Return element-wise strain-energy density SENE/VOLU as a NumPy array.

    This is an intermediate Python output only. It is intentionally not emitted
    directly to t_out because element-wise values are mesh-size dependent.
    """

    pair = _strain_density_values_weights(mapdl)
    if pair is None:
        return np.asarray([], dtype=float)
    values, _weights = pair
    return values


def extract_strain_density_arrays(mapdl: Mapdl) -> tuple[np.ndarray, np.ndarray]:
    """Return (SENE/VOLU values, VOLU weights) as NumPy arrays."""

    pair = _strain_density_values_weights(mapdl)
    if pair is None:
        empty = np.asarray([], dtype=float)
        return empty, empty
    return pair


def reference_strain_density(ctx: PostprocessContext) -> float:
    """Return 0.5 * E * strain^2 in mJ/mm^3-compatible units."""

    e_mod = float(ctx.sim_case.post_mesh_spec.material.e_mod)
    strain = float(ctx.sim_case.post_mesh_spec.setup.strain)
    return float(0.5 * e_mod * strain * strain)


def extract_normalized_strain_density_array(
    ctx: PostprocessContext,
    mapdl: Mapdl,
) -> np.ndarray:
    """Return element-wise (SENE/VOLU) / (0.5*E*strain^2)."""

    values, _weights = extract_normalized_strain_density_arrays(ctx, mapdl)
    return values


def extract_normalized_strain_density_arrays(
    ctx: PostprocessContext,
    mapdl: Mapdl,
) -> tuple[np.ndarray, np.ndarray]:
    """Return normalized strain-density values and VOLU weights."""

    ref = reference_strain_density(ctx)
    if not np.isfinite(ref) or ref == 0.0:
        empty = np.asarray([], dtype=float)
        return empty, empty

    values, weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return values, weights
    out = values / ref
    mask = np.isfinite(out) & np.isfinite(weights) & (weights > 0.0)
    return out[mask].astype(float, copy=False), weights[mask].astype(float, copy=False)


def _weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.average(values, weights=weights))


def _weighted_std(values: np.ndarray, weights: np.ndarray) -> float:
    mean = _weighted_mean(values, weights)
    return float(np.sqrt(np.average((values - mean) ** 2, weights=weights)))


def _weighted_skewness(values: np.ndarray, weights: np.ndarray) -> float | None:
    mean = _weighted_mean(values, weights)
    centered = values - mean
    variance = float(np.average(centered**2, weights=weights))
    if variance <= 0.0:
        return None
    m3 = float(np.average(centered**3, weights=weights))
    return float(m3 / (variance ** 1.5))


def _weighted_kurtosis(values: np.ndarray, weights: np.ndarray) -> float | None:
    mean = _weighted_mean(values, weights)
    centered = values - mean
    variance = float(np.average(centered**2, weights=weights))
    if variance <= 0.0:
        return None
    m4 = float(np.average(centered**4, weights=weights))
    return float(m4 / (variance * variance))


def _weighted_percentile(values: np.ndarray, weights: np.ndarray, percentile: float) -> float:
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cutoff = (float(percentile) / 100.0) * float(np.sum(weights))
    idx = int(np.searchsorted(np.cumsum(weights), cutoff, side="left"))
    idx = min(max(idx, 0), values.size - 1)
    return float(values[idx])


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    return _weighted_percentile(values, weights, 50.0)


def _energy_stat_row(
    *,
    ctx: PostprocessContext,
    case_hash: str,
    category: str,
    value: float,
    unit: str,
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None or not np.isfinite(value):
        return []

    return [
        TOutRow(
            index=int(ctx.sim_case.row_idx) + 1,
            hash=case_hash,
            category=category,
            row=int(out_row),
            col=1,
            value=float(value),
            unit=unit,
        )
    ]


def extract_element_count_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "-",
) -> List[TOutRow]:
    try:
        count = float(mapdl.parameters["pp_volume_energy_count"])
    except Exception:
        values, _weights = extract_strain_density_arrays(mapdl)
        if values.size == 0:
            return []
        count = float(values.size)

    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="element.count",
        value=count,
        unit=unit,
    )


def extract_volume_mean_strain_density_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mJ/mm^3",
) -> List[TOutRow]:
    values, weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="energy.strain_density.mean",
        value=_weighted_mean(values, weights),
        unit=unit,
    )


def extract_volume_std_strain_density_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mJ/mm^3",
) -> List[TOutRow]:
    values, weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="energy.strain_density.std",
        value=_weighted_std(values, weights),
        unit=unit,
    )


def extract_volume_median_strain_density_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mJ/mm^3",
) -> List[TOutRow]:
    values, weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="energy.strain_density.median",
        value=_weighted_median(values, weights),
        unit=unit,
    )


def extract_volume_min_strain_density_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mJ/mm^3",
) -> List[TOutRow]:
    values, _weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="energy.strain_density.min",
        value=float(np.min(values)),
        unit=unit,
    )


def extract_volume_max_strain_density_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mJ/mm^3",
) -> List[TOutRow]:
    values, _weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="energy.strain_density.max",
        value=float(np.max(values)),
        unit=unit,
    )


def extract_volume_range_strain_density_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mJ/mm^3",
) -> List[TOutRow]:
    values, _weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="energy.strain_density.range",
        value=float(np.max(values) - np.min(values)),
        unit=unit,
    )


def extract_volume_p95_strain_density_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mJ/mm^3",
) -> List[TOutRow]:
    values, weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="energy.strain_density.p95",
        value=_weighted_percentile(values, weights, 95.0),
        unit=unit,
    )


def extract_volume_p99_strain_density_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mJ/mm^3",
) -> List[TOutRow]:
    values, weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="energy.strain_density.p99",
        value=_weighted_percentile(values, weights, 99.0),
        unit=unit,
    )


def extract_volume_cv_strain_density_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "-",
) -> List[TOutRow]:
    values, weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return []
    mean = _weighted_mean(values, weights)
    if mean == 0.0:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="energy.strain_density.cv",
        value=float(_weighted_std(values, weights) / mean),
        unit=unit,
    )


def extract_volume_skewness_strain_density_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "-",
) -> List[TOutRow]:
    values, weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return []
    skewness = _weighted_skewness(values, weights)
    if skewness is None:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="energy.strain_density.skewness",
        value=float(skewness),
        unit=unit,
    )


def extract_volume_kurtosis_strain_density_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "-",
) -> List[TOutRow]:
    values, weights = extract_strain_density_arrays(mapdl)
    if values.size == 0:
        return []
    kurtosis = _weighted_kurtosis(values, weights)
    if kurtosis is None:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category="energy.strain_density.kurtosis",
        value=float(kurtosis),
        unit=unit,
    )


def _normalized_density_stat_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    category: str,
    stat: str,
    unit: str = "-",
) -> List[TOutRow]:
    values, weights = extract_normalized_strain_density_arrays(ctx, mapdl)
    if values.size == 0:
        return []

    if stat == "mean":
        value: float | None = _weighted_mean(values, weights)
    elif stat == "std":
        value = _weighted_std(values, weights)
    elif stat == "median":
        value = _weighted_median(values, weights)
    elif stat == "min":
        value = float(np.min(values))
    elif stat == "max":
        value = float(np.max(values))
    elif stat == "range":
        value = float(np.max(values) - np.min(values))
    elif stat == "p95":
        value = _weighted_percentile(values, weights, 95.0)
    elif stat == "p99":
        value = _weighted_percentile(values, weights, 99.0)
    elif stat == "cv":
        mean = _weighted_mean(values, weights)
        value = None if mean == 0.0 else float(_weighted_std(values, weights) / mean)
    elif stat == "skewness":
        value = _weighted_skewness(values, weights)
    elif stat == "kurtosis":
        value = _weighted_kurtosis(values, weights)
    else:
        raise ValueError(f"Unknown normalized strain-density stat: {stat}")

    if value is None:
        return []
    return _energy_stat_row(
        ctx=ctx,
        case_hash=case_hash,
        category=category,
        value=float(value),
        unit=unit,
    )


def extract_volume_mean_normalized_strain_density_rows(*, ctx: PostprocessContext, mapdl: Mapdl, case_hash: str, unit: str = "-") -> List[TOutRow]:
    return _normalized_density_stat_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, category="energy.strain_density.normalized.mean", stat="mean", unit=unit)


def extract_volume_std_normalized_strain_density_rows(*, ctx: PostprocessContext, mapdl: Mapdl, case_hash: str, unit: str = "-") -> List[TOutRow]:
    return _normalized_density_stat_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, category="energy.strain_density.normalized.std", stat="std", unit=unit)


def extract_volume_median_normalized_strain_density_rows(*, ctx: PostprocessContext, mapdl: Mapdl, case_hash: str, unit: str = "-") -> List[TOutRow]:
    return _normalized_density_stat_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, category="energy.strain_density.normalized.median", stat="median", unit=unit)


def extract_volume_min_normalized_strain_density_rows(*, ctx: PostprocessContext, mapdl: Mapdl, case_hash: str, unit: str = "-") -> List[TOutRow]:
    return _normalized_density_stat_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, category="energy.strain_density.normalized.min", stat="min", unit=unit)


def extract_volume_max_normalized_strain_density_rows(*, ctx: PostprocessContext, mapdl: Mapdl, case_hash: str, unit: str = "-") -> List[TOutRow]:
    return _normalized_density_stat_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, category="energy.strain_density.normalized.max", stat="max", unit=unit)


def extract_volume_range_normalized_strain_density_rows(*, ctx: PostprocessContext, mapdl: Mapdl, case_hash: str, unit: str = "-") -> List[TOutRow]:
    return _normalized_density_stat_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, category="energy.strain_density.normalized.range", stat="range", unit=unit)


def extract_volume_p95_normalized_strain_density_rows(*, ctx: PostprocessContext, mapdl: Mapdl, case_hash: str, unit: str = "-") -> List[TOutRow]:
    return _normalized_density_stat_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, category="energy.strain_density.normalized.p95", stat="p95", unit=unit)


def extract_volume_p99_normalized_strain_density_rows(*, ctx: PostprocessContext, mapdl: Mapdl, case_hash: str, unit: str = "-") -> List[TOutRow]:
    return _normalized_density_stat_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, category="energy.strain_density.normalized.p99", stat="p99", unit=unit)


def extract_volume_cv_normalized_strain_density_rows(*, ctx: PostprocessContext, mapdl: Mapdl, case_hash: str, unit: str = "-") -> List[TOutRow]:
    return _normalized_density_stat_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, category="energy.strain_density.normalized.cv", stat="cv", unit=unit)


def extract_volume_skewness_normalized_strain_density_rows(*, ctx: PostprocessContext, mapdl: Mapdl, case_hash: str, unit: str = "-") -> List[TOutRow]:
    return _normalized_density_stat_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, category="energy.strain_density.normalized.skewness", stat="skewness", unit=unit)


def extract_volume_kurtosis_normalized_strain_density_rows(*, ctx: PostprocessContext, mapdl: Mapdl, case_hash: str, unit: str = "-") -> List[TOutRow]:
    return _normalized_density_stat_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, category="energy.strain_density.normalized.kurtosis", stat="kurtosis", unit=unit)
