from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from core.apdl_commands import ApdlCommands
from core.parameters.element_type_params import (
    ElementTypeParams,
)
from core.parameters.geometry_params import GeometryParams
from core.parameters.material_params import MaterialParams
from core.parameters.meshing_params import MeshingParams
from core.parameters.profile_params import (
    BeamProfileParams,
    SolidProfileParams,
)
from core.parameters.setup_params import SetupParams
from core.parameters.sim_case import (
    PostMeshSpec,
    PreMeshSpec,
    SimCase,
)
from core.unit_cell import UnitCell
from custom_io.lgf_io import import_lgf
from pipeline import build_pipeline
from preprocess.pipeline import (
    lattice_to_unit_cell,
    lgf_to_lattice,
)


@dataclass(frozen=True)
class SimCaseInput:
    sim_type: str
    size_xyz: tuple[float, float, float]
    radius: float
    e_mod: float
    nu: float
    density: float
    max_element_size: float
    strain: float
    n_substeps: int = 1
    kappa: float = 0.85
    element_type: str = "BEAM188"
    row_idx: int = 0


def load_unit_cell(cell_name: str) -> UnitCell:
    lgf_lines = import_lgf(cell_name)
    unit_cell = lattice_to_unit_cell(lgf_to_lattice(lgf_lines))
    return replace(unit_cell, name=cell_name)


def build_sim_case(
    cell_name: str,
    sim_input: SimCaseInput,
) -> SimCase:
    return SimCase(
        row_idx=sim_input.row_idx,
        pre_mesh_spec=PreMeshSpec(
            element_type=ElementTypeParams(
                model=sim_input.element_type
            ),
            profile=(
                BeamProfileParams(
                    radius=sim_input.radius,
                    kappa=sim_input.kappa,
                )
                if "BEAM" in sim_input.element_type.upper()
                else SolidProfileParams(
                    radius=sim_input.radius
                )
            ),
            geometry=GeometryParams(
                cell_name=cell_name,
                size=np.array(
                    sim_input.size_xyz, dtype=float
                ),
            ),
            meshing=MeshingParams(
                max_element_size=sim_input.max_element_size
            ),
        ),
        post_mesh_spec=PostMeshSpec(
            material=MaterialParams(
                e_mod=sim_input.e_mod,
                nu=sim_input.nu,
                density=sim_input.density,
            ),
            setup=SetupParams(
                sim_type=sim_input.sim_type,
                strain=sim_input.strain,
                n_substeps=sim_input.n_substeps,
            ),
        ),
    )


def generate_apdl_commands(
    sim_case: SimCase,
) -> ApdlCommands:
    commands = build_pipeline(sim_case)

    # The preview API/fixtures want the command stream starting from the first
    # "real" stage marker (element type definition), not the global /CLEAR.
    try:
        start = commands.index(
            "! Define beam element type and material properties"
        )
        return commands[start:]
    except ValueError:
        return commands


def generate_apdl_text(
    sim_case: SimCase,
) -> str:
    commands = generate_apdl_commands(sim_case)
    return "\n".join(commands)
