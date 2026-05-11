import numpy as np

from core.parameters.element_type_params import (
    ElementTypeParams,
)
from core.parameters.geometry_params import (
    GeometryParams,
    build_geometry_params,
)
from core.parameters.material_params import (
    MaterialParams,
    build_material_params,
)
from core.parameters.meshing_params import (
    MeshingParams,
    build_meshing_params,
)
from core.parameters.profile_params import (
    BeamProfileParams,
    SolidProfileParams,
)
from core.parameters.setup_params import (
    SetupParams,
    build_setup_params,
)


def test_build_geometry_params_reads_excel_row():
    header = (
        "cell_name",
        "size_x",
        "size_y",
        "size_z",
    )
    row = ("bcc", 1.5, 2.0, 2.5)

    params = build_geometry_params(header, row)

    assert params.cell_name == "bcc"
    np.testing.assert_allclose(
        params.size,
        np.array([1.5, 2.0, 2.5], dtype=float),
    )


def test_build_material_params_reads_excel_row():
    header = ("e_mod", "nu", "density")
    row = (210000.0, 0.31, 7.85e-9)

    params = build_material_params(header, row)

    assert params == MaterialParams(210000.0, 0.31, 7.85e-9)


def test_build_meshing_params_reads_excel_row():
    header = ("max_element_size",)
    row = (0.25,)

    params = build_meshing_params(header, row)

    assert params == MeshingParams(0.25)


def test_build_setup_params_reads_excel_row():
    header = ("sim_type", "strain", "n_substeps")
    row = ("xx", 0.02, 12)

    params = build_setup_params(header, row)

    assert params == SetupParams("xx", 0.02, 12)


def test_element_and_profile_param_dataclasses_store_values():
    element_type = ElementTypeParams(model="BEAM188")
    beam_profile = BeamProfileParams(radius=0.5, kappa=0.85)
    solid_profile = SolidProfileParams(radius=0.75)

    assert element_type.model == "BEAM188"
    assert beam_profile.radius == 0.5
    assert beam_profile.kappa == 0.85
    assert solid_profile.radius == 0.75
