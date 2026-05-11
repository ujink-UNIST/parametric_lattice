from dataclasses import fields, is_dataclass
from typing import (
    Any,
    Dict,
    List,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    cast,
)

import xlwings as xw
import numpy as np
from xlwings.main import Table

from core.parameters.element_type_params import (
    ElementTypeParams,
)
from core.parameters.geometry_params import GeometryParams
from core.parameters.material_params import MaterialParams
from core.parameters.meshing_params import MeshingParams
from core.parameters.profile_params import BeamProfileParams
from core.parameters.setup_params import SetupParams
from core.parameters.sim_case import (
    PostMeshSpec,
    PreMeshSpec,
    SimCase,
)
from custom_io.apdl_io import mapdl_session, run_commands
from pipeline import build_pipeline

_INPUT_TABLE = "t_input"
_OUTPUT_TABLE = "t_output"


class DataclassType(Protocol):
    __dataclass_fields__: dict[str, Any]


T = TypeVar("T", bound=DataclassType)


class DataclassInstance(Protocol):
    __dataclass_fields__: dict[str, Any]


Header = tuple[str, ...]
Body = tuple[tuple[Any, ...], ...]


def run_selected(book: xw.Book):
    return


def run_all(
    book: xw.Book,
) -> None:
    input_table: Table = _find_table(book, _INPUT_TABLE)
    output_table: Table = _find_table(book, _OUTPUT_TABLE)
    input_header, input_body = _get_table_data(input_table)
    output_header, output_body = _get_table_data(
        output_table
    )

    inputs: Tuple[SimCase, ...] = _get_simulation_cases(
        input_header, input_body
    )
    try:
        with mapdl_session() as mapdl:
            pipeline = build_pipeline(inputs[0])
            run_commands(mapdl, pipeline)
    except Exception as e:
        print(f"Error: {e}")
        raise


def _find_table(
    book: xw.Book,
    key: str,
) -> Table:
    for sheet in book.sheets:
        for table in sheet.tables:
            if (
                table.name == key
                or table.display_name == key
            ):
                return table

    raise KeyError(f"Could not find Excel table {key!r}")


def _get_table_data(
    table: Table,
) -> tuple[Header, Body]:
    header_row_range = table.header_row_range
    data_body_range = table.data_body_range

    if header_row_range is None:
        return (), ()

    header_values = header_row_range.options(ndim=1).value
    headers = tuple(str(v) for v in header_values)

    if data_body_range is None:
        return headers, ()

    body_values = data_body_range.options(ndim=2).value
    body = tuple(tuple(row) for row in body_values)

    return headers, body


def _get_simulation_cases(
    input_header: Header,
    input_body: Body,
) -> Tuple[SimCase, ...]:
    cases: List[SimCase] = []

    for i, row in enumerate(input_body):
        row_values = _map_header_to_row_values(
            input_header, row
        )

        cases.append(
            SimCase(
                row_idx=i,
                pre_mesh_spec=PreMeshSpec(
                    element_type=ElementTypeParams(
                        model=row_values["Element Type"]
                    ),
                    profile=BeamProfileParams(
                        radius=row_values[
                            "Radius Multiplier"
                        ],
                        kappa=row_values["Kappa"],
                    ),
                    geometry=GeometryParams(
                        cell_name=row_values["Cell Name"],
                        size=np.array(
                            [
                                row_values["Cell Size X"],
                                row_values["Cell Size Y"],
                                row_values["Cell Size Z"],
                            ],
                            dtype=float,
                        ),
                    ),
                    meshing=MeshingParams(
                        max_element_size=row_values[
                            "Max Element Size"
                        ]
                    ),
                ),
                post_mesh_spec=PostMeshSpec(
                    material=MaterialParams(
                        e_mod=row_values["Elastic Modulus"],
                        nu=row_values["Poisson Ratio"],
                        density=row_values["Density"],
                    ),
                    setup=SetupParams(
                        sim_type=row_values[
                            "Simulation Type"
                        ],
                        strain=row_values["Strain"],
                        n_substeps=row_values["Substeps"],
                    ),
                ),
            )
        )

    return tuple(cases)


def _map_header_to_row_values(
    input_header: Header,
    row: tuple[Any, ...],
) -> Dict[str, Any]:
    if len(input_header) != len(row):
        raise ValueError(
            "Header and row lengths do not match: "
            f"{len(input_header)} != {len(row)}"
        )

    return dict(zip(input_header, row))
