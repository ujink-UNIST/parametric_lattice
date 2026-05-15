# apdl_preview.py

from __future__ import annotations

from dataclasses import replace
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


def load_unit_cell(cell_name: str) -> UnitCell:
    lgf_lines = import_lgf(cell_name)
    unit_cell = lattice_to_unit_cell(lgf_to_lattice(lgf_lines))
    return replace(unit_cell, name=cell_name)


def build_sim_case(
    cell_name: str,
    *,
    sim_type: str,
    size_xyz: tuple[float, float, float],
    radius: float,
    e_mod: float,
    nu: float,
    density: float,
    max_element_size: float,
    strain: float,
    n_substeps: int = 1,
    kappa: float = 0.85,
    element_type: str = "BEAM188",
    row_idx: int = 0,
    # Joint strengthening factors (beam-only)
    joint_area_factor: float = 1.0,
    joint_length_factor: float = 1.0,
    joint_bending_factor: float = 1.0,
    joint_torsion_factor: float = 1.0,
) -> SimCase:
    return SimCase(
        row_idx=row_idx,
        pre_mesh_spec=PreMeshSpec(
            element_type=ElementTypeParams(model=element_type),
            profile=(
                BeamProfileParams(
                    radius=radius,
                    kappa=kappa,
                    joint_area_factor=joint_area_factor,
                    joint_length_factor=joint_length_factor,
                    joint_bending_factor=joint_bending_factor,
                    joint_torsion_factor=joint_torsion_factor,
                )
                if "BEAM" in element_type.upper()
                else SolidProfileParams(radius=radius)
            ),
            geometry=GeometryParams(
                cell_name=cell_name,
                size=np.array(size_xyz, dtype=float),
            ),
            meshing=MeshingParams(max_element_size=max_element_size),
        ),
        post_mesh_spec=PostMeshSpec(
            material=MaterialParams(
                e_mod=e_mod,
                nu=nu,
                density=density,
            ),
            setup=SetupParams(
                sim_type=sim_type,
                strain=strain,
                n_substeps=n_substeps,
            ),
        ),
    )


def generate_apdl_commands(
    sim_case: SimCase,
) -> ApdlCommands:
    return build_pipeline(sim_case, save_intermediate=False)


def generate_apdl_text(
    sim_case: SimCase,
) -> str:
    commands = generate_apdl_commands(sim_case)
    return "\n".join(commands)
