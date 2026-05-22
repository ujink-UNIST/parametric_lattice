from __future__ import annotations

from collections.abc import Callable

from core.apdl_commands import ApdlCommands, apdl_command
from core.parameters.sim_case import SimCase
from post.boundary_force_command import build_boundary_force_commands_
from post.boundary_moment_command import build_boundary_moment_commands_
from post.boundary_traction_command import build_boundary_traction_commands_
from post.boundary_stress_command import build_boundary_stress_commands_
from post.context import PostprocessContext
from post.dependency_resolver import expand_prefixes, topo_sort
from post.output_dependency import OUTPUT_DEPENDENCIES
from post.output_spec import is_post_output_allowed

PostHandler = Callable[[PostprocessContext], ApdlCommands]


def _noop(_: PostprocessContext) -> ApdlCommands:
    return ()


_HANDLERS: dict[str, PostHandler] = {
    # Identifiers / externally-provided
    "index": _noop,
    "hash": _noop,
    # Implemented in post/
    "boundary_force": build_boundary_force_commands_,
    "boundary_moment": build_boundary_moment_commands_,
    "boundary_traction": build_boundary_traction_commands_,
    "boundary_stress": build_boundary_stress_commands_,
    "boundary_modulus": _noop,
    "boundary_modulus_ratio": _noop,
    "effective_youngs_modulus": _noop,
    "effective_shear_modulus": _noop,
    "boundary_touch_area": _noop,
    "boundary_touch_area_ratio": _noop,
    "contact_traction": _noop,
    "contact_stress": _noop,
    "volume_stress": _noop,
    "volume_avg_stress": _noop,
    "volume_energy": _noop,
    "volume_avg_energy": _noop,
    "volume": _noop,
    # Modal stubs
    **{f"res_freq_{i}": _noop for i in range(1, 21)},
    **{f"part_factor_{i}": _noop for i in range(1, 21)},
    **{f"eff_modal_mass_{i}": _noop for i in range(1, 21)},
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
