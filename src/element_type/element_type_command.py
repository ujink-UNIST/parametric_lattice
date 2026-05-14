# element_type_command.py

from core.apdl_commands import ApdlCommands


def build_element_type_commands_(
    model: str,
) -> ApdlCommands:
    """Return element type definition commands.

    Note: Keep this output stable/minimal because unit tests assert exact tuples.
    """

    model_upper = model.strip().upper()

    if model_upper.startswith("BEAM"):
        et_num = int(model_upper.replace("BEAM", ""))
        return (
            "! Define beam element type and material properties",
            f"ET,1,{et_num}",
            "KEYOPT,1,3,3",
            "KEYOPT,1,15,0",
        )

    if model_upper.startswith("SOLID"):
        et_num = int(model_upper.replace("SOLID", ""))
        return (
            "! Define solid element type",
            f"ET,1,{et_num}",
        )

    raise ValueError(f"Unsupported element model: {model}")
