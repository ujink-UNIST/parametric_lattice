from core.parameters.material_params import MaterialParams
from material.pipeline import material_commands


def test_material_commands_emit_mp_cards():
    commands = material_commands(
        MaterialParams(
            e_mod=210000.0,
            nu=0.3,
            density=7.85e-9,
        )
    )

    assert commands == (
        "MP,EX,1,210000",
        "MP,NUXY,1,0.3",
        "MP,DENS,1,7.85e-09",
    )
