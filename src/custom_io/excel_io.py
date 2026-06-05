#excel_io.py
"""Module for excel io functionality in src.custom_io."""

import json
from contextlib import suppress
from pathlib import Path
from typing import Any

import xlwings as xw  # type: ignore[import-not-found]
from xlwings.main import Table  # type: ignore[import-not-found]

from core.parameters.sim_case import SimCase
from custom_io.case_hash import build_case_hash
from custom_io.mapdl.apdl_io import mapdl_session, run_commands, write_apdl_macro
from custom_io.mapdl.batch import MapdlBatchRunner
from custom_io.post.aggregate import write_aggregate_rows
from custom_io.excel.cases import get_simulation_cases as _get_simulation_cases
from custom_io.excel.config import apply_path_config_from_book as _apply_path_config_from_book
from custom_io.excel.status import (
    set_status_done as _set_status_done,
    set_status_fail as _set_status_fail,
    set_status_pending as _set_status_pending,
    set_status_running as _set_status_running,
    set_status_skip as _set_status_skip,
    status_range_for_input_row as _status_range_for_input_row,
)
from custom_io.excel.tables import Body, Header, find_table, find_table_and_sheet, get_table_data
from custom_io.excel.ui_heartbeat import UIHeartbeat
from custom_io.path_config import get_path_config
from pipeline import build_pipeline
from post.output_spec import is_post_output_allowed
from post.pipeline import post_commands

_INPUT_TABLE = "t_input"
_OUTPUT_TABLE = "t_out"  # long-format output table (required)


def run_selected(
    book: xw.Book,
    selected_indices: tuple[int, ...] | None = None,
) -> None:
    """Run selected simulation cases from the Excel input table.

    Parameters
    ----------
    book : xw.Book
        Calling xlwings workbook containing ``t_input``.
    selected_indices : tuple[int, ...] or None, optional
        Zero-based indices into the input table. If ``None``, all cases are
        solved.
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
    """Run postprocessing for selected simulation cases.

    Parameters
    ----------
    book : xw.Book
        Calling xlwings workbook containing ``t_input`` and ``t_out``.
    selected_indices : tuple[int, ...] or None, optional
        Zero-based input table row indices to postprocess. If ``None``, all
        cases are postprocessed.
    """

    _apply_path_config_from_book(book)

    input_table: Table = find_table(book, _INPUT_TABLE)
    input_header, input_body = get_table_data(input_table)

    inputs: tuple[SimCase, ...] = _get_simulation_cases(input_header, input_body)

    output_table: Table = find_table(book, _OUTPUT_TABLE)

    # Long-format output does not have 1:1 rows with inputs.
    output_header, _output_body = get_table_data(output_table)

    if selected_indices is None:
        run_postprocess(book, inputs, output_header)
        return

    selected: list[SimCase] = []
    selected_set = set(selected_indices)
    for i, sim_case in enumerate(inputs):
        if i in selected_set:
            selected.append(sim_case)

    run_postprocess(book, tuple(selected), output_header, source_inputs=inputs)


def run_all(book: xw.Book) -> None:
    """Run all simulation cases in the workbook.

    Parameters
    ----------
    book : xw.Book
        Calling xlwings workbook.
    """
    run_selected(book, selected_indices=None)


def selected_input_indices(
    book: xw.Book,
    table_key: str = _INPUT_TABLE,
) -> tuple[int, ...] | None:
    """Return selected visible row indices within the input table body.

    Parameters
    ----------
    book : xw.Book
        Workbook whose active Excel selection is inspected.
    table_key : str, optional
        Input table name or display name.

    Returns
    -------
    tuple[int, ...] or None
        Sorted zero-based body row indices. ``None`` is returned when the
        selection does not intersect the table body or the table is empty.

    Notes
    -----
    Selection is accepted only when it intersects the actual table body on the
    same worksheet in both row and column directions. Hidden rows are ignored.
    """

    table, table_sheet = find_table_and_sheet(book, table_key)
    body = table.data_body_range
    if body is None:
        return None

    sel = book.app.selection
    if sel is None:
        return None

    body_first_row = int(body.row)
    body_last_row = body_first_row + int(body.rows.count) - 1
    body_first_col = int(body.column)
    body_last_col = body_first_col + int(body.columns.count) - 1

    def _same_sheet(area: Any) -> bool:
        with suppress(Exception):
            return str(area.sheet.name) == str(table_sheet.name)
        return False

    def _is_row_hidden(row_num: int) -> bool:
        with suppress(Exception):
            return bool(table_sheet.range(f"{row_num}:{row_num}").api.EntireRow.Hidden)
        return False

    # xlwings Range may or may not expose .areas depending on backend/typing.
    sel_any: Any = sel
    areas_obj = getattr(sel_any, "areas", None)
    areas = areas_obj if areas_obj is not None else [sel_any]

    idxs: set[int] = set()
    for area in areas:
        if not _same_sheet(area):
            continue

        r0 = int(area.row)
        r1 = r0 + int(area.rows.count) - 1
        c0 = int(area.column)
        c1 = c0 + int(area.columns.count) - 1

        # Require row AND column intersection with the t_input body range.
        rr0 = max(r0, body_first_row)
        rr1 = min(r1, body_last_row)
        cc0 = max(c0, body_first_col)
        cc1 = min(c1, body_last_col)
        if rr0 > rr1 or cc0 > cc1:
            continue

        for r in range(rr0, rr1 + 1):
            if _is_row_hidden(r):
                continue
            idxs.add(r - body_first_row)

    return tuple(sorted(idxs)) if idxs else None


def _read_json(path: Path) -> dict[str, Any] | None:
    with suppress(Exception):
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _meta_matches(
    path: Path, *, key_field: str, hash_field: str, key: str, h: str
) -> bool:
    """Check whether a metadata file matches the expected key and hash.

    Parameters
    ----------
    path : Path
        JSON metadata file to inspect.
    key_field : str
        Field name containing the canonical case key.
    hash_field : str
        Field name containing the derived hash.
    key : str
        Expected canonical case key.
    h : str
        Expected hash value.

    Returns
    -------
    bool
        ``True`` when both metadata fields match the expected values.
    """

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
    """Return whether a case has complete solve outputs and matching metadata.

    Parameters
    ----------
    run_dir : Path
        Case result directory expected to contain MAPDL database and result files.
    case_meta_path : Path
        Metadata JSON path associated with the case.
    case_key : str
        Canonical case key used to validate metadata.
    case_hash : str
        Expected case hash used to validate metadata.

    Returns
    -------
    bool
        ``True`` if ``case.db``, ``case.rst``, and matching metadata all exist.
    """

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
    """Solve simulation cases through MAPDL and update Excel status cells.

    Parameters
    ----------
    book : xw.Book
        Calling workbook used for UI status updates.
    inputs : tuple[SimCase, ...]
        Simulation cases to solve. Aggregate-only cases are skipped here.
    save_intermediate : bool, optional
        If ``True``, write reusable geometry and mesh artifacts during solve
        pipeline generation.
    """

    hb = UIHeartbeat(book)

    cfg = get_path_config()
    base_run_dir = cfg.results_root / "case"
    case_artifacts_root = cfg.artifacts_root / "case"

    # Reuse one MAPDL session for a configurable number of solve cases.
    # t_config.ansys_batch_size:
    #   1 = restart every case (previous behavior)
    #   0 = run all runnable cases in one MAPDL session
    #   N = restart every N runnable cases
    session_root = base_run_dir / "__mapdl_session"
    session_root.mkdir(parents=True, exist_ok=True)
    ansys_batch_size = int(getattr(cfg, "ansys_batch_size", 1))

    # Use a stable, non-hash jobname so result filenames don't include the case hash.
    jobname = "case"

    try:
        # Mark all selected rows as pending up-front.
        for sim_case in inputs:
            _set_status_pending(
                book,
                _status_range_for_input_row(book, int(sim_case.row_idx)),
            )
            hb.tick()

        with MapdlBatchRunner(
            session_root=session_root,
            jobname=jobname,
            nproc=getattr(cfg, "nproc", None),
            batch_size=ansys_batch_size,
        ) as mapdl_runner:
            for sim_case in inputs:
                status_cell = _status_range_for_input_row(book, int(sim_case.row_idx))
                _set_status_running(book, status_cell)
                hb.tick()

                if _is_aggregate_sim_type(sim_case.post_mesh_spec.setup.sim_type):
                    # Aggregate rows (static=100, total=101) are postprocess-only.
                    # They combine already-computed cases and never run MAPDL solve.
                    _set_status_skip(book, status_cell)
                    continue

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
                        default=lambda o: (o.tolist() if hasattr(o, "tolist") else vars(o)),
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
                        # RESUME may reset jobname; /FILNAME must run at BEGIN level.
                        + ("FINISH", "/FILNAME,case", "/PREP7")
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
                        # RESUME may reset jobname; /FILNAME must run at BEGIN level.
                        + ("FINISH", "/FILNAME,case", "/PREP7")
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
                    pipeline = build_pipeline(sim_case, save_intermediate=save_intermediate)

                # Ensure jobname is set after /CLEAR inside the pipeline.
                pipeline = pipeline[:1] + ("/FILNAME,case",) + pipeline[1:]

                cwd_cmds = (f"/CWD,'{run_dir.as_posix()}'",)

                # Save full solve command stream for reproducibility.
                macro_path = case_artifacts_root / case_hash / "main.mac"
                write_apdl_macro(
                    macro_path,
                    cwd_cmds + pipeline,
                    title="solve",
                    metadata={
                        "case_hash": case_hash,
                        "jobname": jobname,
                    },
                )

                try:
                    mapdl_runner.run_case(cwd_cmds + pipeline)
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
    *,
    source_inputs: tuple[SimCase, ...] | None = None,
) -> None:
    """Run MAPDL postprocessing and write long-format rows to ``t_out``.

    Parameters
    ----------
    book : xw.Book
        Calling workbook used for table writes and status updates.
    inputs : tuple[SimCase, ...]
        Cases to postprocess. Static/total aggregate rows are handled without
        launching additional MAPDL commands.
    output_header : Header
        Existing output table header. Kept for backward-compatible call sites.
    source_inputs : tuple[SimCase, ...] or None, optional
        Full source case list used when aggregate rows need to find component
        load cases outside the selected subset.

    Notes
    -----
    Output table is expected to be named ``t_out``.

    Extraction produces a flat list of ``post.row.TOutRow`` and writes them
    into the output table with columns ``hash``, ``category``, ``row``,
    ``col``, ``value``, and ``unit``.
    """

    hb = UIHeartbeat(book)

    _ = output_header

    cfg = get_path_config()
    base_run_dir = cfg.results_root / "case"
    case_artifacts_root = cfg.artifacts_root / "case"

    # Requested output prefixes for the new long-format pipeline.
    # Provide only user-facing outputs here; prerequisites are resolved automatically.
    # TODO: make this configurable from Excel once the schema is finalized.
    requested_needed: dict[str, int] = {
        # Static (default)
        "volume.solid.value": 1,
        "mass.solid.value": 1,
        "volume_fraction.cell.value": 1,
        "element.count": 1,
        "stress.volume.sum": 1,
        "energy.strain.total": 1,
        "energy.strain_density.reference": 1,
        "stress.volume.avg": 1,
        "energy.strain_density.mean": 1,
        "energy.strain_density.std": 1,
        "energy.strain_density.median": 1,
        "energy.strain_density.min": 1,
        "energy.strain_density.max": 1,
        "energy.strain_density.range": 1,
        "energy.strain_density.p95": 1,
        "energy.strain_density.p99": 1,
        "energy.strain_density.cv": 1,
        "energy.strain_density.skewness": 1,
        "energy.strain_density.kurtosis": 1,
        "energy.strain_density.normalized.mean": 1,
        "energy.strain_density.normalized.std": 1,
        "energy.strain_density.normalized.median": 1,
        "energy.strain_density.normalized.min": 1,
        "energy.strain_density.normalized.max": 1,
        "energy.strain_density.normalized.range": 1,
        "energy.strain_density.normalized.p95": 1,
        "energy.strain_density.normalized.p99": 1,
        "energy.strain_density.normalized.cv": 1,
        "energy.strain_density.normalized.skewness": 1,
        "energy.strain_density.normalized.kurtosis": 1,
        "force.boundary.value": 1,
        "moment.boundary.value": 1,
        "traction.boundary.value": 1,
        "stress.boundary.value": 1,
        "modulus.boundary.value": 1,
        "modulus.boundary.ratio": 1,
        "modulus.effective.youngs": 1,
        "modulus.effective.shear": 1,
        "modulus.effective.bulk": 1,
        "modulus.effective.youngs.ratio": 1,
        "modulus.effective.shear.ratio": 1,
        "modulus.effective.youngs.specific": 1,
        "modulus.effective.shear.specific": 1,
        "area.boundary_contact.value": 1,
        "area.boundary_contact.ratio": 1,
        "traction.contact.value": 1,
        "stress.contact.value": 1,
        # Modal (default)
        **{f"res_freq_{i}": 1 for i in range(1, 11)},
        **{f"part_factor_{i}": 1 for i in range(1, 11)},
        **{f"eff_modal_mass_{i}": 1 for i in range(1, 11)},
    }

    # Compute-time needed = requested + all prerequisites.
    from post.dependency_resolver import expand_prefixes
    from post.output_dependency import OUTPUT_DEPENDENCIES

    expanded = expand_prefixes(requested_needed.keys(), OUTPUT_DEPENDENCIES)
    needed: dict[str, int] = {p: 1 for p in expanded}

    from custom_io.excel.write_long import upsert_long_rows
    from custom_io.post.extract import extract_post_rows
    from post.context import PostprocessContext
    from post.row import T_OUT_COLUMNS

    output_table: Table = find_table(book, _OUTPUT_TABLE)
    aggregate_source_cases = source_inputs if source_inputs is not None else inputs

    # We upsert to t_out incrementally per case for better UI responsiveness.

    # Keep a single MAPDL session open and switch working directory per case.
    session_dir = base_run_dir / "__mapdl_post_session"
    session_dir.mkdir(parents=True, exist_ok=True)
    jobname = "case"

    try:
        for sim_case in inputs:
            _set_status_pending(
                book, _status_range_for_input_row(book, int(sim_case.row_idx))
            )
            hb.tick()

        with mapdl_session(
            run_location=str(session_dir),
            jobname=jobname,
            cleanup_on_exit=False,
            nproc=getattr(cfg, "nproc", None),
        ) as mapdl:
            for sim_case in inputs:
                status_cell = _status_range_for_input_row(book, int(sim_case.row_idx))
                _set_status_running(book, status_cell)
                hb.tick()

                if _is_aggregate_sim_type(sim_case.post_mesh_spec.setup.sim_type):
                    try:
                        write_aggregate_rows(
                            aggregate_case=sim_case,
                            source_cases=tuple(aggregate_source_cases),
                            case_artifacts_root=case_artifacts_root,
                            output_table=output_table,
                        )
                    except Exception:
                        _set_status_fail(book, status_cell)
                        hb.tick(force=True)
                        raise
                    _set_status_done(book, status_cell)
                    hb.tick(force=True)
                    continue

                sim_type = str(sim_case.post_mesh_spec.setup.sim_type)
                allowed_needed: dict[str, int] = {
                    p: n
                    for p, n in needed.items()
                    if is_post_output_allowed(p, sim_type)
                }
                if not allowed_needed:
                    _set_status_done(book, status_cell)
                    continue

                allowed_requested: set[str] = {
                    p for p in requested_needed.keys() if p in allowed_needed
                }

                case_hash = build_case_hash(sim_case.to_string())
                run_dir = base_run_dir / f"{case_hash}"

                # Load per-case post cache (avoid Excel reads for caching).
                from post.post_cache import (
                    cache_path_for_case,
                    load_post_cache,
                    required_keys_modal,
                    required_keys_static,
                    save_post_cache,
                )
                from post.boundary_force_command import _SIM_TYPE_TO_ROW

                cache_path = cache_path_for_case(
                    artifacts_case_dir=case_artifacts_root,
                    case_hash=case_hash,
                )
                cache = load_post_cache(cache_path, case_hash=case_hash)

                prelude = (
                    f"/CWD,'{run_dir.as_posix()}'",
                    "FINISH",
                    "/CLEAR",
                    "RESUME,'case','db'",
                )
                run_commands(mapdl, prelude)

                # Reduce compute set using cache completeness.
                sim_type_l = str(sim_type).strip().lower()
                static_row = _SIM_TYPE_TO_ROW.get(sim_type_l)

                compute_prefixes: set[str] = set()
                for p in allowed_needed.keys():
                    # Always compute identifiers/noops via pipeline filtering; here we decide only
                    # whether to request actual computation.
                    req_keys: set[str] | None = None
                    if sim_type_l in {"modal", "modal_ff"}:
                        # modal: prefixes already include mode number in name
                        # parse mode index from suffix
                        try:
                            mode_index = int(p.rsplit("_", 1)[1])
                        except Exception:
                            mode_index = 0
                        if mode_index > 0:
                            req_keys = required_keys_modal(p, sim_type=sim_type_l, mode_index=mode_index)
                    else:
                        if static_row is not None:
                            req_keys = required_keys_static(p, sim_type=sim_type_l, row=int(static_row))

                    if not req_keys:
                        compute_prefixes.add(p)
                        continue

                    if all(k in cache.rows for k in req_keys):
                        # cached: skip computing this prefix
                        continue
                    compute_prefixes.add(p)

                compute_needed: dict[str, int] = {p: 1 for p in compute_prefixes}

                pipeline = post_commands(sim_case=sim_case, needed=compute_needed)

                write_apdl_macro(
                    case_artifacts_root / case_hash / "post.mac",
                    prelude + pipeline,
                    title="post",
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
                    hb.tick(force=True)
                    raise

                hb.tick()

                ctx = PostprocessContext(sim_case=sim_case, needed=allowed_needed)

                from post.sim_case_meta import sim_case_meta

                meta = sim_case_meta(sim_case)
                cache.sim_case_meta = meta

                extract_post_rows(
                    ctx=ctx,
                    mapdl=mapdl,
                    cache=cache,
                    meta=meta,
                    case_hash=case_hash,
                    allowed_needed=allowed_needed,
                    compute_needed=compute_needed,
                    allowed_requested=allowed_requested,
                )
                # Persist cache for this case (including intermediates).
                save_post_cache(cache_path, cache)

                # Upsert this case immediately from cache (ensures units are always current).
                from post.post_cache import parse_key
                from post.unit_resolver import unit_for_category

                sync_rows: list[dict[str, Any]] = []
                for k, v in cache.rows.items():
                    try:
                        cat, r_i, c_i = parse_key(k)
                    except Exception:
                        continue
                    d = {
                        "hash": case_hash,
                        "category": str(cat),
                        "row": int(r_i),
                        "col": int(c_i),
                        "value": float(v),
                        "unit": unit_for_category(str(cat)),
                    }
                    sync_rows.append(d)

                if sync_rows:
                    upsert_long_rows(
                        table=output_table,
                        rows=sync_rows,
                        required_columns=T_OUT_COLUMNS,
                    )
                    hb.tick(force=True)

                _set_status_done(book, status_cell)

    except Exception as e:
        print(f"Error: {e}")
        raise


def _canonical_sim_type(sim_type: object) -> str:
    """Return canonical sim_type string used for grouping/aggregation."""

    s = str(sim_type).strip().lower()
    if s in {"100", "100.0", "static"}:
        return "100"
    if s in {"101", "101.0", "total"}:
        return "101"
    if s == "zx":
        # User-facing alias; internally shear XZ is represented as xz.
        return "xz"
    return s


def _is_static_aggregate_sim_type(sim_type: object) -> bool:
    return _canonical_sim_type(sim_type) == "100"


def _is_total_aggregate_sim_type(sim_type: object) -> bool:
    return _canonical_sim_type(sim_type) == "101"


def _is_aggregate_sim_type(sim_type: object) -> bool:
    return _canonical_sim_type(sim_type) in {"100", "101"}


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
    """Write case hashes back to the Excel input table.

    Parameters
    ----------
    input_table : Table
        Excel ``t_input`` table to update.
    hashes : list[str]
        Hash value for each body row in the input table.
    selected_indices : tuple[int, ...] or None
        Rows to update. If ``None``, all rows are updated.
    column_name : str, optional
        Name of the column that stores hashes. The column is created if it is
        missing.
    """

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
