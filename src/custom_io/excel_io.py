from dataclasses import fields, is_dataclass
import hashlib
import json
from pathlib import Path
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
from core.parameters.profile_params import (
    build_profile_params,
)
from core.parameters.setup_params import SetupParams
from core.parameters.sim_case import (
    PostMeshSpec,
    PreMeshSpec,
    SimCase,
)
from custom_io.apdl_io import mapdl_session, run_commands
from custom_io.lgf_io import resolve_cell_name
from custom_io.socket_io import choose_free_port
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


def run_selected(
    book: xw.Book,
    selected_indices: tuple[int, ...] | None = None,
) -> None:
    """Run selected simulation cases.

    Args:
        book: Calling xlwings workbook.
        selected_indices: 0-based indices into the input table.
            - None: run all cases
            - tuple[int, ...]: run only those cases
    """

    input_table: Table = find_table(book, _INPUT_TABLE)
    input_header, input_body = get_table_data(input_table)

    inputs: Tuple[SimCase, ...] = _get_simulation_cases(
        input_header, input_body
    )

    # Write case hashes back into the Excel input table (t_input) so each row
    # records the exact case identifier used on disk.
    _write_hashes_to_input_table(
        input_table,
        inputs,
        selected_indices=selected_indices,
        column_name="HASH",
    )

    if selected_indices is None:
        run_cases(inputs)
        return

    selected: list[SimCase] = []
    selected_set = set(selected_indices)
    for i, sim_case in enumerate(inputs):
        if i in selected_set:
            selected.append(sim_case)

    run_cases(tuple(selected))


def run_all(book: xw.Book) -> None:
    """Backwards-compatible helper: run all cases."""
    run_selected(book, selected_indices=None)


def selected_input_indices(
    book: xw.Book,
    table_key: str = _INPUT_TABLE,
) -> tuple[int, ...] | None:
    """Return 0-based indices within the input table body for current selection.

    This is intended for the Excel macro entrypoint (simulation.py) to run only
    the currently selected rows.

    Rules:
      - If the selection does not intersect the table body, returns None.
      - If the table has no body (empty), returns None.
    """

    table: Table = find_table(book, table_key)
    body = table.data_body_range
    if body is None:
        return None

    sel = book.app.selection
    if sel is None:
        return None

    body_first_row = body.row
    body_last_row = body.row + body.rows.count - 1

    # xlwings Range may or may not expose .areas depending on backend/typing.
    sel_any: Any = sel
    areas_obj = getattr(sel_any, "areas", None)
    areas = (
        areas_obj if areas_obj is not None else [sel_any]
    )

    idxs: set[int] = set()
    for area in areas:
        r0 = area.row
        r1 = area.row + area.rows.count - 1
        rr0 = max(r0, body_first_row)
        rr1 = min(r1, body_last_row)
        for r in range(rr0, rr1 + 1):
            idxs.add(r - body_first_row)

    return tuple(sorted(idxs)) if idxs else None


def run_cases(inputs: Tuple[SimCase, ...]):
    repo_root = Path(__file__).resolve().parents[2]
    base_run_dir = repo_root / "results" / "case"
    case_artifacts_root = repo_root / "artifacts" / "case"

    for sim_case in inputs:
        case_key = sim_case.to_string()
        case_hash = build_case_hash(case_key)

        run_dir = base_run_dir / f"{case_hash}"
        jobname = f"case_{case_hash}"

        run_dir.mkdir(parents=True, exist_ok=True)

        # Save sim_case metadata alongside results for reproducibility.
        sim_case_path = (
            case_artifacts_root
            / case_hash
            / "sim_case.json"
        )
        sim_case_path.parent.mkdir(
            parents=True, exist_ok=True
        )
        sim_case_path.write_text(
            json.dumps(
                {
                    "case_key": case_key,
                    "case_hash": case_hash,
                    "sim_case": sim_case,
                },
                ensure_ascii=False,
                indent=2,
                default=lambda o: (
                    o.tolist()
                    if hasattr(o, "tolist")
                    else vars(o)
                ),
            ),
            encoding="utf-8",
        )

        try:
            with mapdl_session(
                run_location=str(run_dir),
                jobname=jobname,
                cleanup_on_exit=False,
            ) as mapdl:
                print(sim_case.to_string())
                pipeline = build_pipeline(sim_case)
                run_commands(mapdl, pipeline)
        except Exception as e:
            print(f"Error: {e}")
            raise


def build_case_hash(key: str):
    return hashlib.sha256(key.encode()).hexdigest()


def _ensure_table_column(
    table: Table,
    column_name: str,
) -> int:
    """Ensure a ListObject table has a column and return its 1-based index."""

    # xlwings Table.api is the underlying Excel ListObject (Windows COM).
    api = table.api
    list_columns = api.ListColumns

    for i in range(1, list_columns.Count + 1):
        col = list_columns(i)
        # .Name is the column header
        if str(col.Name).strip() == column_name:
            return i

    # Add a new column at the end.
    new_col = list_columns.Add()
    new_col.Name = column_name
    return int(new_col.Index)


def _write_hashes_to_input_table(
    input_table: Table,
    inputs: Tuple[SimCase, ...],
    selected_indices: tuple[int, ...] | None,
    column_name: str = "HASH",
) -> None:
    body = input_table.data_body_range
    if body is None:
        return

    # Compute hashes for all cases (stable w.r.t. table row order).
    hashes: list[str] = []
    for sim_case in inputs:
        case_key = sim_case.to_string()
        hashes.append(build_case_hash(case_key))

    # Ensure the column exists, then write the selected rows.
    col_idx = _ensure_table_column(input_table, column_name)

    if selected_indices is None:
        rows_to_write = range(len(hashes))
    else:
        rows_to_write = selected_indices

    # xlwings Range uses 0-based indexing for __getitem__.
    # Our col_idx from Excel ListColumns is 1-based, so convert it.
    col0 = col_idx - 1

    for i in rows_to_write:
        # i is 0-based within the table body.
        body[i, col0].value = hashes[i]


def find_table(
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


def get_table_data(
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
                    profile=build_profile_params(
                        element_model=row_values[
                            "Element Type"
                        ],
                        radius=row_values[
                            "Radius Multiplier"
                        ],
                        kappa=row_values.get("Kappa"),
                    ),
                    geometry=GeometryParams(
                        cell_name=resolve_cell_name(
                            row_values["Cell Name"]
                        ),
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
