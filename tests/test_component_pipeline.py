import numpy as np

from core.parameters.element_type_params import (
    ElementTypeParams,
)
from core.parameters.geometry_params import GeometryParams
from core.parameters.material_params import MaterialParams
from core.parameters.meshing_params import MeshingParams
from core.parameters.profile_params import BeamProfileParams
from core.parameters.setup_params import SetupParams
from core.parameters.sim_case import (
    PostMeshSpec,
    PreMeshSpec,
    SimCase,
)
from pipeline import build_pipeline


def _build_sim_case(sim_type: str) -> SimCase:
    return SimCase(
        row_idx=0,
        pre_mesh_spec=PreMeshSpec(
            element_type=ElementTypeParams(model="BEAM188"),
            profile=BeamProfileParams(
                radius=0.5, kappa=0.85
            ),
            geometry=GeometryParams(
                cell_name="toy",
                size=np.array([1.0, 1.0, 1.0], dtype=float),
            ),
            meshing=MeshingParams(max_element_size=0.6),
        ),
        post_mesh_spec=PostMeshSpec(
            material=MaterialParams(
                e_mod=210000.0,
                nu=0.3,
                density=7.85e-9,
            ),
            setup=SetupParams(
                sim_type=sim_type,
                strain=0.01,
                n_substeps=3,
            ),
        ),
    )


def test_pipeline_modal_case_uses_modal_solver_branch(
    simple_unit_cell,
):
    commands = build_pipeline(
        simple_unit_cell,
        _build_sim_case("modal"),
    )

    assert "ANTYPE,MODAL" in commands
    assert any(
        cmd.startswith("MODOPT,LANB,") for cmd in commands
    )
    assert any(
        cmd.startswith("MXPAND,") for cmd in commands
    )
    assert "SOLVE" in commands
    assert "OUTRES,ALL,NONE" not in commands
    assert not any(
        cmd.startswith("NSUBST,") for cmd in commands
    )
