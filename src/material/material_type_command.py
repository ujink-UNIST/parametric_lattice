# material_type_command.py

from core.apdl_commands import ApdlCommands
from core.parameters.material_params import MaterialParams


def build_material_type_commands_(
    material_params: MaterialParams,
    mat_id: int = 1,
) -> ApdlCommands:
    """Return material definition commands."""
    return (
        f"MP,EX,{mat_id},{material_params.e_mod:.10g}",
        f"MP,NUXY,{mat_id},{material_params.nu:.10g}",
        f"MP,DENS,{mat_id},{material_params.density:.10g}",
    )
