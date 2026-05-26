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
    if c in {"boundary_traction", "boundary_stress", "boundary_modulus", "effective_youngs_modulus", "effective_shear_modulus", "contact_traction", "contact_stress", "volume_avg_stress"}:
        return "MPa"
    if c in {"boundary_modulus_ratio", "boundary_touch_area_ratio", "part_factor"}:
        return "-"
    if c in {"boundary_touch_area"}:
        return "mm^2"
    if c in {"volume"}:
        return "mm^3"
    if c in {"volume_stress"}:
        return "MPa*mm^3"
    if c in {"volume_energy"}:
        return "mJ"
    if c in {"volume_avg_energy"}:
        return "mJ/mm^3"
    if c in {"mass"}:
        return "kg"
    if c in {"specific_youngs_modulus", "specific_shear_modulus"}:
        return "mm^2/s^2"

    # Modal categories are enumerated with suffixes.
    if c == "res_freq" or c.startswith("res_freq_"):
        return "Hz"
    if c == "part_factor" or c.startswith("part_factor_"):
        return "-"
    if c == "eff_modal_mass" or c.startswith("eff_modal_mass_"):
        return "kg"

    # Fallback: unknown.
    return ""
