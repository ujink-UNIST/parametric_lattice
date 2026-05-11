import re

from core.apdl_commands import ApdlCommands
from core.parameters.results_params import ResultsParams
from results.force_extractor import get_all_face_forces


def results_commands(
    # results_params: ResultsParams,
) -> ApdlCommands:
    # grouped: dict[str, list[str]] = {}

    # for parameter in results_params.value:
    #     m = re.fullmatch(
    #         r"([a-zA-Z]+)_([a-zA-Z0-9]+)", parameter
    #     )
    #     if m is None:
    #         raise ValueError(f"Invalid Format: {parameter}")

    #     key: str = m.group(1)  # "stress"
    #     subkey: str = m.group(2)  # "xx", "xy", ...

    #     grouped.setdefault(key, []).append(subkey)

    get_forces_cmd = get_all_face_forces()

    return (
        "/POST1",
        "SET,LAST",
    ) + get_forces_cmd
