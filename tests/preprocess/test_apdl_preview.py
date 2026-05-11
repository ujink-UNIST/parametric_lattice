from apdl_preview import (
    SimCaseInput,
    build_sim_case,
    generate_apdl_commands,
    generate_apdl_text,
    load_unit_cell,
)


def test_load_unit_cell_reads_bcc_fixture():
    unit_cell = load_unit_cell("bcc")

    assert unit_cell.name == "bcc"
    assert len(unit_cell.nodes) > 0
    assert len(unit_cell.edges) > 0


def test_generate_apdl_text_for_bcc_static_case():
    sim_case = build_sim_case(
        "bcc",
        SimCaseInput(
            sim_type="xx",
            size_xyz=(1.0, 1.0, 1.0),
            radius=0.08,
            e_mod=210000.0,
            nu=0.3,
            density=7.85e-9,
            max_element_size=0.25,
            strain=0.01,
            n_substeps=3,
        ),
    )

    commands = generate_apdl_commands(sim_case)
    text = generate_apdl_text(sim_case)

    assert (
        commands[0]
        == "! Define beam element type and material properties"
    )
    assert "ANTYPE,STATIC" in commands
    assert "SOLVE" in commands
    assert "ANTYPE,STATIC" in text
    assert text.endswith("FINISH")
