# pipeline.py

from __future__ import annotations

from collections.abc import Callable

from core.apdl_commands import ApdlCommands, apdl_command
from core.parameters.sim_case import SimCase
from postprocess.boundary_command import (
    build_boundary_stress_commands_,
    build_boundary_traction_commands_,
)
from postprocess.context import PostprocessContext
from postprocess.dependency_resolver import expand_prefixes, topo_sort
from postprocess.energy_command import (
    build_element_strain_energy_commands_,
    build_node_strain_energy_commands_,
)
from postprocess.force_command import build_boundary_force_moment_commands_
from postprocess.modal_command import (
    build_modal_effective_mass_commands_,
    build_modal_participation_commands_,
    build_resonant_frequency_command_,
)
from postprocess.output_dependency import OUTPUT_DEPENDENCIES
from postprocess.volume_command import (
    build_volume_commands_,
    build_volume_energy_commands_,
    build_volume_stress_commands_,
)
from postprocess.weight_command import build_node_volume_mass_commands_

PostprocessHandler = Callable[[PostprocessContext], ApdlCommands]


def _noop(_: PostprocessContext) -> ApdlCommands:
    return ()


_HANDLERS: dict[str, PostprocessHandler] = {
    # Scalars written by excel_io (not computed by MAPDL postprocess)
    "index": _noop,
    "hash": _noop,
    # Actual MAPDL postprocess blocks
    "boundary_traction": lambda _ctx: build_boundary_traction_commands_(_ctx),
    "boundary_force": lambda _ctx: build_boundary_force_moment_commands_(_ctx),
    "boundary_moment": lambda _ctx: build_boundary_force_moment_commands_(_ctx),
    "boundary_stress": lambda _ctx: build_boundary_stress_commands_(_ctx),
    "volume_stress": lambda _ctx: build_volume_stress_commands_(_ctx),
    "volume_energy": lambda _ctx: build_volume_energy_commands_(_ctx),
    # Derived outputs computed in Python (see excel_io)
    "boundary_modulus": _noop,
    "boundary_modulus_ratio": _noop,
    "effective_youngs_modulus": _noop,
    "effective_shear_modulus": _noop,
    "boundary_touch_area": _noop,
    "boundary_touch_area_ratio": _noop,
    "contact_traction": _noop,
    "contact_stress": _noop,
    "volume_avg_stress": _noop,
    "volume_avg_energy": _noop,
    # Intermediate outputs (not written to Excel)
    "elem_sene": lambda _ctx: build_element_strain_energy_commands_(_ctx),
    "node_sene": lambda _ctx: build_node_strain_energy_commands_(_ctx),
    "node_volmass": lambda _ctx: build_node_volume_mass_commands_(_ctx),
    "volume": lambda _ctx: build_volume_commands_(_ctx),
    # Modal-only (resonant frequencies)
    **{
        f"res_freq_{i}": (lambda _ctx, i=i: build_resonant_frequency_command_(_ctx, mode_index=i))
        for i in range(1, 21)
    },
    # Modal-only (participation factors)
    **{
        f"part_factor_{i}": (lambda _ctx, i=i: build_modal_participation_commands_(_ctx, mode_index=i))
        for i in range(1, 21)
    },
    # Modal-only (effective modal mass)
    **{
        f"eff_modal_mass_{i}": (lambda _ctx, i=i: build_modal_effective_mass_commands_(_ctx, mode_index=i))
        for i in range(1, 21)
    },
}


def postprocess_commands(
    sim_case: SimCase,
    needed: dict[str, int],
) -> ApdlCommands:
    """Build APDL postprocess command sequence.

    Steps:
      1) Expand requested prefixes with prerequisites (DFS)
      2) Topologically sort to get a safe execution orderㄱ
      3) Append APDL command blocks produced by per-output handlers

    Handler internals are intentionally stubbed for now.
    """

    requested_prefixes = set(needed.keys())
    all_prefixes = expand_prefixes(requested_prefixes, OUTPUT_DEPENDENCIES)
    order = topo_sort(all_prefixes, OUTPUT_DEPENDENCIES)

    missing = [p for p in order if p not in _HANDLERS]
    if missing:
        raise KeyError("Missing postprocess handler(s) for: " + ", ".join(missing))

    ctx = PostprocessContext(
        sim_case=sim_case,
        needed=needed,
    )

    # Common POST1 prelude (run once).
    cmds: ApdlCommands = (
        apdl_command("", "--- postprocess begin ---"),
        apdl_command("/POST1", "enter post1"),
        apdl_command("FILE,'case','rst'", "attach results"),
        apdl_command("SET,LAST", "use last substep"),
        apdl_command("ALLSEL,ALL", "reset selections"),
        apdl_command("ESEL,ALL", "select all elements"),
    )

    for prefix in order:
        cmds = cmds + _HANDLERS[prefix](ctx)

    cmds = cmds + (apdl_command("", "--- postprocess end ---"),)

    return cmds
