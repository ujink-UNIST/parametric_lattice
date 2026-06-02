from __future__ import annotations

from collections.abc import Callable

from core.apdl_commands import ApdlCommands, apdl_command
from core.parameters.sim_case import SimCase
from post.boundary_force_command import build_boundary_force_commands_
from post.boundary_moment_command import build_boundary_moment_commands_
from post.boundary_traction_command import build_boundary_traction_commands_
from post.boundary_stress_command import build_boundary_stress_commands_
from post.boundary_modulus_command import build_boundary_modulus_commands_
from post.boundary_touch_area_command import build_boundary_touch_area_commands_
from post.contact_command import build_contact_stress_commands_, build_contact_traction_commands_
from post.effective_moduli_command import (
    build_effective_shear_modulus_commands_,
    build_effective_youngs_modulus_commands_,
)
from post.effective_bulk_modulus_command import build_effective_bulk_modulus_commands_
from post.mass_command import build_mass_commands_
from post.specific_moduli_command import (
    build_specific_shear_modulus_commands_,
    build_specific_youngs_modulus_commands_,
)
from post.effective_moduli_ratio_command import (
    build_effective_shear_modulus_ratio_commands_,
    build_effective_youngs_modulus_ratio_commands_,
)
from post.volume_command import build_volume_commands_
from post.volume_metrics_command import build_volume_energy_commands_, build_volume_stress_commands_
from post.volume_fraction_command import build_volume_fraction_commands_
from post.modal_command import (
    build_modal_effective_mass_commands_,
    build_modal_participation_commands_,
    build_resonant_frequency_command_,
)
from post.context import PostprocessContext
from post.dependency_resolver import expand_prefixes, topo_sort
from post.output_dependency import OUTPUT_DEPENDENCIES
from post.output_spec import is_post_output_allowed

PostHandler = Callable[[PostprocessContext], ApdlCommands]


def _noop(_: PostprocessContext) -> ApdlCommands:
    return ()




_HANDLERS: dict[str, PostHandler] = {
    # Identifiers / externally-provided
    "id.index": _noop,
    "id.hash": _noop,

    # MAPDL-computed outputs (implemented in post/)
    "force.boundary.value": build_boundary_force_commands_,
    "moment.boundary.value": build_boundary_moment_commands_,
    "traction.boundary.value": build_boundary_traction_commands_,
    "stress.boundary.value": build_boundary_stress_commands_,
    "volume.solid.value": build_volume_commands_,
    "stress.volume.sum": build_volume_stress_commands_,
    "energy.strain.total": build_volume_energy_commands_,

    # Python-derived outputs (no MAPDL commands)
    "modulus.boundary.value": _noop,
    "modulus.boundary.ratio": _noop,
    "modulus.effective.youngs": build_effective_youngs_modulus_commands_,
    "modulus.effective.shear": build_effective_shear_modulus_commands_,
    "modulus.effective.bulk": build_effective_bulk_modulus_commands_,
    "modulus.effective.youngs.specific": build_specific_youngs_modulus_commands_,
    "modulus.effective.shear.specific": build_specific_shear_modulus_commands_,
    "modulus.effective.youngs.ratio": build_effective_youngs_modulus_ratio_commands_,
    "modulus.effective.shear.ratio": build_effective_shear_modulus_ratio_commands_,
    "area.boundary_contact.value": _noop,
    "area.boundary_contact.ratio": _noop,
    "traction.contact.value": _noop,
    "stress.contact.value": _noop,
    "stress.volume.avg": _noop,
    "energy.strain_density": _noop,
    "energy.strain_density.reference": _noop,
    "energy.strain_density.normalized": _noop,
    "energy.strain_density.mean": _noop,
    "energy.strain_density.std": _noop,
    "energy.strain_density.median": _noop,
    "energy.strain_density.min": _noop,
    "energy.strain_density.max": _noop,
    "energy.strain_density.range": _noop,
    "energy.strain_density.p95": _noop,
    "energy.strain_density.p99": _noop,
    "energy.strain_density.cv": _noop,
    "energy.strain_density.skewness": _noop,
    "energy.strain_density.kurtosis": _noop,
    "energy.strain_density.normalized.mean": _noop,
    "energy.strain_density.normalized.std": _noop,
    "energy.strain_density.normalized.median": _noop,
    "energy.strain_density.normalized.min": _noop,
    "energy.strain_density.normalized.max": _noop,
    "energy.strain_density.normalized.range": _noop,
    "energy.strain_density.normalized.p95": _noop,
    "energy.strain_density.normalized.p99": _noop,
    "energy.strain_density.normalized.cv": _noop,
    "energy.strain_density.normalized.skewness": _noop,
    "energy.strain_density.normalized.kurtosis": _noop,
    "mass.solid.value": build_mass_commands_,
    "volume_fraction.cell.value": build_volume_fraction_commands_,
    "element.count": _noop,

    # Modal outputs
    **{
        f"res_freq_{i}": (lambda _ctx, i=i: build_resonant_frequency_command_(_ctx, mode_index=i))
        for i in range(1, 11)
    },
    **{
        f"part_factor_{i}": (lambda _ctx, i=i: build_modal_participation_commands_(_ctx, mode_index=i))
        for i in range(1, 11)
    },
    **{
        f"eff_modal_mass_{i}": (lambda _ctx, i=i: build_modal_effective_mass_commands_(_ctx, mode_index=i))
        for i in range(1, 11)
    },
}


def post_commands(
    sim_case: SimCase,
    needed: dict[str, int],
) -> ApdlCommands:
    """Build APDL post command sequence (POST1) for requested outputs.

    This mirrors :func:`postprocess.pipeline.postprocess_commands`, but targets
    the new post/ long-format output pipeline.

    Extraction to :class:`post.row.TOutRow` is performed separately.
    """

    sim_type = str(sim_case.post_mesh_spec.setup.sim_type)

    requested_prefixes = {p for p in needed.keys() if is_post_output_allowed(p, sim_type)}
    all_prefixes = expand_prefixes(requested_prefixes, OUTPUT_DEPENDENCIES)
    order = topo_sort(all_prefixes, OUTPUT_DEPENDENCIES)

    missing = [p for p in order if p not in _HANDLERS]
    if missing:
        raise KeyError("Missing post handler(s) for: " + ", ".join(missing))

    ctx = PostprocessContext(sim_case=sim_case, needed=needed)

    cmds: ApdlCommands = (
        apdl_command("", "--- post begin ---"),
        apdl_command("/POST1", "enter post1"),
        apdl_command("FILE,'case','rst'", "attach results"),
        apdl_command("SET,LAST", "use last substep"),
        apdl_command("ALLSEL,ALL", "reset selections"),
        apdl_command("ESEL,ALL", "select all elements"),
    )

    for prefix in order:
        cmds = cmds + _HANDLERS[prefix](ctx)

    cmds = cmds + (apdl_command("", "--- post end ---"),)
    return cmds
