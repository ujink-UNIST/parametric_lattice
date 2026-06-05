#pipeline.py
"""Module for pipeline functionality in src.element_type."""

from core.apdl_commands import ApdlCommands
from core.parameters.element_type_params import (
    ElementTypeParams,
)
from element_type.element_type_command import (
    build_element_type_commands_,
)


def element_type_commands(
    element_type_params: ElementTypeParams,
) -> ApdlCommands:

    return build_element_type_commands_(
        element_type_params.model,
    )
