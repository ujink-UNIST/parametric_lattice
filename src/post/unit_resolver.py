from __future__ import annotations

"""Resolve unit strings for t_out categories.

Policy: Units are not stored in post_cache; they are resolved at runtime so
unit convention changes can be applied without cache invalidation.
"""


def unit_for_category(category: str) -> str:
    c = str(category)

    if c in {"boundary_force"}:
        return "N"
    if c in {"boundary_moment"}:
        return "N*mm"
    if c in {"boundary_traction", "boundary_stress", "boundary_modulus", "effective_youngs_modulus", "effective_shear_modulus", "effective_bulk_modulus", "contact_traction", "contact_stress", "stress_vol_avg"}:
        return "MPa"
    if c in {
        "boundary_modulus_ratio",
        "boundary_touch_area_ratio",
        "effective_youngs_modulus_ratio",
        "effective_shear_modulus_ratio",
    }:
        return "-"
    if c in {"boundary_touch_area"}:
        return "mm^2"
    if c in {"volume"}:
        return "mm^3"
    if c in {"volume_fraction"}:
        return "-"
    if c in {"stress_vol_sum"}:
        return "MPa*mm^3"
    if c in {"energy_sum"}:
        return "mJ"
    if c in {"energy_vol_avg"}:
        return "mJ/mm^3"
    if c in {"mass"}:
        return "kg"
    if c in {"specific_youngs_modulus", "specific_shear_modulus"}:
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
