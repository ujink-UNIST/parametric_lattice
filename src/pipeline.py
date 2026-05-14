# pipeline.py

from __future__ import annotations

from core.apdl_commands import ApdlCommands
from core.lattice import Lattice
from core.parameters.sim_case import SimCase
from core.unit_cell import UnitCell
from custom_io.lattice_io import export_lattice
from custom_io.lgf_io import import_lgf
from element_type.pipeline import element_type_commands
from geometry.pipeline import geometry_commands
from material.pipeline import material_commands
from meshing.pipeline import meshing_commands
from preprocess.pipeline import (
    lattice_to_unit_cell,
    lgf_to_lattice,
)
from profile_.pipeline import profile_commands
from results.pipeline import results_commands
from setup.pipeline import setup_commands
from solve.pipeline import solver_commands


def build_pipeline(
    unit_cell: UnitCell | SimCase,
    sim_case: SimCase | None = None,
) -> ApdlCommands:
    """Build a flattened APDL command sequence.

    - Production path: ``build_pipeline(sim_case)`` loads the LGF from disk.
    - Test path: ``build_pipeline(unit_cell, sim_case)`` uses the provided
      UnitCell fixture.
    """

    if isinstance(unit_cell, SimCase):
        sim_case = unit_cell
        lattice: Lattice = lgf_to_lattice(
            import_lgf(
                sim_case.pre_mesh_spec.geometry.cell_name
            )
        )
        export_lattice(
            sim_case.pre_mesh_spec.geometry.cell_name,
            lattice,
        )
        unit_cell = lattice_to_unit_cell(lattice)
    else:
        if sim_case is None:
            raise TypeError(
                "build_pipeline(unit_cell, sim_case) missing sim_case"
            )

    pre = (
        "/CLEAR,START",
        "/UNITS,MPA",
        "/PREP7",
    )

    return (
        pre
        + element_type_commands(
            sim_case.pre_mesh_spec.element_type
        )
        + geometry_commands(
            unit_cell, sim_case.pre_mesh_spec.geometry
        )
        + profile_commands(
            unit_cell,
            sim_case.pre_mesh_spec.geometry,
            sim_case.pre_mesh_spec.profile,
        )
        + meshing_commands(
            unit_cell,
            sim_case.pre_mesh_spec.geometry,
            sim_case.pre_mesh_spec.profile,
            sim_case.pre_mesh_spec.meshing,
        )
        + material_commands(
            sim_case.post_mesh_spec.material
        )
        + setup_commands(
            unit_cell,
            sim_case.pre_mesh_spec.profile,
            sim_case.pre_mesh_spec.geometry,
            sim_case.post_mesh_spec.setup,
        )
        + solver_commands(sim_case.post_mesh_spec.setup)
        # results_commands()
        + ("FINISH",)
    )
