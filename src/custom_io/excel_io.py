# excel_io.py

import json
from contextlib import suppress
from pathlib import Path
from typing import Any, Protocol, TypeVar

import numpy as np
import xlwings as xw  # type: ignore[import-not-found]
from xlwings.main import Table  # type: ignore[import-not-found]

from core.hashing import sha1_hex

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
from custom_io.apdl_io import mapdl_session, run_commands, write_apdl_macro
from custom_io.excel_read import (
    read_float,
    read_int,
    read_optional_float,
    read_str,
    read_Vector3,
)
from custom_io.lgf_io import resolve_cell_name
from custom_io.path_config import (
    PathConfig,
    default_config,
    get_path_config,
    set_path_config,
)
from pipeline import build_pipeline
from postprocess.output_spec import (
    POSTPROCESS_OUTPUT_SPEC,
    is_postprocess_output_allowed,
)
from postprocess.pipeline import postprocess_commands

_INPUT_TABLE = "t_input"
_OUTPUT_TABLE = "t_output"
_CONFIG_TABLE = "t_config"

# UI: lightweight progress indicator column (outside the t_input table)
# For a running case at table body row i, we write to e.g. A{excel_row}.
_STATUS_COL = "A"
_PENDING_MARK = "…"
_DONE_MARK = "✔"
_FAIL_MARK = "✘"
_SKIP_MARK = "➥"

# Status cell styling (RGB)
_PENDING_COLOR = (235, 235, 235)  # light gray
_RUNNING_COLOR = (255, 242, 204)  # light yellow
_DONE_COLOR = (198, 239, 206)  # light green
_FAIL_COLOR = (255, 199, 206)  # light red
_SKIP_COLOR = (221, 235, 247)  # light blue

# Status font colors (RGB)
_PENDING_FONT = (90, 90, 90)  # dark gray
_RUNNING_FONT = (156, 101, 0)  # dark orange/brown
_DONE_FONT = (0, 97, 0)  # dark green
_FAIL_FONT = (156, 0, 6)  # dark red
_SKIP_FONT = (31, 78, 121)  # dark blue


def _doevents(book: xw.Book) -> None:
    """Let Excel process UI events (best-effort).

    This helps Excel repaint the sheet after .value updates.
    """

    with suppress(Exception):
        book.app.api.Run("DoEvents")


def _rgb_to_excel_color(rgb: tuple[int, int, int]) -> int:
    """Convert (R,G,B) to Excel/VBA Color integer (BGR)."""

    r, g, b = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    return (b << 16) | (g << 8) | r


def _style_status_cell(
    cell: xw.Range,
    *,
    fill_rgb: tuple[int, int, int],
    font_rgb: tuple[int, int, int] | None = None,
    bold: bool = False,
) -> None:
    with suppress(Exception):
        cell.color = fill_rgb
    with suppress(Exception):
        if font_rgb is not None:
            cell.api.Font.Color = _rgb_to_excel_color(font_rgb)
    with suppress(Exception):
        cell.api.Font.Bold = bool(bold)
    with suppress(Exception):
        cell.api.HorizontalAlignment = -4108  # xlCenter


def _set_status_pending(book: xw.Book, cell: xw.Range | None) -> None:
    if cell is None:
        return
    cell.value = _PENDING_MARK
    _style_status_cell(cell, fill_rgb=_PENDING_COLOR, font_rgb=_PENDING_FONT, bold=True)
    _doevents(book)


def _set_status_running(book: xw.Book, cell: xw.Range | None) -> None:
    if cell is None:
        return
    # Mirror the global spinner cell (Sheet1!A1) while this case runs.
    cell.formula = "=Sheet1!$A$1"
    _style_status_cell(cell, fill_rgb=_RUNNING_COLOR, font_rgb=_RUNNING_FONT)
    _doevents(book)


def _set_status_done(book: xw.Book, cell: xw.Range | None) -> None:
    if cell is None:
        return
    cell.value = _DONE_MARK
    _style_status_cell(cell, fill_rgb=_DONE_COLOR, font_rgb=_DONE_FONT)
    _doevents(book)


def _set_status_fail(book: xw.Book, cell: xw.Range | None) -> None:
    if cell is None:
        return
    cell.value = _FAIL_MARK
    _style_status_cell(cell, fill_rgb=_FAIL_COLOR, font_rgb=_FAIL_FONT)
    _doevents(book)


def _set_status_skip(book: xw.Book, cell: xw.Range | None) -> None:
    if cell is None:
        return
    cell.value = _SKIP_MARK
    _style_status_cell(cell, fill_rgb=_SKIP_COLOR, font_rgb=_SKIP_FONT)
    _doevents(book)


class DataclassType(Protocol):
    __dataclass_fields__: dict[str, Any]


T = TypeVar("T", bound=DataclassType)


class DataclassInstance(Protocol):
    __dataclass_fields__: dict[str, Any]


Header = tuple[str, ...]
Body = tuple[tuple[Any, ...], ...]


def _apply_path_config_from_book(book: xw.Book) -> None:
    """Apply runtime path config from Excel `t_config` (if present).

    We interpret values *as-is* (no '~' expansion). If a value is provided, it
    must be an absolute path.

    Expected columns in `t_config` (first row is used):
      - lgf
      - artifacts
      - results
      - compute_policy  (cache|recompute|smart)

    Missing table/columns/cells fall back to repo defaults.
    """

    repo_root = Path(__file__).resolve().parents[2]
    cfg = default_config(repo_root)

    try:
        table = find_table(book, _CONFIG_TABLE)
    except KeyError:
        set_path_config(cfg)
        return

    header, body = get_table_data(table)
    if not body:
        set_path_config(cfg)
        return

    row0 = body[0]
    col_index = {str(h).strip().lower(): i for i, h in enumerate(header)}

    def read_abs(col: str) -> Path | None:
        i = col_index.get(col)
        if i is None or i >= len(row0):
            return None
        v = row0[i]
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        p = Path(s)
        if not p.is_absolute():
            raise ValueError(f"t_config.{col} must be an absolute path (got {s!r})")
        return p

    lgf_root = read_abs("lgf") or cfg.lgf_root
    artifacts_root = read_abs("artifacts") or cfg.artifacts_root
    results_root = read_abs("results") or cfg.results_root

    compute_policy_raw = "smart"
    i_pol = col_index.get("compute_policy")
    if i_pol is not None and i_pol < len(row0):
        v = row0[i_pol]
        if v is not None and str(v).strip():
            compute_policy_raw = str(v).strip().lower()

    if compute_policy_raw not in {"cache", "recompute", "smart"}:
        raise ValueError(
            f"t_config.compute_policy must be one of cache/recompute/smart (got {compute_policy_raw!r})"
        )

    set_path_config(
        PathConfig(
            repo_root=cfg.repo_root,
            lgf_root=lgf_root,
            artifacts_root=artifacts_root,
            results_root=results_root,
            compute_policy=compute_policy_raw,
        )
    )


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

    _apply_path_config_from_book(book)

    input_table: Table = find_table(book, _INPUT_TABLE)
    input_header, input_body = get_table_data(input_table)

    inputs: tuple[SimCase, ...] = _get_simulation_cases(input_header, input_body)

    hashes = [build_case_hash(sc.to_string()) for sc in inputs]

    # Write case hashes back into the Excel input table (t_input) so each row
    # records the exact case identifier used on disk.
    _write_hashes_to_input_table(
        input_table,
        hashes,
        selected_indices=selected_indices,
        column_name="hash",
    )

    if selected_indices is None:
        # When running from Excel, we want intermediate artifacts (geometry_db,
        # mesh_db, lattice JSON, etc.) for debugging/reuse.
        run_cases(book, inputs, save_intermediate=True)
        return

    selected: list[SimCase] = []
    selected_set = set(selected_indices)
    for i, sim_case in enumerate(inputs):
        if i in selected_set:
            selected.append(sim_case)

    # When running from Excel, we want intermediate artifacts (geometry_db,
    # mesh_db, lattice JSON, etc.) for debugging/reuse.
    run_cases(book, tuple(selected), save_intermediate=True)


def run_selected_postprocess(
    book: xw.Book,
    selected_indices: tuple[int, ...] | None = None,
) -> None:
    _apply_path_config_from_book(book)

    input_table: Table = find_table(book, _INPUT_TABLE)
    input_header, input_body = get_table_data(input_table)

    inputs: tuple[SimCase, ...] = _get_simulation_cases(input_header, input_body)

    output_table: Table = find_table(book, _OUTPUT_TABLE)
    # Ensure output has the same number of rows as inputs so row_idx lookups are valid.
    _ensure_table_rows(output_table, len(inputs))
    output_header, _output_body = get_table_data(output_table)

    if selected_indices is None:
        run_postprocess(book, inputs, output_header)
        return

    selected: list[SimCase] = []
    selected_set = set(selected_indices)
    for i, sim_case in enumerate(inputs):
        if i in selected_set:
            selected.append(sim_case)

    run_postprocess(book, tuple(selected), output_header)


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
    areas = areas_obj if areas_obj is not None else [sel_any]

    idxs: set[int] = set()
    for area in areas:
        r0 = area.row
        r1 = area.row + area.rows.count - 1
        rr0 = max(r0, body_first_row)
        rr1 = min(r1, body_last_row)
        for r in range(rr0, rr1 + 1):
            idxs.add(r - body_first_row)

    return tuple(sorted(idxs)) if idxs else None


def _read_json(path: Path) -> dict[str, Any] | None:
    with suppress(Exception):
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _meta_matches(
    path: Path, *, key_field: str, hash_field: str, key: str, h: str
) -> bool:
    meta = _read_json(path)
    if not isinstance(meta, dict):
        return False
    return str(meta.get(key_field, "")) == key and str(meta.get(hash_field, "")) == h


def _is_case_solved(
    *,
    run_dir: Path,
    case_meta_path: Path,
    case_key: str,
    case_hash: str,
) -> bool:
    if not (run_dir / "case.db").exists():
        return False
    if not (run_dir / "case.rst").exists():
        return False
    if not case_meta_path.exists():
        return False
    return _meta_matches(
        case_meta_path,
        key_field="case_key",
        hash_field="case_hash",
        key=case_key,
        h=case_hash,
    )


def run_cases(
    book: xw.Book,
    inputs: tuple[SimCase, ...],
    save_intermediate: bool = False,
):
    cfg = get_path_config()
    base_run_dir = cfg.results_root / "case"
    case_artifacts_root = cfg.artifacts_root / "case"

    # Keep a single MAPDL session open and switch working directory per case.
    session_dir = base_run_dir / "__mapdl_session"
    session_dir.mkdir(parents=True, exist_ok=True)

    # Use a stable, non-hash jobname so result filenames don't include the case hash.
    jobname = "case"

    try:
        # Mark all selected rows as pending up-front.
        for sim_case in inputs:
            _set_status_pending(
                book,
                _status_range_for_input_row(book, int(sim_case.row_idx)),
            )

        with mapdl_session(
            run_location=str(session_dir),
            jobname=jobname,
            cleanup_on_exit=False,
        ) as mapdl:
            for sim_case in inputs:
                status_cell = _status_range_for_input_row(book, int(sim_case.row_idx))
                _set_status_running(book, status_cell)

                case_key = sim_case.to_string()
                case_hash = build_case_hash(case_key)

                run_dir = base_run_dir / f"{case_hash}"
                run_dir.mkdir(parents=True, exist_ok=True)

                # Save sim_case metadata alongside results for reproducibility.
                sim_case_path = case_artifacts_root / case_hash / "sim_case.json"
                sim_case_path.parent.mkdir(parents=True, exist_ok=True)
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
                            o.tolist() if hasattr(o, "tolist") else vars(o)
                        ),
                    ),
                    encoding="utf-8",
                )

                print(sim_case.to_string())

                # If smart/cache and this case is already solved, skip.
                case_meta_path = case_artifacts_root / case_hash / "sim_case.json"
                compute_policy = str(getattr(cfg, "compute_policy", "smart")).lower()

                if compute_policy in {"smart", "cache"} and _is_case_solved(
                    run_dir=run_dir,
                    case_meta_path=case_meta_path,
                    case_key=case_key,
                    case_hash=case_hash,
                ):
                    _set_status_skip(book, status_cell)
                    continue

                # Decide whether to reuse geometry/mesh caches.
                from custom_io.geometry_io import (
                    geometry_db_dir,
                    geometry_hash,
                    geometry_key,
                    import_geometry_db,
                )
                from custom_io.mesh_io import (
                    export_mesh_cdb,
                    export_mesh_db,
                    import_mesh_db,
                    mesh_db_dir,
                    mesh_hash,
                    mesh_key,
                )
                from material.pipeline import material_commands
                from setup.pipeline import setup_commands
                from solve.pipeline import solver_commands
                from meshing.pipeline import meshing_commands

                mesh_dir = mesh_db_dir(sim_case)
                mesh_meta = mesh_dir / "sim_case.json"
                mesh_db = mesh_dir / "mesh.db"
                mesh_ok = mesh_db.exists() and _meta_matches(
                    mesh_meta,
                    key_field="mesh_key",
                    hash_field="mesh_hash",
                    key=mesh_key(sim_case),
                    h=mesh_hash(sim_case),
                )

                geom_dir = geometry_db_dir(sim_case)
                geom_meta = geom_dir / "sim_case.json"
                geom_db = geom_dir / "geometry.db"
                geom_ok = geom_db.exists() and _meta_matches(
                    geom_meta,
                    key_field="geometry_key",
                    hash_field="geometry_hash",
                    key=geometry_key(sim_case),
                    h=geometry_hash(sim_case),
                )

                # cache policy: if no reusable caches, skip.
                if compute_policy == "cache" and not (mesh_ok or geom_ok):
                    _set_status_skip(book, status_cell)
                    continue

                # Switch MAPDL working directory so all solver files are
                # written under this case.
                cwd_cmds = (f"/CWD,'{run_dir.as_posix()}'",)
                run_commands(mapdl, cwd_cmds)

                # Build the solve pipeline depending on cache availability.
                if compute_policy in {"smart", "cache"} and mesh_ok:
                    # Fast path: import mesh DB, then apply material/setup/solve.
                    # We still compute unit_cell in Python for setup naming.
                    from preprocess.pipeline import lattice_to_unit_cell, lgf_to_lattice
                    from custom_io.lgf_io import import_lgf

                    lattice = lgf_to_lattice(
                        import_lgf(sim_case.pre_mesh_spec.geometry.cell_name)
                    )
                    unit_cell = lattice_to_unit_cell(lattice)

                    pipeline = (
                        ("/CLEAR,START", "/UNITS,MPA", "/PREP7")
                        + import_mesh_db(sim_case)
                        + material_commands(sim_case.post_mesh_spec.material)
                        + setup_commands(
                            unit_cell,
                            sim_case.pre_mesh_spec.profile,
                            sim_case.pre_mesh_spec.geometry,
                            sim_case.post_mesh_spec.setup,
                        )
                        + solver_commands(sim_case.post_mesh_spec.setup)
                        + ("SAVE,'case','db'",)
                    )
                elif compute_policy in {"smart", "cache"} and geom_ok:
                    # Mid path: import geometry DB, then mesh + material/setup/solve.
                    from preprocess.pipeline import lattice_to_unit_cell, lgf_to_lattice
                    from custom_io.lgf_io import import_lgf

                    lattice = lgf_to_lattice(
                        import_lgf(sim_case.pre_mesh_spec.geometry.cell_name)
                    )
                    unit_cell = lattice_to_unit_cell(lattice)

                    pipeline = (
                        ("/CLEAR,START", "/UNITS,MPA", "/PREP7")
                        + import_geometry_db(sim_case)
                        + meshing_commands(
                            unit_cell,
                            sim_case.pre_mesh_spec.geometry,
                            sim_case.pre_mesh_spec.profile,
                            sim_case.pre_mesh_spec.meshing,
                        )
                        + (
                            (export_mesh_db(sim_case) + export_mesh_cdb(sim_case))
                            if save_intermediate
                            else ()
                        )
                        + material_commands(sim_case.post_mesh_spec.material)
                        + setup_commands(
                            unit_cell,
                            sim_case.pre_mesh_spec.profile,
                            sim_case.pre_mesh_spec.geometry,
                            sim_case.post_mesh_spec.setup,
                        )
                        + solver_commands(sim_case.post_mesh_spec.setup)
                        + ("SAVE,'case','db'",)
                    )
                else:
                    # Full recompute.
                    pipeline = build_pipeline(
                        sim_case,
                        save_intermediate=save_intermediate,
                    )

                # Ensure jobname is set after /CLEAR inside the pipeline.
                pipeline = pipeline[:1] + ("/FILNAME,case",) + pipeline[1:]

                # Save full solve command stream for reproducibility.
                write_apdl_macro(
                    case_artifacts_root / case_hash / "main.mac",
                    cwd_cmds + pipeline,
                    title="solve",
                    metadata={
                        "case_hash": case_hash,
                        "jobname": jobname,
                    },
                )

                try:
                    run_commands(mapdl, pipeline)
                except Exception:
                    _set_status_fail(book, status_cell)
                    raise

                _set_status_done(book, status_cell)
    except Exception as e:
        print(f"Error: {e}")
        raise


def run_postprocess(
    book: xw.Book,
    inputs: tuple[SimCase, ...],
    output_header: Header,
) -> None:
    """Run postprocessing for the given cases.

    This derives required outputs from the Excel `t_output` header and validates
    them against `POSTPROCESS_OUTPUT_SPEC`.

    The derived mapping is `prefix -> n_components` where `n_components` must be
    one of {1,3,6,9}.
    """

    cfg = get_path_config()
    base_run_dir = cfg.results_root / "case"
    case_artifacts_root = cfg.artifacts_root / "case"

    needed: dict[str, int] = {}
    component_sets: dict[str, set[str]] = {}

    for col in output_header:
        name = str(col).strip()
        if not name:
            continue

        if "_" in name:
            prefix, suffix = name.rsplit("_", 1)
            if suffix in _DIR_COMPONENTS:
                component_sets.setdefault(prefix, set()).add(suffix)
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
            raise ValueError(f"t_output is missing required scalar column {req!r}.")

    # Prepare output table writer.
    from custom_io.excel_write import WriteQueue

    output_table: Table = find_table(book, _OUTPUT_TABLE)
    q = WriteQueue()

    # Keep a single MAPDL session open and switch working directory per case.
    session_dir = base_run_dir / "__mapdl_postprocess_session"
    session_dir.mkdir(parents=True, exist_ok=True)
    jobname = "case"

    try:
        # Mark all selected rows as pending up-front.
        for sim_case in inputs:
            _set_status_pending(
                book,
                _status_range_for_input_row(book, int(sim_case.row_idx)),
            )

        with mapdl_session(
            run_location=str(session_dir),
            jobname=jobname,
            cleanup_on_exit=False,
        ) as mapdl:
            # Run per-case postprocess APDL and queue requested results.
            for sim_case in inputs:
                status_cell = _status_range_for_input_row(book, int(sim_case.row_idx))
                _set_status_running(book, status_cell)

                # Validate postprocess outputs against this case's simulation_type.
                # Policy: run MAPDL postprocess for outputs that are allowed for
                # this simulation_type, and write #N/A (=NA()) for disallowed
                # outputs.
                sim_type = sim_case.post_mesh_spec.setup.sim_type

                allowed_needed: dict[str, int] = {
                    p: n
                    for p, n in needed.items()
                    if is_postprocess_output_allowed(p, sim_type)
                }
                disallowed = [p for p in needed.keys() if p not in allowed_needed]

                from custom_io.excel_write import EXCEL_NA

                row0 = int(sim_case.row_idx)

                # Always write required scalars.
                case_key = sim_case.to_string()
                case_hash = build_case_hash(case_key)
                if "index" in needed:
                    q.add_int(row0, "index", row0 + 1)
                if "hash" in needed:
                    q.add_str(row0, "hash", case_hash)

                # Write #N/A for unsupported outputs.
                for p in disallowed:
                    ncomp = needed.get(p, 1)
                    if ncomp == 1:
                        q.add_float(row0, p, EXCEL_NA)
                    elif ncomp == 6:
                        q.add_values(
                            row0,
                            {
                                f"{p}_X": EXCEL_NA,
                                f"{p}_Y": EXCEL_NA,
                                f"{p}_Z": EXCEL_NA,
                                f"{p}_XY": EXCEL_NA,
                                f"{p}_YZ": EXCEL_NA,
                                f"{p}_XZ": EXCEL_NA,
                            },
                        )
                    elif ncomp == 9:
                        q.add_values(
                            row0,
                            {
                                f"{p}_XX": EXCEL_NA,
                                f"{p}_XY": EXCEL_NA,
                                f"{p}_XZ": EXCEL_NA,
                                f"{p}_YX": EXCEL_NA,
                                f"{p}_YY": EXCEL_NA,
                                f"{p}_YZ": EXCEL_NA,
                                f"{p}_ZX": EXCEL_NA,
                                f"{p}_ZY": EXCEL_NA,
                                f"{p}_ZZ": EXCEL_NA,
                            },
                        )
                    else:
                        # For any future component counts, fall back to scalar #N/A.
                        q.add_float(row0, p, EXCEL_NA)

                # If nothing beyond index/hash is allowed, just flush the N/A
                # values and move on.
                nontrivial_allowed = [
                    p for p in allowed_needed.keys() if p not in ("index", "hash")
                ]
                if not nontrivial_allowed:
                    q.flush(output_table)
                    _set_status_done(book, status_cell)
                    continue

                case_key = sim_case.to_string()
                case_hash = build_case_hash(case_key)
                run_dir = base_run_dir / f"{case_hash}"

                # Switch to the case working directory, restore DB, attach RST.
                # This avoids restarting MAPDL for each postprocess run.
                prelude = (
                    f"/CWD,'{run_dir.as_posix()}'",
                    "FINISH",
                    "/CLEAR",
                    "RESUME,'case','db'",
                )
                run_commands(mapdl, prelude)

                pipeline = postprocess_commands(
                    sim_case=sim_case,
                    needed=allowed_needed,
                )

                # Save full postprocess command stream for reproducibility.
                write_apdl_macro(
                    case_artifacts_root / case_hash / "post.mac",
                    prelude + pipeline,
                    title="postprocess",
                    metadata={
                        "case_hash": case_hash,
                        "jobname": jobname,
                        "needed": ",".join(sorted(allowed_needed.keys())),
                    },
                )

                try:
                    run_commands(mapdl, pipeline)
                except Exception:
                    _set_status_fail(book, status_cell)
                    raise

                _set_status_done(book, status_cell)

                # Queue outputs
                row0 = int(sim_case.row_idx)

                if "index" in allowed_needed:
                    q.add_int(row0, "index", row0 + 1)

                if "hash" in allowed_needed:
                    q.add_str(row0, "hash", case_hash)

                if "volume" in allowed_needed:
                    q.add_float(row0, "volume", mapdl.parameters["pp_volume"])

                if "boundary_traction" in allowed_needed:
                    q.add_Vector3x3(
                        row0,
                        "boundary_traction",
                        mapdl.parameters["pp_boundary_traction"],
                    )

                if "boundary_force" in allowed_needed:
                    q.add_Vector3x3(
                        row0,
                        "boundary_force",
                        mapdl.parameters["pp_boundary_force"],
                    )

                if "boundary_moment" in allowed_needed:
                    q.add_Vector3x3(
                        row0,
                        "boundary_moment",
                        mapdl.parameters["pp_boundary_moment"],
                    )

                if "boundary_stress" in allowed_needed:
                    q.add_Vector6(
                        row0,
                        "boundary_stress",
                        mapdl.parameters["pp_boundary_stress"],
                    )

                if "volume_stress" in allowed_needed:
                    q.add_Vector6(
                        row0,
                        "volume_stress",
                        mapdl.parameters["pp_volume_stress"],
                    )

                if "volume_avg_stress" in allowed_needed:
                    vol = float(mapdl.parameters["pp_volume"])
                    vs = mapdl.parameters["pp_volume_stress"]
                    if hasattr(vs, "ravel"):
                        vs6 = [float(x) for x in vs.ravel().tolist()]
                    else:
                        vs6 = [float(x) for x in vs]
                    if vol == 0.0:
                        avg6 = [float("nan")] * 6
                    else:
                        avg6 = [x / vol for x in vs6]

                    q.add_Vector6(
                        row0,
                        "volume_avg_stress",
                        np.asarray(avg6, dtype=float),
                    )

                if "volume_energy" in allowed_needed:
                    q.add_float(
                        row0, "volume_energy", mapdl.parameters["pp_volume_energy"]
                    )

                if "volume_avg_energy" in allowed_needed:
                    vol = float(mapdl.parameters["pp_volume"])
                    ve = float(mapdl.parameters["pp_volume_energy"])
                    if vol == 0.0:
                        q.add_float(row0, "volume_avg_energy", float("nan"))
                    else:
                        q.add_float(row0, "volume_avg_energy", ve / vol)

                # Modal resonant frequencies (mode 1..20)
                for i in range(1, 21):
                    key = f"res_freq_{i}"
                    if key in allowed_needed:
                        q.add_float(row0, key, mapdl.parameters[f"pp_res_freq_{i}"])

                q.flush(output_table)
    except Exception as e:
        print(f"Error: {e}")
        raise

    # Note: we flush after each case for more responsive Excel updates.


def build_case_hash(key: str) -> str:
    return sha1_hex(key)


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


def find_table(
    book: xw.Book,
    key: str,
) -> Table:
    table, _sheet = find_table_and_sheet(book, key)
    return table


def find_table_and_sheet(
    book: xw.Book,
    key: str,
) -> tuple[Table, xw.Sheet]:
    for sheet in book.sheets:
        for table in sheet.tables:
            if table.name == key or table.display_name == key:
                return table, sheet

    raise KeyError(f"Could not find Excel table {key!r}")


def _status_range_for_input_row(book: xw.Book, row_idx: int) -> xw.Range | None:
    """Return the status cell range for a given t_input body row.

    We write to a fixed column (default: X) on the same sheet that contains
    `t_input`, at the Excel row corresponding to `row_idx` in the table body.
    """

    try:
        t, sheet = find_table_and_sheet(book, _INPUT_TABLE)
    except KeyError:
        return None

    body = t.data_body_range
    if body is None:
        return None

    excel_row = int(body.row) + int(row_idx)
    addr = f"{_STATUS_COL}{excel_row}"

    try:
        return sheet.range(addr)
    except Exception:
        return None


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
            f"Excel header {s!r} contains spaces. Use snake_case (e.g. 'cell_size_X')."
        )

    normalized = _normalize_header_key(s)
    if s != normalized:
        raise ValueError(f"Excel header {s!r} is not in canonical form {normalized!r}.")

    return s


def _get_simulation_cases(
    input_header: Header,
    input_body: Body,
) -> tuple[SimCase, ...]:
    cases: list[SimCase] = []

    for i, row in enumerate(input_body):
        row_values = _map_header_to_row_values(input_header, row)

        cases.append(
            SimCase(
                row_idx=i,
                pre_mesh_spec=PreMeshSpec(
                    element_type=ElementTypeParams(
                        model=read_str(row_values, "element_type")
                    ),
                    profile=build_profile_params(
                        element_model=read_str(row_values, "element_type"),
                        radius=read_float(row_values, "radius_multiplier"),
                        kappa=read_optional_float(row_values, "kappa"),
                        joint_area_factor=(
                            read_optional_float(row_values, "joint_area_factor") or 1.0
                        ),
                        joint_length_factor=(
                            read_optional_float(row_values, "joint_length_factor")
                            or 1.0
                        ),
                        joint_bending_factor=(
                            read_optional_float(row_values, "joint_bending_factor")
                            or 1.0
                        ),
                        joint_torsion_factor=(
                            read_optional_float(row_values, "joint_torsion_factor")
                            or 1.0
                        ),
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


def _map_header_to_row_values(
    input_header: Header,
    row: tuple[Any, ...],
) -> dict[str, Any]:
    if len(input_header) != len(row):
        raise ValueError(
            f"Header and row lengths do not match: {len(input_header)} != {len(row)}"
        )

    keys = [_validate_header_key(h) for h in input_header]

    if len(set(keys)) != len(keys):
        dupes = {k for k in keys if keys.count(k) > 1}
        raise ValueError("Duplicate Excel headers: " + ", ".join(sorted(dupes)))

    return dict(zip(keys, row, strict=True))
