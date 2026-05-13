import numpy as np

from core.parameters.profile_params import BeamProfileParams
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
        SetupParams(
            sim_type="xy", strain=0.02, n_substeps=5
        )
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
