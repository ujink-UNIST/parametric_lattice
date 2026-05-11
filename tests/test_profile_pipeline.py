from core.parameters.profile_params import (
    BeamProfileParams,
    SolidProfileParams,
)
from profile_.line_section_command import (
    build_line_section_commands_,
)
from profile_.section_command import build_section_commands_


def test_build_section_commands_reuses_identical_sections(
    simple_unit_cell,
):
    commands, edge_sec_ids = build_section_commands_(
        simple_unit_cell,
        BeamProfileParams(radius=0.5, kappa=0.85),
    )

    assert edge_sec_ids == (1, 2)
    assert sum(
        1 for command in commands if command.startswith("SECTYPE,")
    ) == 2
    assert any("D1.0000_Q1.00" in command for command in commands)
    assert any("D1.0000_Q0.50" in command for command in commands)


def test_build_section_commands_returns_empty_for_solid_profile(
    simple_unit_cell,
):
    commands, edge_sec_ids = build_section_commands_(
        simple_unit_cell,
        SolidProfileParams(radius=0.5),
    )

    assert commands == ()
    assert edge_sec_ids == ()


def test_build_line_section_commands_assigns_orientation_keypoints():
    commands = build_line_section_commands_(
        edge_sec_ids=(3, 4),
        orientation_keypoint_start=10,
    )

    assert commands == (
        "! Assign section 3 to beam line 1",
        "LSEL,S,LINE,,1",
        "LATT,1,,1,,11,,3",
        "! Assign section 4 to beam line 2",
        "LSEL,S,LINE,,2",
        "LATT,1,,1,,12,,4",
        "LSEL,ALL",
    )
