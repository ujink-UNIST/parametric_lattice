from dataclasses import fields, is_dataclass
from typing import (
    Any,
    List,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    cast,
)

import xlwings as xw
from xlwings.main import Table

from core.parameters.geometry_params import (
    build_geometry_params,
)
from core.parameters.material_params import (
    build_material_params,
)
from core.parameters.meshing_params import (
    build_meshing_params,
)
from core.parameters.setup_params import build_setup_params
from core.parameters.sim_case import SimCase

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


def clear_workbook_results(book: xw.Book):
    return


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
    col_idx = {
        name: i for i, name in enumerate(input_header)
    }

    for row_idx, row in enumerate(input_body):
        cases.append(
            SimCase(
                row_idx=row_idx,
                material_params=build_params(
                    input_header, row
                ),
                geometry_params=build_geometry_params(
                    input_header, row
                ),
                meshing_params=build_params(
                    input_header, row
                ),
                setup_params=build_params(SetupParams, row),
            )
        )
    return tuple(cases)
