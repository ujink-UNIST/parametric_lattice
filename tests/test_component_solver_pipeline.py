from core.parameters.setup_params import SetupParams
from solve.pipeline import solver_commands


def test_solver_commands_static_case_includes_outres_and_substeps():
    commands = solver_commands(
        SetupParams(sim_type="xx", strain=0.01, n_substeps=7),
        nlgeom=True,
        nsubst=7,
    )

    assert commands[:3] == (
        "/SOLU",
        "ANTYPE,STATIC",
        "NLGEOM,ON",
    )
    assert "OUTRES,ALL,NONE" in commands
    assert "NSUBST,7,1,1" in commands
    assert "TIME,1.0" in commands
    assert commands[-2:] == ("SOLVE", "FINISH")


def test_solver_commands_modal_case_omits_static_only_commands():
    commands = solver_commands(
        SetupParams(sim_type="modal", strain=0.0, n_substeps=1),
        modal_n_modes=12,
    )

    assert commands[:4] == (
        "/SOLU",
        "ANTYPE,MODAL",
        "MODOPT,LANB,12",
        "MXPAND,12,,,,YES",
    )
    assert "OUTRES,ALL,NONE" not in commands
    assert not any(cmd.startswith("NSUBST,") for cmd in commands)
    assert commands[-2:] == ("SOLVE", "FINISH")
