# File: c:\Users\USER\Documents\parametric_lattice\src\meshing\element_type_command.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from core.apdl_commands import ApdlCommands


def build_element_type_commands_(
    model: str,
    # material_params: MaterialParams,
    # mat_id: int = 1,
) -> ApdlCommands:
    """Return beam element type and material definition commands."""
    et_num = int(model.strip().upper().replace("BEAM", ""))
    return (
        "! Define beam element type and material properties",
        f"ET,1,{et_num}",
        "KEYOPT,1,3,3",
        "KEYOPT,1,15,0",
        # f"MP,EX,{mat_id},{material_params.e_mod:.10g}",
        # f"MP,NUXY,{mat_id},{material_params.nu:.10g}",
        # f"MP,DENS,{mat_id},{material_params.density:.10g}",
    )
