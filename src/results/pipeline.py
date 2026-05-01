import re

from core.apdl_commands import ApdlCommands
from core.parameters.results_params import ResultsParams


def results_commands(
    results_params: ResultsParams,
) -> ApdlCommands:
    for parameter in results_params.value:
        m = re.fullmatch(r"(.*?)\[(.*?)\]", parameter)

        if m is None:
            raise ValueError("Invalid Format")

        key: str = m.group(1)
        unit: str = m.group(2)

    return ()
