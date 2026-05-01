"""Element energy density extraction from MAPDL POST1 element tables."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, NamedTuple, Optional, Tuple

from core.types_ import SimCase
from results.apdl_utils import run_commands


def _parse_element_energy_density_csv(
    path: Path,
) -> Dict[Tuple[float, float, float], float]:
    """Parse an element energy density CSV written by MAPDL *VWRITE.

    Expected header: x,y,z,sene,volu,energy_density
    Returns a dict keyed by element centroid (x, y, z).
    """
    densities: Dict[Tuple[float, float, float], float] = {}
    if not path.exists():
        return densities

    def _to_float(value: str) -> float:
        return float(value.strip().replace("D", "E").replace("d", "e"))

    header = None
    energy_density_idx = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue

        parts = tuple(p.strip() for p in line.split(","))
        if header is None and parts and parts[0].lower() == "x":
            header = tuple(p.lower() for p in parts)
            if "energy_density" in header:
                energy_density_idx = header.index("energy_density")
            elif "ed" in header:
                energy_density_idx = header.index("ed")
            continue

        try:
            cx = _to_float(parts[0])
            cy = _to_float(parts[1])
            cz = _to_float(parts[2])
            if energy_density_idx is not None and energy_density_idx < len(parts):
                edens = _to_float(parts[energy_density_idx])
            elif len(parts) >= 6:
                edens = _to_float(parts[5])
            elif len(parts) >= 4:
                edens = _to_float(parts[3])
            else:
                continue
        except Exception:
            continue
        densities[(cx, cy, cz)] = edens
    return densities


def extract_element_energy_density(
    mapdl,
    sim_case: SimCase,
    *,
    out_path: Optional[Path] = None,
    log_path: Optional[Path] = None,
) -> Dict[Tuple[float, float, float], float]:
    """Export and return element-wise strain-energy density for the active result set.

    We use POST1 element tables:
    - SENE: strain energy per element
    - VOLU: element volume (for BEAM elements this is typically an equivalent volume A*L)
    """
    if out_path is None:
        return {}

    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the CSV header from Python to avoid ANSYS *VWRITE string-width issues.
    out_path.write_text("x,y,z,sene,volu,energy_density\n", encoding="utf-8")

    # APDL *CFOPEN uses (fname, ext, dir). Provide a stable location + name.
    fname = out_path.with_suffix("").name
    ext = out_path.suffix.lstrip(".") or "csv"
    directory = str(out_path.parent).replace("\\", "/")

    cmds = (
        "! ---- element energy density export (POST1) ----",
        "ALLSEL,ALL",
        "ESEL,ALL",
        "ETABLE,SE_val,SENE",
        "ETABLE,EVOL,VOLU",
        "PRETAB,EVOL",
        "*GET,NEL,ELEM,0,COUNT",
        f"*CFOPEN,'{fname}','{ext}','{directory}',APPEND",
        "*GET,EID,ELEM,0,NUM,MIN",
        "*DO,II,1,NEL",
        "  *GET,SE,ELEM,EID,ETAB,SE_val",
        "  *GET,VO,ELEM,EID,ETAB,EVOL",
        "  *GET,CX,ELEM,EID,CENT,X",
        "  *GET,CY,ELEM,EID,CENT,Y",
        "  *GET,CZ,ELEM,EID,CENT,Z",
        "  *IF,VO,GT,0,THEN",
        "    ED=SE/VO",
        "  *ELSE",
        "    ED=0",
        "  *ENDIF",
        "  *VWRITE,CX,CY,CZ,SE,VO,ED",
        "(E20.12,',',E20.12,',',E20.12,',',E20.12,',',E20.12,',',E20.12)",
        "  *IF,II,LT,NEL,THEN",
        "    ESEL,U,ELEM,,EID,EID",
        "    *GET,EID,ELEM,0,NUM,MIN",
        "  *ENDIF",
        "*ENDDO",
        "*CFCLSE",
        "ALLSEL,ALL",
        "! ---- end element energy density export ----",
    )
    run_commands(mapdl, cmds, log_path=log_path)
    densities = _parse_element_energy_density_csv(out_path)
    print(
        f"[energy_extractor] element_energy_density exported: "
        f"model={sim_case.model} count={len(densities)} path={out_path}"
    )
    return densities


class EnergyDensityStats(NamedTuple):
    """Descriptive statistics of element-wise energy metric.

    ``valid_count`` means the number of valid elements used in the moment calculation
    (finite SENE and finite, strictly-positive VOLU).
    """

    mean: float
    variance: float
    skewness: float
    kurtosis: float
    valid_count: int


def summarize_energy_density(
    densities: Dict[Tuple[float, float, float], float],
) -> EnergyDensityStats:
    """Compute ED summary stats from parsed element-wise energy density values."""
    values = [float(v) for v in densities.values()]
    n = len(values)
    if n == 0:
        return EnergyDensityStats(
            mean=0.0,
            variance=0.0,
            skewness=0.0,
            kurtosis=0.0,
            valid_count=0,
        )

    mean = sum(values) / n
    centered = [v - mean for v in values]
    m2 = sum(c * c for c in centered) / n
    if m2 <= 0.0:
        return EnergyDensityStats(
            mean=mean,
            variance=0.0,
            skewness=0.0,
            kurtosis=0.0,
            valid_count=n,
        )

    m3 = sum(c * c * c for c in centered) / n
    m4 = sum(c * c * c * c for c in centered) / n
    sigma = math.sqrt(m2)
    skewness = m3 / (sigma**3)
    kurtosis = (m4 / (m2 * m2)) - 3.0  # excess kurtosis (Fisher)
    return EnergyDensityStats(
        mean=mean,
        variance=m2,
        skewness=skewness,
        kurtosis=kurtosis,
        valid_count=n,
    )


def compute_energy_density_stats(mapdl, sim_case: SimCase) -> EnergyDensityStats:
    """Compute ED statistics with explicit valid-element count semantics.

    ``valid_count`` is the number of valid elements used in the moments:
    finite SENE and finite, strictly-positive VOLU.
    """
    import numpy as np

    run_commands(
        mapdl,
        (
            "ALLSEL,ALL",
            "ESEL,ALL",
            "ETABLE,SE_val,SENE",
            "ETABLE,EVOL,VOLU",
        ),
    )

    se_arr = np.asarray(mapdl.get_array("ELEM", item1="ETAB", it1num="SE_val"), dtype=float)
    vol_arr = np.asarray(mapdl.get_array("ELEM", item1="ETAB", it1num="EVOL"), dtype=float)

    n_total = int(se_arr.size)
    valid_mask = np.isfinite(se_arr) & np.isfinite(vol_arr) & (vol_arr > 0)
    n_valid = int(np.count_nonzero(valid_mask))

    if n_valid == 0:
        print(
            f"[energy_extractor] stats model={sim_case.model} total={n_total} valid=0 -> zeros"
        )
        return EnergyDensityStats(mean=0.0, variance=0.0, skewness=0.0, kurtosis=0.0, valid_count=0)

    se = se_arr[valid_mask]
    vol = vol_arr[valid_mask]
    ed = se / vol

    # Volume-weighted moments on ED.
    w = vol / vol.sum()
    mean = float(np.sum(w * ed))  # equals SENE_total / V_total
    centered = ed - mean
    m2 = float(np.sum(w * centered**2))

    if m2 <= 0.0:
        print(
            f"[energy_extractor] stats model={sim_case.model} total={n_total} valid={n_valid} "
            "variance~0"
        )
        return EnergyDensityStats(mean=mean, variance=0.0, skewness=0.0, kurtosis=0.0, valid_count=n_valid)

    sigma = math.sqrt(m2)
    skewness = float(np.sum(w * (centered / sigma) ** 3))
    kurtosis = float(np.sum(w * (centered / sigma) ** 4)) - 3.0

    return EnergyDensityStats(
        mean=mean,
        variance=m2,
        skewness=skewness,
        kurtosis=kurtosis,
        valid_count=n_valid,
    )
