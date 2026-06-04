from __future__ import annotations

"""Resolve unit strings for t_out categories.

Policy: Units are not stored in post_cache; they are resolved at runtime so
unit convention changes can be applied without cache invalidation.
"""


def unit_for_category(category: str) -> str:
    c = str(category)

    # Identifiers
    if c in {"id.index", "id.hash"}:
        return ""

    if c in {"force.boundary.value"}:
        return "N"
    if c in {"moment.boundary.value"}:
        return "N*mm"

    if c in {
        "traction.boundary.value",
        "stress.boundary.value",
        "modulus.boundary.value",
        "modulus.effective.youngs",
        "modulus.effective.shear",
        "modulus.effective.bulk",
        "stiffness.elastic.tensor",
        "traction.contact.value",
        "stress.contact.value",
        "stress.volume.avg",
    }:
        return "MPa"

    if c in {
        "modulus.boundary.ratio",
        "area.boundary_contact.ratio",
        "modulus.effective.youngs.ratio",
        "modulus.effective.shear.ratio",
        "volume_fraction.cell.value",
        "element.count",
    }:
        return "-"

    if c in {"area.boundary_contact.value"}:
        return "mm^2"
    if c in {"volume.solid.value"}:
        return "mm^3"
    if c in {"stress.volume.sum"}:
        return "MPa*mm^3"
    if c in {"energy.strain.total"}:
        return "mJ"
    if c in {
        "energy.strain_density.reference",
        "energy.strain_density.mean",
        "energy.strain_density.std",
        "energy.strain_density.median",
        "energy.strain_density.min",
        "energy.strain_density.max",
        "energy.strain_density.range",
        "energy.strain_density.p95",
        "energy.strain_density.p99",
    }:
        return "mJ/mm^3"
    if c in {
        "energy.strain_density.cv",
        "energy.strain_density.skewness",
        "energy.strain_density.kurtosis",
        "energy.strain_density.normalized.mean",
        "energy.strain_density.normalized.std",
        "energy.strain_density.normalized.median",
        "energy.strain_density.normalized.min",
        "energy.strain_density.normalized.max",
        "energy.strain_density.normalized.range",
        "energy.strain_density.normalized.p95",
        "energy.strain_density.normalized.p99",
        "energy.strain_density.normalized.cv",
        "energy.strain_density.normalized.skewness",
        "energy.strain_density.normalized.kurtosis",
    }:
        return "-"
    if c in {"compliance.elastic.tensor"}:
        return "1/MPa"
    if c in {"mass.solid.value"}:
        return "kg"
    if c in {"modulus.effective.youngs.specific", "modulus.effective.shear.specific"}:
        return "mm^2/s^2"

    # Modal categories.
    if c in {"modal.res_freq", "modal_ff.res_freq"}:
        return "Hz"
    if c in {"modal.part_factor", "modal_ff.part_factor"}:
        return "-"
    if c in {"modal.eff_modal_mass", "modal_ff.eff_modal_mass"}:
        return "kg"

    # Fallback: unknown.
    return ""
