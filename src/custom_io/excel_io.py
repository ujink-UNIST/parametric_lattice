# excel_io.py

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
from custom_io.excel_read import (
    read_float,
    read_int,
    read_optional_float,
    read_str,
    read_Vector3,
)
from custom_io.lgf_io import resolve_cell_name
from custom_io.socket_io import choose_free_port
from pipeline import build_pipeline
from postprocess.output_spec import POSTPROCESS_OUTPUT_SPEC
from postprocess.pipeline import postprocess_commands

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

    hashes = [
        build_case_hash(sc.to_string()) for sc in inputs
    ]

    # Write case hashes back into the Excel input table (t_input) so each row
    # records the exact case identifier used on disk.
    _write_hashes_to_input_table(
        input_table,
        hashes,
        selected_indices=selected_indices,
        column_name="hash",
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


def run_selected_postprocess(
    book: xw.Book,
    selected_indices: tuple[int, ...] | None = None,
) -> None:
    input_table: Table = find_table(book, _INPUT_TABLE)
    input_header, input_body = get_table_data(input_table)

    inputs: Tuple[SimCase, ...] = _get_simulation_cases(
        input_header, input_body
    )

    hashes = [
        build_case_hash(sc.to_string()) for sc in inputs
    ]

    output_table: Table = find_table(book, _OUTPUT_TABLE)
    output_header, output_body = get_table_data(
        output_table
    )

    _write_index_hash_to_output_table(
        book,
        inputs,
        hashes,
        selected_indices=selected_indices,
        table_key=_OUTPUT_TABLE,
    )

    if selected_indices is None:
        run_postprocess(inputs, output_header)
        return

    selected: list[SimCase] = []
    selected_set = set(selected_indices)
    for i, sim_case in enumerate(inputs):
        if i in selected_set:
            selected.append(sim_case)

    run_postprocess(tuple(selected), output_header)


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


def run_cases(
    inputs: Tuple[SimCase, ...],
    save_intermediate: bool = False,
):
    repo_root = Path(__file__).resolve().parents[2]
    base_run_dir = repo_root / "results" / "case"
    case_artifacts_root = repo_root / "artifacts" / "case"

    for sim_case in inputs:
        case_key = sim_case.to_string()
        case_hash = build_case_hash(case_key)

        run_dir = base_run_dir / f"{case_hash}"
        # Use a stable, non-hash jobname so result filenames don't include the case hash.
        # The run_dir is already namespaced by case_hash.
        jobname = "case"

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
                pipeline = build_pipeline(
                    sim_case,
                    save_intermediate=save_intermediate,
                )
                run_commands(mapdl, pipeline)
        except Exception as e:
            print(f"Error: {e}")
            raise


def run_postprocess(
    inputs: Tuple[SimCase, ...],
    output_header: Header,
) -> None:
    """Run postprocessing for the given cases.

    This derives required outputs from the Excel `t_output` header and validates
    them against `POSTPROCESS_OUTPUT_SPEC`.

    The derived mapping is `prefix -> n_components` where `n_components` must be
    one of {1,3,6,9}.
    """

    repo_root = Path(__file__).resolve().parents[2]
    base_run_dir = repo_root / "results" / "case"

    needed: dict[str, int] = {}
    component_sets: dict[str, set[str]] = {}

    for col in output_header:
        name = str(col).strip()
        if not name:
            continue

        if "_" in name:
            prefix, suffix = name.rsplit("_", 1)
            if suffix in _DIR_COMPONENTS:
                component_sets.setdefault(
                    prefix, set()
                ).add(suffix)
                continue

        # Scalar output column
        needed[name] = 1

    for prefix, comps in component_sets.items():
        needed[prefix] = len(comps)

    # Validate against the postprocess output spec.
    for prefix, n in needed.items():
        expected = POSTPROCESS_OUTPUT_SPEC.get(prefix)
        if expected is None:
            raise KeyError(
                f"t_output requests unknown postprocess prefix {prefix!r}. "
                f"Add it to POSTPROCESS_OUTPUT_SPEC (src/postprocess/output_spec.py)."
            )
        if expected != n:
            raise ValueError(
                f"t_output prefix {prefix!r} has {n} components, but spec requires {expected}."
            )

    # Ensure required scalar columns exist.
    for req in ("index", "hash"):
        if req not in needed:
            raise ValueError(
                f"t_output is missing required scalar column {req!r}."
            )

    # Run per-case postprocess APDL.
    for sim_case in inputs:
        case_key = sim_case.to_string()
        case_hash = build_case_hash(case_key)

        run_dir = base_run_dir / f"{case_hash}"
        jobname = "case"

        try:
            with mapdl_session(
                run_location=str(run_dir),
                jobname=jobname,
                cleanup_on_exit=False,
            ) as mapdl:
                print(sim_case.to_string())
                pipeline = postprocess_commands(
                    sim_case=sim_case,
                    needed=needed,
                )
                run_commands(mapdl, pipeline)
                # TODO: parse postprocess outputs and write to t_output via hash matching.
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
    hashes: list[str],
    selected_indices: tuple[int, ...] | None,
    column_name: str = "hash",
) -> None:
    # Ensure the column exists (may add a new column).
    col_idx = _ensure_table_column(input_table, column_name)

    # Refresh the body range after mutating table columns.
    body = input_table.data_body_range
    if body is None:
        return

    if selected_indices is None:
        rows_to_write = range(len(hashes))
    else:
        rows_to_write = selected_indices

    # xlwings Range uses 0-based indexing for __getitem__.
    # Our col_idx from Excel ListColumns is 1-based, so convert it.
    col0 = col_idx - 1

    for i in rows_to_write:
        body[i, col0].value = hashes[i]


def _ensure_table_rows(table: Table, n_rows: int) -> None:
    """Ensure a ListObject table has exactly n_rows body rows."""

    api = table.api
    list_rows = api.ListRows

    # Delete extra rows (from bottom).
    while list_rows.Count > n_rows:
        list_rows(list_rows.Count).Delete()

    # Add missing rows.
    while list_rows.Count < n_rows:
        list_rows.Add()


def _write_index_hash_to_output_table(
    book: xw.Book,
    inputs: Tuple[SimCase, ...],
    hashes: list[str],
    selected_indices: tuple[int, ...] | None,
    table_key: str = _OUTPUT_TABLE,
) -> None:
    output_table: Table = find_table(book, table_key)

    # Ensure output has the same number of rows as inputs.
    _ensure_table_rows(output_table, len(inputs))

    col_index = _ensure_table_column(output_table, "index")
    col_hash = _ensure_table_column(output_table, "hash")

    body = output_table.data_body_range
    if body is None:
        return

    col0_index = col_index - 1
    col0_hash = col_hash - 1

    if selected_indices is None:
        rows_to_write = range(len(inputs))
    else:
        rows_to_write = selected_indices

    for i in rows_to_write:
        # Excel-side index is 1-based.
        body[i, col0_index].value = inputs[i].row_idx + 1
        body[i, col0_hash].value = hashes[i]


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


_DIR_COMPONENTS = {
    "X",
    "Y",
    "Z",
    "XX",
    "XY",
    "XZ",
    "YX",
    "YY",
    "YZ",
    "ZX",
    "ZY",
    "ZZ",
}


def _normalize_header_key(header: Any) -> str:
    """Normalize an Excel column header to snake_case.

    Rule: everything is lower-case except direction/tensor components,
    which stay uppercase (X, Y, Z, XX, XY, XZ, ...).
    """

    s = str(header).strip()
    if not s:
        return s

    raw_tokens = [t for t in s.split("_") if t]

    out: list[str] = []
    for t in raw_tokens:
        tu = t.upper()
        if tu in _DIR_COMPONENTS:
            out.append(tu)
        else:
            out.append(t.lower())

    return "_".join(out)


def _validate_header_key(header: Any) -> str:
    """Validate that an Excel header already follows our naming convention.

    Disallows legacy space-based headers (e.g. "Cell Size X").
    """

    s = str(header).strip()
    if not s:
        raise ValueError("Empty Excel header")

    if " " in s:
        raise ValueError(
            f"Excel header {s!r} contains spaces. "
            "Use snake_case (e.g. 'cell_size_X')."
        )

    normalized = _normalize_header_key(s)
    if s != normalized:
        raise ValueError(
            f"Excel header {s!r} is not in canonical form {normalized!r}."
        )

    return s


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
                        model=read_str(
                            row_values, "element_type"
                        )
                    ),
                    profile=build_profile_params(
                        element_model=read_str(
                            row_values, "element_type"
                        ),
                        radius=read_float(
                            row_values, "radius_multiplier"
                        ),
                        kappa=read_optional_float(
                            row_values, "kappa"
                        ),
                    ),
                    geometry=GeometryParams(
                        cell_name=resolve_cell_name(
                            read_str(
                                row_values, "cell_name"
                            )
                        ),
                        size=read_Vector3(
                            row_values, "cell_size"
                        ),
                    ),
                    meshing=MeshingParams(
                        max_element_size=read_float(
                            row_values, "max_element_size"
                        )
                    ),
                ),
                post_mesh_spec=PostMeshSpec(
                    material=MaterialParams(
                        e_mod=read_float(
                            row_values, "elastic_modulus"
                        ),
                        nu=read_float(
                            row_values, "poisson_ratio"
                        ),
                        density=read_float(
                            row_values, "density"
                        ),
                    ),
                    setup=SetupParams(
                        sim_type=read_str(
                            row_values, "simulation_type"
                        ),
                        strain=read_float(
                            row_values, "strain"
                        ),
                        n_substeps=read_int(
                            row_values, "substeps"
                        ),
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

    keys = [_validate_header_key(h) for h in input_header]

    if len(set(keys)) != len(keys):
        dupes = {k for k in keys if keys.count(k) > 1}
        raise ValueError(
            "Duplicate Excel headers: "
            + ", ".join(sorted(dupes))
        )

    return dict(zip(keys, row))
