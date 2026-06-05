#cases.py
"""Module for cases functionality in src.custom_io.excel."""

from __future__ import annotations

from typing import Any

from core.parameters.element_type_params import ElementTypeParams
from core.parameters.geometry_params import GeometryParams
from core.parameters.material_params import MaterialParams
from core.parameters.meshing_params import MeshingParams
from core.parameters.profile_params import build_profile_params
from core.parameters.setup_params import SetupParams
from core.parameters.sim_case import PostMeshSpec, PreMeshSpec, SimCase
from custom_io.excel.read import (
    read_Vector3,
    read_float,
    read_int,
    read_optional_float,
    read_str,
)
from custom_io.excel.tables import Body, Header
from custom_io.lgf_io import resolve_cell_name

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


def get_simulation_cases(input_header: Header, input_body: Body) -> tuple[SimCase, ...]:
    """Convert Excel input table rows into simulation case objects.

    Parameters
    ----------
    input_header : Header
        Column names from the ``t_input`` table.
    input_body : Body
        Data rows from the ``t_input`` table.

    Returns
    -------
    tuple[SimCase, ...]
        Parsed simulation cases with zero-based row indices.

    Raises
    ------
    ValueError
        If headers are invalid, duplicated, or row values cannot be parsed.
    """

    cases: list[SimCase] = []

    for i, row in enumerate(input_body):
        row_values = _map_header_to_row_values(input_header, row)
        element_type = read_str(row_values, "element_type")

        cases.append(
            SimCase(
                row_idx=i,
                pre_mesh_spec=PreMeshSpec(
                    element_type=ElementTypeParams(model=element_type),
                    profile=build_profile_params(
                        element_model=element_type,
                        radius=read_float(row_values, "radius_multiplier"),
                        kappa=read_optional_float(row_values, "kappa"),
                    ),
                    geometry=GeometryParams(
                        cell_name=resolve_cell_name(read_str(row_values, "cell_name")),
                        size=read_Vector3(row_values, "cell_size"),
                    ),
                    meshing=MeshingParams(
                        max_element_size=read_float(row_values, "max_element_size")
                    ),
                ),
                post_mesh_spec=PostMeshSpec(
                    material=MaterialParams(
                        e_mod=read_float(row_values, "elastic_modulus"),
                        nu=read_float(row_values, "poisson_ratio"),
                        density=read_float(row_values, "density"),
                    ),
                    setup=SetupParams(
                        sim_type=read_str(row_values, "simulation_type"),
                        strain=read_float(row_values, "strain"),
                        n_substeps=read_int(row_values, "substeps"),
                    ),
                ),
            )
        )

    return tuple(cases)


def _map_header_to_row_values(input_header: Header, row: tuple[Any, ...]) -> dict[str, Any]:
    """Map one Excel row to canonical header keys.

    Parameters
    ----------
    input_header : Header
        Table headers to validate and use as dictionary keys.
    row : tuple[Any, ...]
        One row of table values.

    Returns
    -------
    dict[str, Any]
        Mapping from canonical header names to row values.
    """

    if len(input_header) != len(row):
        raise ValueError(
            f"Header and row lengths do not match: {len(input_header)} != {len(row)}"
        )

    keys = [_validate_header_key(h) for h in input_header]

    if len(set(keys)) != len(keys):
        dupes = {k for k in keys if keys.count(k) > 1}
        raise ValueError("Duplicate Excel headers: " + ", ".join(sorted(dupes)))

    return dict(zip(keys, row, strict=True))


def _validate_header_key(header: Any) -> str:
    """Validate an Excel header against the project naming convention.

    Parameters
    ----------
    header : Any
        Raw Excel header value.

    Returns
    -------
    str
        Canonical header string.

    Raises
    ------
    ValueError
        If the header is empty, contains spaces, or is not canonical.
    """

    s = str(header).strip()
    if not s:
        raise ValueError("Empty Excel header")

    if " " in s:
        raise ValueError(
            f"Excel header {s!r} contains spaces. Use snake_case (e.g. 'cell_size_X')."
        )

    normalized = _normalize_header_key(s)
    if s != normalized:
        raise ValueError(f"Excel header {s!r} is not in canonical form {normalized!r}.")

    return s


def _normalize_header_key(header: Any) -> str:
    """Normalize a header while preserving tensor direction suffixes.

    Parameters
    ----------
    header : Any
        Raw header value to normalize.

    Returns
    -------
    str
        Snake-case header where direction tokens such as ``X`` and ``XY`` stay
        uppercase.
    """

    s = str(header).strip()
    if not s:
        return s

    raw_tokens = [t for t in s.split("_") if t]
    out: list[str] = []
    for token in raw_tokens:
        upper_token = token.upper()
        if upper_token in _DIR_COMPONENTS:
            out.append(upper_token)
        else:
            out.append(token.lower())

    return "_".join(out)
