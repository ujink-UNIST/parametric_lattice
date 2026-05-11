from core.parameters.element_type_params import (
    ElementTypeParams,
)
from element_type.pipeline import element_type_commands


def test_element_type_commands_emit_beam188_cards():
    commands = element_type_commands(
        ElementTypeParams(model="BEAM188")
    )

    assert commands == (
        "! Define beam element type and material properties",
        "ET,1,188",
        "KEYOPT,1,3,3",
        "KEYOPT,1,15,0",
    )
