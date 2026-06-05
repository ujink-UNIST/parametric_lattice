#extract.py
"""Module for extract functionality in src.custom_io.post."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from post.boundary_force_command import extract_boundary_force_rows
from post.boundary_moment_command import extract_boundary_moment_rows
from post.boundary_traction_command import extract_boundary_traction_rows
from post.boundary_stress_command import extract_boundary_stress_rows
from post.boundary_modulus_command import extract_boundary_modulus_rows
from post.boundary_modulus_ratio_command import extract_boundary_modulus_ratio_rows
from post.boundary_touch_area_command import extract_boundary_touch_area_rows
from post.boundary_touch_area_ratio_command import extract_boundary_touch_area_ratio_rows
from post.contact_command import extract_contact_stress_rows, extract_contact_traction_rows
from post.effective_bulk_modulus_command import extract_effective_bulk_modulus_rows
from post.effective_moduli_command import (
    extract_effective_shear_modulus_rows,
    extract_effective_youngs_modulus_rows,
)
from post.effective_moduli_ratio_command import (
    extract_effective_shear_modulus_ratio_rows,
    extract_effective_youngs_modulus_ratio_rows,
)
from post.mass_command import extract_mass_rows
from post.modal_command import (
    extract_effective_modal_mass_rows,
    extract_participation_factor_rows,
    extract_resonant_frequency_rows,
)
from post.specific_moduli_command import (
    extract_specific_shear_modulus_rows,
    extract_specific_youngs_modulus_rows,
)
from post.volume_command import extract_volume_rows
from post.volume_fraction_command import extract_volume_fraction_rows
from post.volume_metrics_command import (
    extract_element_count_rows,
    extract_reference_strain_density_rows,
    extract_volume_avg_stress_rows,
    extract_volume_cv_normalized_strain_density_rows,
    extract_volume_cv_strain_density_rows,
    extract_volume_energy_rows,
    extract_volume_kurtosis_normalized_strain_density_rows,
    extract_volume_kurtosis_strain_density_rows,
    extract_volume_max_normalized_strain_density_rows,
    extract_volume_max_strain_density_rows,
    extract_volume_mean_normalized_strain_density_rows,
    extract_volume_mean_strain_density_rows,
    extract_volume_median_normalized_strain_density_rows,
    extract_volume_median_strain_density_rows,
    extract_volume_min_normalized_strain_density_rows,
    extract_volume_min_strain_density_rows,
    extract_volume_p95_normalized_strain_density_rows,
    extract_volume_p95_strain_density_rows,
    extract_volume_p99_normalized_strain_density_rows,
    extract_volume_p99_strain_density_rows,
    extract_volume_range_normalized_strain_density_rows,
    extract_volume_range_strain_density_rows,
    extract_volume_skewness_normalized_strain_density_rows,
    extract_volume_skewness_strain_density_rows,
    extract_volume_std_normalized_strain_density_rows,
    extract_volume_std_strain_density_rows,
    extract_volume_stress_rows,
)


@dataclass(frozen=True)
class ExtractorSpec:
    """Configuration for one postprocess row extractor.

    Parameters
    ----------
    func : Callable[..., Any]
        Function that extracts rows for a postprocess output prefix.
    unit : str
        Unit string passed to the extractor and written to output rows.
    needs_mapdl : bool, optional
        Whether the extractor requires a ``mapdl`` keyword argument.
    extra_kwargs : dict[str, Any], optional
        Additional keyword arguments passed to the extractor.
    """

    func: Callable[..., Any]
    unit: str
    needs_mapdl: bool = True
    extra_kwargs: dict[str, Any] = field(default_factory=dict)


STATIC_EXTRACTORS: dict[str, ExtractorSpec] = {
    "force.boundary.value": ExtractorSpec(extract_boundary_force_rows, "N"),
    "moment.boundary.value": ExtractorSpec(extract_boundary_moment_rows, "N*mm"),
    "traction.boundary.value": ExtractorSpec(extract_boundary_traction_rows, "MPa"),
    "stress.boundary.value": ExtractorSpec(extract_boundary_stress_rows, "MPa"),
    "modulus.boundary.value": ExtractorSpec(extract_boundary_modulus_rows, "MPa"),
    "modulus.boundary.ratio": ExtractorSpec(extract_boundary_modulus_ratio_rows, "-"),
    "modulus.effective.youngs": ExtractorSpec(extract_effective_youngs_modulus_rows, "MPa"),
    "modulus.effective.shear": ExtractorSpec(extract_effective_shear_modulus_rows, "MPa"),
    "modulus.effective.bulk": ExtractorSpec(extract_effective_bulk_modulus_rows, "MPa"),
    "modulus.effective.youngs.ratio": ExtractorSpec(extract_effective_youngs_modulus_ratio_rows, "-"),
    "modulus.effective.shear.ratio": ExtractorSpec(extract_effective_shear_modulus_ratio_rows, "-"),
    "modulus.effective.youngs.specific": ExtractorSpec(extract_specific_youngs_modulus_rows, "mm^2/s^2"),
    "modulus.effective.shear.specific": ExtractorSpec(extract_specific_shear_modulus_rows, "mm^2/s^2"),
    "area.boundary_contact.value": ExtractorSpec(extract_boundary_touch_area_rows, "mm^2"),
    "area.boundary_contact.ratio": ExtractorSpec(extract_boundary_touch_area_ratio_rows, "-"),
    "traction.contact.value": ExtractorSpec(extract_contact_traction_rows, "MPa"),
    "stress.contact.value": ExtractorSpec(extract_contact_stress_rows, "MPa"),
    "volume.solid.value": ExtractorSpec(extract_volume_rows, "mm^3"),
    "mass.solid.value": ExtractorSpec(extract_mass_rows, "kg"),
    "volume_fraction.cell.value": ExtractorSpec(extract_volume_fraction_rows, "-"),
    "stress.volume.sum": ExtractorSpec(extract_volume_stress_rows, "MPa*mm^3"),
    "stress.volume.avg": ExtractorSpec(extract_volume_avg_stress_rows, "MPa"),
    "energy.strain.total": ExtractorSpec(extract_volume_energy_rows, "mJ"),
    "element.count": ExtractorSpec(extract_element_count_rows, "-"),
    "energy.strain_density.reference": ExtractorSpec(extract_reference_strain_density_rows, "mJ/mm^3", needs_mapdl=False),
    "energy.strain_density.mean": ExtractorSpec(extract_volume_mean_strain_density_rows, "mJ/mm^3"),
    "energy.strain_density.std": ExtractorSpec(extract_volume_std_strain_density_rows, "mJ/mm^3"),
    "energy.strain_density.median": ExtractorSpec(extract_volume_median_strain_density_rows, "mJ/mm^3"),
    "energy.strain_density.min": ExtractorSpec(extract_volume_min_strain_density_rows, "mJ/mm^3"),
    "energy.strain_density.max": ExtractorSpec(extract_volume_max_strain_density_rows, "mJ/mm^3"),
    "energy.strain_density.range": ExtractorSpec(extract_volume_range_strain_density_rows, "mJ/mm^3"),
    "energy.strain_density.p95": ExtractorSpec(extract_volume_p95_strain_density_rows, "mJ/mm^3"),
    "energy.strain_density.p99": ExtractorSpec(extract_volume_p99_strain_density_rows, "mJ/mm^3"),
    "energy.strain_density.cv": ExtractorSpec(extract_volume_cv_strain_density_rows, "-"),
    "energy.strain_density.skewness": ExtractorSpec(extract_volume_skewness_strain_density_rows, "-"),
    "energy.strain_density.kurtosis": ExtractorSpec(extract_volume_kurtosis_strain_density_rows, "-"),
    "energy.strain_density.normalized.mean": ExtractorSpec(extract_volume_mean_normalized_strain_density_rows, "-"),
    "energy.strain_density.normalized.std": ExtractorSpec(extract_volume_std_normalized_strain_density_rows, "-"),
    "energy.strain_density.normalized.median": ExtractorSpec(extract_volume_median_normalized_strain_density_rows, "-"),
    "energy.strain_density.normalized.min": ExtractorSpec(extract_volume_min_normalized_strain_density_rows, "-"),
    "energy.strain_density.normalized.max": ExtractorSpec(extract_volume_max_normalized_strain_density_rows, "-"),
    "energy.strain_density.normalized.range": ExtractorSpec(extract_volume_range_normalized_strain_density_rows, "-"),
    "energy.strain_density.normalized.p95": ExtractorSpec(extract_volume_p95_normalized_strain_density_rows, "-"),
    "energy.strain_density.normalized.p99": ExtractorSpec(extract_volume_p99_normalized_strain_density_rows, "-"),
    "energy.strain_density.normalized.cv": ExtractorSpec(extract_volume_cv_normalized_strain_density_rows, "-"),
    "energy.strain_density.normalized.skewness": ExtractorSpec(extract_volume_skewness_normalized_strain_density_rows, "-"),
    "energy.strain_density.normalized.kurtosis": ExtractorSpec(extract_volume_kurtosis_normalized_strain_density_rows, "-"),
}

MODAL_EXTRACTORS: tuple[tuple[str, Callable[..., Any], str], ...] = (
    ("res_freq", extract_resonant_frequency_rows, "Hz"),
    ("part_factor", extract_participation_factor_rows, "-"),
    ("eff_modal_mass", extract_effective_modal_mass_rows, "kg"),
)


def extract_post_rows(
    *,
    ctx: Any,
    mapdl: Any,
    cache: Any,
    meta: dict[str, Any],
    case_hash: str,
    allowed_needed: dict[str, int],
    compute_needed: dict[str, int],
    allowed_requested: set[str],
) -> list[dict[str, Any]]:
    """Run registered postprocess extractors and update the case cache.

    Parameters
    ----------
    ctx : Any
        Postprocess context passed to extractor functions.
    mapdl : Any
        Active MAPDL object used by extractors that query MAPDL.
    cache : Any
        Per-case post cache. Extracted values are upserted into this object.
    meta : dict[str, Any]
        Case metadata appended to explicitly requested Excel rows.
    case_hash : str
        Hash identifying the current case.
    allowed_needed : dict[str, int]
        Output prefixes allowed for this simulation type after dependency
        expansion.
    compute_needed : dict[str, int]
        Output prefixes that must be recomputed because cache entries are
        missing.
    allowed_requested : set[str]
        User-facing prefixes requested for Excel output.

    Returns
    -------
    list[dict[str, Any]]
        Rows for explicitly requested outputs computed during this call.
    """

    case_rows: list[dict[str, Any]] = []

    def cache_rows(rows: Any) -> None:
        for r in rows:
            cache.upsert(
                category=str(r.category),
                row=int(r.row),
                col=int(r.col),
                value=float(r.value),
            )

    def add_rows(rows: Any) -> None:
        for r in rows:
            d = r.as_dict()
            d.update(meta)
            case_rows.append(d)

    for prefix, spec in STATIC_EXTRACTORS.items():
        if prefix not in allowed_needed or prefix not in compute_needed:
            continue
        kwargs = {
            "ctx": ctx,
            "case_hash": case_hash,
            "unit": spec.unit,
            **spec.extra_kwargs,
        }
        if spec.needs_mapdl:
            kwargs["mapdl"] = mapdl
        rows = spec.func(**kwargs)
        cache_rows(rows)
        if prefix in allowed_requested:
            add_rows(rows)

    for mode_index in range(1, 11):
        for prefix_base, func, unit in MODAL_EXTRACTORS:
            prefix = f"{prefix_base}_{mode_index}"
            if prefix not in allowed_needed or prefix not in compute_needed:
                continue
            rows = func(
                ctx=ctx,
                mapdl=mapdl,
                case_hash=case_hash,
                mode_index=mode_index,
                unit=unit,
            )
            cache_rows(rows)
            if prefix in allowed_requested:
                add_rows(rows)

    return case_rows
