# pipeline.py

from core.apdl_commands import ApdlCommands
from core.parameters.material_params import MaterialParams
from material.material_type_command import (
    build_material_type_commands_,
)


def material_commands(
    material_params: MaterialParams,
) -> ApdlCommands:
    return build_material_type_commands_(material_params)
