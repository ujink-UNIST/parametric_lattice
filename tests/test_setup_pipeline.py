import numpy as np

from core.parameters.element_type_params import (
    ElementTypeParams,
)
from core.unit_cell import UnitCell
from core.parameters.geometry_params import GeometryParams
from core.parameters.setup_params import SetupParams
from setup.bc_applicator import (
    apply_displacement_loop_commands,
    bc_commands,
    strain_variable_commands,
)
from setup.pipeline import setup_commands


def test_strain_variable_commands_activate_only_selected_component():
    commands = strain_variable_commands(
        SetupParams(sim_type="xy", strain=0.02, n_substeps=5)
    )

    assert commands == (
        "*SET,e_xx,0",
        "*SET,e_yy,0",
        "*SET,e_zz,0",
        "*SET,e_xy,0.02",
        "*SET,e_yx,0.02",
        "*SET,e_yz,0",
        "*SET,e_zy,0",
        "*SET,e_xz,0",
        "*SET,e_zx,0",
    )


def test_apply_displacement_loop_commands_adds_rotations_when_requested():
    commands = apply_displacement_loop_commands(
        has_rotation_dof=True
    )

    assert "D,_NID_BC_,ROTX,0" in commands
    assert "D,_NID_BC_,ROTY,0" in commands
    assert "D,_NID_BC_,ROTZ,0" in commands


def test_bc_commands_end_with_allsel():
    commands = bc_commands(
        SetupParams(sim_type="xx", strain=0.01, n_substeps=3)
    )

    assert commands[-1] == "ALLSEL,ALL"


def test_bc_commands_can_target_endpoint_component():
    commands = bc_commands(
        SetupParams(sim_type="xx", strain=0.01, n_substeps=3),
        boundary_component="BOUNDARY_ENDPOINT_NODES",
    )

    assert "CMSEL,S,BOUNDARY_ENDPOINT_NODES" in commands


def test_setup_commands_for_static_case_include_boundary_selection():
    unit_cell = UnitCell(
        name="toy",
        nodes=np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
            ],
            dtype=float,
        ),
        node_boundaries=np.array(
            [
                [-1, -1, -1],
                [1, -1, -1],
                [1, 1, -1],
            ],
            dtype=int,
        ),
        beam_types=({},),
        edges=np.array(
            [
                [0, 1],
                [1, 2],
            ],
            dtype=int,
        ),
        edge_beam_type_ids=np.array([0, 0], dtype=int),
        edge_ratios=np.array([1.0, 0.5], dtype=float),
        edge_normal_vectors=np.array(
            [
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=float,
        ),
    )
    commands = setup_commands(
        unit_cell=unit_cell,
        element_type_params=ElementTypeParams(model="BEAM188"),
        geometry_params=GeometryParams(
            cell_name="toy",
            size=np.array([1.0, 1.0, 1.0], dtype=float),
        ),
        setup_params=SetupParams(
            sim_type="xx",
            strain=0.01,
            n_substeps=3,
        ),
    )

    assert "CM,BOUNDARY_ENDPOINT_NODES,NODE" in commands
    assert "CMSEL,S,BOUNDARY_ENDPOINT_NODES" in commands
    assert commands[-1] == "ALLSEL,ALL"
