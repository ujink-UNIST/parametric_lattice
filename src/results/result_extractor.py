"""Orchestrator: extracts reaction forces and stresses from MAPDL results."""

from __future__ import annotations

import math
from typing import Dict, Tuple

from core.types_ import SimCase, SimResult, StressTensor9, UnitCell
from geometry import face_area
from geometry.solid_geometry import OPPOSITE_FACE, POSITIVE_FACES
from io_utils import apdl_io
from results.energy_extractor import compute_energy_density_stats
from results.force_extractor import extract_face_forces
from results.stress_math import (
    average_force,
    check_force_balance,
    compute_stress_tensor,
    compute_traction,
)

_RIGID_BODY_MODE_COUNT = 6
_MAX_MODAL_SCAN_MODES = 256


def _normalize_frequency_values(values) -> Tuple[float, ...]:
    freqs = []
    for value in values:
        try:
            freq = float(value)
        except Exception:
            continue
        if math.isfinite(freq):
            freqs.append(freq)
    return tuple(freqs)


def _extract_modal_frequencies(
    mapdl,
    *,
    rigid_body_mode_count: int = _RIGID_BODY_MODE_COUNT,
) -> Dict[str, float]:
    """Extract modal frequencies and drop the first rigid-body modes."""
    freqs: Tuple[float, ...] = tuple()

    try:
        post = getattr(mapdl, "post_processing", None)
        raw = getattr(post, "frequency_values", None) if post is not None else None
        if raw is None and post is not None:
            raw = getattr(post, "frequencies", None)
        if raw is not None:
            freqs = _normalize_frequency_values(raw() if callable(raw) else raw)
    except Exception:
        freqs = tuple()

    if not freqs:
        try:
            raw = mapdl.get_array("MODE", item1="FREQ")
            freqs = _normalize_frequency_values(raw if raw is not None else ())
        except Exception:
            freqs = tuple()

    if not freqs:
        scanned = []
        for mode_idx in range(1, _MAX_MODAL_SCAN_MODES + 1):
            try:
                value = mapdl.get("FREQ", "MODE", mode_idx, "FREQ")
                scanned.append(value)
            except Exception:
                break
        freqs = _normalize_frequency_values(scanned)

    physical = freqs[rigid_body_mode_count:] if len(freqs) > rigid_body_mode_count else tuple()
    return {f"freq_{idx}": freq for idx, freq in enumerate(physical, start=1)}


def _compute_stiffness_terms(
    stress,
    strain: float,
    e_mod: float,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Return stiffness and relative-stiffness components derived from stress."""
    eps = 1e-12
    if abs(strain) <= eps:
        return {}, {}

    stress_components = {
        "xx": stress.xx,
        "yy": stress.yy,
        "zz": stress.zz,
        "xy": 0.5 * (stress.xy + stress.yx),
        "yz": 0.5 * (stress.yz + stress.zy),
        "zx": 0.5 * (stress.zx + stress.xz),
    }
    stiffness = {k: (v / strain) for k, v in stress_components.items()}
    if abs(e_mod) <= eps:
        return stiffness, {}
    relative = {k: (v / e_mod) for k, v in stiffness.items()}
    return stiffness, relative


def _compute_density_terms(
    mapdl,
    unit_cell: UnitCell,
    material_density: float,
    model: str,
) -> Tuple[float | None, float | None]:
    """Return (effective density, relative density) from element volumes."""
    def _fallback_from_geometry() -> Tuple[float | None, float | None]:
        try:
            lx, ly, lz = unit_cell.size
            cell_volume = float(lx * ly * lz)
            if cell_volume <= 0.0:
                return (None, None)

            upper_model = model.strip().upper()
            # Beam models have exact strut diameters and node coordinates in unit_cell.
            # Use geometric strut volumes when ETABLE/VOLU is unavailable in modal POST1.
            if upper_model.startswith("BEAM"):
                lattice_volume = 0.0
                for n1, n2, diameter in unit_cell.edges:
                    p1 = unit_cell.nodes[int(n1)]
                    p2 = unit_cell.nodes[int(n2)]
                    dx = float(p2[0] - p1[0])
                    dy = float(p2[1] - p1[1])
                    dz = float(p2[2] - p1[2])
                    length = math.sqrt(dx * dx + dy * dy + dz * dz)
                    radius = 0.5 * float(diameter)
                    area = math.pi * radius * radius
                    lattice_volume += area * length
                relative_density = lattice_volume / cell_volume
                effective_density = float(material_density) * relative_density
                return (effective_density, relative_density)
        except Exception:
            return (None, None)
        return (None, None)

    try:
        import numpy as np

        mapdl.run("ALLSEL,ALL")
        mapdl.run("ESEL,ALL")
        mapdl.run("ETABLE,EVOL,VOLU")
        raw = mapdl.get_array("ELEM", item1="ETAB", it1num="EVOL")
        if raw is None:
            return _fallback_from_geometry()
        vol_arr = np.asarray(raw, dtype=float)
        if vol_arr.size == 0:
            return _fallback_from_geometry()
        valid = np.isfinite(vol_arr) & (vol_arr > 0.0)
        lattice_volume = float(np.sum(vol_arr[valid]))
        lx, ly, lz = unit_cell.size
        cell_volume = float(lx * ly * lz)
        if cell_volume <= 0.0:
            return (None, None)
        relative_density = lattice_volume / cell_volume
        effective_density = float(material_density) * relative_density
        return (effective_density, relative_density)
    except Exception:
        return _fallback_from_geometry()


def _characteristic_length(unit_cell: UnitCell) -> float | None:
    """Return characteristic unit-cell length (geometric mean)."""
    lx, ly, lz = unit_cell.size
    if lx <= 0.0 or ly <= 0.0 or lz <= 0.0:
        return None
    return (lx * ly * lz) ** (1.0 / 3.0)


def _compute_relative_modal_frequencies(
    modal_frequencies: Dict[str, float],
    *,
    length_scale: float | None,
    material_density: float,
    elastic_modulus: float,
    relative_density: float | None,
) -> Dict[str, float]:
    """Compute normalized modal frequencies using user-defined scaling."""
    eps = 1e-30
    if (
        not modal_frequencies
        or length_scale is None
        or length_scale <= 0.0
        or material_density <= eps
        or elastic_modulus <= eps
        or relative_density is None
        or relative_density <= eps
    ):
        return {}

    def _mode_index(item: Tuple[str, float]) -> int:
        key = item[0]
        try:
            return int(key.split("_", 1)[1])
        except Exception:
            return 0

    factor = length_scale * math.sqrt(material_density / elastic_modulus) / math.sqrt(relative_density)
    rel: Dict[str, float] = {}
    for key, freq_hz in sorted(modal_frequencies.items(), key=_mode_index):
        omega = 2.0 * math.pi * float(freq_hz)  # Hz -> rad/s
        idx = _mode_index((key, freq_hz))
        if idx <= 0:
            continue
        rel[f"relative_freq_{idx}"] = omega * factor
    return rel


def extract_results(
    mapdl,
    sim_case: SimCase,
    unit_cell: UnitCell,
    *,
    elastic_modulus: float,
    material_density: float = 7.85e-9,
) -> SimResult:
    """Extract the final-step reactions and homogenized stress tensor."""
    try:
        print(
            f"[result_extractor] Start extraction for "
            f"cell={sim_case.cell_name!r}, model={sim_case.model}, row_idx={sim_case.row_idx}"
        )
        apdl_io.enter_post1(mapdl)
        apdl_io.set_last_result(mapdl)
        density, relative_density = _compute_density_terms(
            mapdl,
            unit_cell,
            material_density,
            sim_case.model,
        )

        sim_type = sim_case.sim_type.strip().lower()
        if sim_type.startswith("modal"):
            modal_frequencies = _extract_modal_frequencies(mapdl)
            relative_modal_frequencies = _compute_relative_modal_frequencies(
                modal_frequencies,
                length_scale=_characteristic_length(unit_cell),
                material_density=material_density,
                elastic_modulus=elastic_modulus,
                relative_density=relative_density,
            )
            return SimResult(
                sim_case=sim_case,
                stress=StressTensor9(),
                reaction_forces={},
                status="DONE",
                density=density,
                relative_density=relative_density,
                modal_frequencies=modal_frequencies,
                relative_modal_frequencies=relative_modal_frequencies,
            )

        element_energy_density: Dict = {}
        energy_density_stats = None
        try:
            energy_density_stats = compute_energy_density_stats(mapdl, sim_case)
        except Exception as exc:
            print(f"[result_extractor] element energy density stats skipped: {exc}")

        face_forces = extract_face_forces(mapdl, sim_case.model, unit_cell)

        face_tractions = {}
        for pos_face in POSITIVE_FACES:
            neg_face = OPPOSITE_FACE[pos_face]
            avg_force = average_force(face_forces[neg_face], face_forces[pos_face])
            area = face_area(unit_cell.size, pos_face)
            face_tractions[pos_face] = compute_traction(avg_force, area)

        stress = compute_stress_tensor(face_tractions)
        stiffness, relative_stiffness = _compute_stiffness_terms(
            stress,
            strain=sim_case.strain,
            e_mod=elastic_modulus,
        )
        force_balance = check_force_balance(face_forces)
        imbalance = max(force_balance.values()) if force_balance else None
        return SimResult(
            sim_case=sim_case,
            stress=stress,
            reaction_forces=face_forces,
            status="DONE",
            element_energy_density=element_energy_density,
            energy_density_stats=energy_density_stats,
            stiffness=stiffness,
            relative_stiffness=relative_stiffness,
            density=density,
            relative_density=relative_density,
            modal_frequencies={},
            relative_modal_frequencies={},
            imbalance=imbalance,
        )
    except Exception as exc:
        print(f"[result_extractor] Extraction failed: {exc}")
        return SimResult(
            sim_case=sim_case,
            stress=StressTensor9(),
            reaction_forces={},
            status="ERROR",
            error_msg=str(exc),
            element_energy_density={},
        )
