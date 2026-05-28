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
from custom_io.ui_heartbeat import UIHeartbeat
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
from post.output_spec import is_post_output_allowed
from post.pipeline import post_commands

_INPUT_TABLE = "t_input"
_OUTPUT_TABLE = "t_out"  # long-format output table (required)
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
    # Mirror the global spinner cell (Input!A1) while this case runs.
    cell.formula = "=Input!$A$1"
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
      - n_proc          (optional int, MAPDL -np)

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

    nproc: int | None = None
    i_np = col_index.get("n_proc")
    if i_np is not None and i_np < len(row0):
        v = row0[i_np]
        if v is not None and str(v).strip():
            try:
                nproc = int(float(v))
            except Exception as e:
                raise ValueError(f"t_config.n_proc must be an int (got {v!r})") from e
            if nproc <= 0:
                raise ValueError(f"t_config.n_proc must be positive (got {nproc})")

    set_path_config(
        PathConfig(
            repo_root=cfg.repo_root,
            lgf_root=lgf_root,
            artifacts_root=artifacts_root,
            results_root=results_root,
            compute_policy=compute_policy_raw,
            nproc=nproc,
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

    run_postprocess(book, tuple(selected), output_header)


def run_all(book: xw.Book) -> None:
    """Backwards-compatible helper: run all cases."""
    run_selected(book, selected_indices=None)


def selected_input_indices(
    book: xw.Book,
    table_key: str = _INPUT_TABLE,
) -> tuple[int, ...] | None:
    """Return 0-based visible row indices within the input table body.

    Selection is accepted only when it intersects the actual `t_input` body on
    the same worksheet, in both row and column directions. This prevents rows on
    other sheets, whole-sheet row selections, or filtered/hidden rows from being
    interpreted as selected simulation cases.

    Rules:
      - If the selection does not intersect the table body, returns None.
      - If the table has no body (empty), returns None.
      - Hidden rows (including rows hidden by filters) are ignored.
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
    hb = UIHeartbeat(book)

    cfg = get_path_config()
    base_run_dir = cfg.results_root / "case"
    case_artifacts_root = cfg.artifacts_root / "case"

    # Run MAPDL via a separate Python subprocess per case.
    # Excel/COM updates remain in this parent process.
    session_root = base_run_dir / "__mapdl_session"
    session_root.mkdir(parents=True, exist_ok=True)

    # Use a stable, non-hash jobname so result filenames don't include the case hash.
    jobname = "case"

    import subprocess
    import sys

    try:
        # Mark all selected rows as pending up-front.
        for sim_case in inputs:
            _set_status_pending(
                book,
                _status_range_for_input_row(book, int(sim_case.row_idx)),
            )
            hb.tick()

        for sim_case in inputs:
            status_cell = _status_range_for_input_row(book, int(sim_case.row_idx))
            _set_status_running(book, status_cell)
            hb.tick()

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

            # Unique session dir per subprocess to avoid collisions.
            session_dir = session_root / case_hash
            session_dir.mkdir(parents=True, exist_ok=True)

            cmd = [
                sys.executable,
                "-m",
                "custom_io.mapdl_worker",
                "--macro",
                str(macro_path),
                "--session-dir",
                str(session_dir),
                "--jobname",
                jobname,
            ]
            if getattr(cfg, "nproc", None):
                cmd += ["--nproc", str(int(cfg.nproc))]

            try:
                subprocess.run(cmd, check=True)
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
    hb = UIHeartbeat(book)

    """Run postprocessing for the given cases (long-format t_out).

    Output table is expected to be named `t_out`.

    Extraction produces a flat list of :class:`post.row.TOutRow` and writes them
    into the output table with columns:
      hash, category, row, col, value, unit

    NOTE: `output_header` is accepted for backward compatibility with call sites
    but is not used.
    """

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
        "stress.volume.sum": 1,
        "energy.strain.total": 1,
        "stress.volume.avg": 1,
        "energy.strain_density.avg": 1,
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
        **{f"res_freq_{i}": 1 for i in range(1, 21)},
        **{f"part_factor_{i}": 1 for i in range(1, 21)},
        **{f"eff_modal_mass_{i}": 1 for i in range(1, 21)},
    }

    # Compute-time needed = requested + all prerequisites.
    from post.dependency_resolver import expand_prefixes
    from post.output_dependency import OUTPUT_DEPENDENCIES

    expanded = expand_prefixes(requested_needed.keys(), OUTPUT_DEPENDENCIES)
    needed: dict[str, int] = {p: 1 for p in expanded}

    from custom_io.excel_write_long import upsert_long_rows
    from post.boundary_force_command import extract_boundary_force_rows
    from post.boundary_moment_command import extract_boundary_moment_rows
    from post.boundary_traction_command import extract_boundary_traction_rows
    from post.boundary_stress_command import extract_boundary_stress_rows
    from post.boundary_modulus_command import extract_boundary_modulus_rows
    from post.boundary_touch_area_command import extract_boundary_touch_area_rows
    from post.boundary_touch_area_ratio_command import extract_boundary_touch_area_ratio_rows
    from post.boundary_modulus_ratio_command import extract_boundary_modulus_ratio_rows
    from post.contact_command import (
        extract_contact_stress_rows,
        extract_contact_traction_rows,
    )
    from post.volume_command import extract_volume_rows
    from post.effective_moduli_command import (
        extract_effective_shear_modulus_rows,
        extract_effective_youngs_modulus_rows,
    )
    from post.effective_bulk_modulus_command import extract_effective_bulk_modulus_rows
    from post.mass_command import extract_mass_rows
    from post.volume_fraction_command import extract_volume_fraction_rows
    from post.specific_moduli_command import (
        extract_specific_shear_modulus_rows,
        extract_specific_youngs_modulus_rows,
    )
    from post.effective_moduli_ratio_command import (
        extract_effective_shear_modulus_ratio_rows,
        extract_effective_youngs_modulus_ratio_rows,
    )
    from post.volume_metrics_command import (
        extract_volume_avg_energy_rows,
        extract_volume_avg_stress_rows,
        extract_volume_energy_rows,
        extract_volume_stress_rows,
    )
    from post.modal_command import (
        extract_effective_modal_mass_rows,
        extract_participation_factor_rows,
        extract_resonant_frequency_rows,
    )
    from post.context import PostprocessContext
    from post.row import T_OUT_COLUMNS

    output_table: Table = find_table(book, _OUTPUT_TABLE)

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

                case_rows: list[dict[str, Any]] = []

                def _add_rows(rs):
                    for r in rs:
                        d = r.as_dict()
                        d.update(meta)
                        case_rows.append(d)

                def _cache_rows(rs):
                    for r in rs:
                        cache.upsert(
                            category=str(r.category),
                            row=int(r.row),
                            col=int(r.col),
                            value=float(r.value),
                        )

                # Extract & cache anything we actually computed this run.
                # Write to Excel only if the prefix was explicitly requested.

                if "force.boundary.value" in allowed_needed and "force.boundary.value" in compute_needed:
                    rows = extract_boundary_force_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="N")
                    _cache_rows(rows)
                    if "force.boundary.value" in allowed_requested:
                        _add_rows(rows)

                if "moment.boundary.value" in allowed_needed and "moment.boundary.value" in compute_needed:
                    rows = extract_boundary_moment_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="N*mm")
                    _cache_rows(rows)
                    if "moment.boundary.value" in allowed_requested:
                        _add_rows(rows)

                if "traction.boundary.value" in allowed_needed and "traction.boundary.value" in compute_needed:
                    rows = extract_boundary_traction_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
                    _cache_rows(rows)
                    if "traction.boundary.value" in allowed_requested:
                        _add_rows(rows)

                if "stress.boundary.value" in allowed_needed and "stress.boundary.value" in compute_needed:
                    rows = extract_boundary_stress_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
                    _cache_rows(rows)
                    if "stress.boundary.value" in allowed_requested:
                        _add_rows(rows)

                if "modulus.boundary.value" in allowed_needed and "modulus.boundary.value" in compute_needed:
                    rows = extract_boundary_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
                    _cache_rows(rows)
                    if "modulus.boundary.value" in allowed_requested:
                        _add_rows(rows)

                if "modulus.boundary.ratio" in allowed_needed and "modulus.boundary.ratio" in compute_needed:
                    rows = extract_boundary_modulus_ratio_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="-")
                    _cache_rows(rows)
                    if "modulus.boundary.ratio" in allowed_requested:
                        _add_rows(rows)

                if "modulus.effective.youngs" in allowed_needed and "modulus.effective.youngs" in compute_needed:
                    rows = extract_effective_youngs_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
                    _cache_rows(rows)
                    if "modulus.effective.youngs" in allowed_requested:
                        _add_rows(rows)

                if "modulus.effective.shear" in allowed_needed and "modulus.effective.shear" in compute_needed:
                    rows = extract_effective_shear_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
                    _cache_rows(rows)
                    if "modulus.effective.shear" in allowed_requested:
                        _add_rows(rows)

                if "modulus.effective.bulk" in allowed_needed and "modulus.effective.bulk" in compute_needed:
                    rows = extract_effective_bulk_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
                    _cache_rows(rows)
                    if "modulus.effective.bulk" in allowed_requested:
                        _add_rows(rows)

                if "modulus.effective.youngs.ratio" in allowed_needed and "modulus.effective.youngs.ratio" in compute_needed:
                    rows = extract_effective_youngs_modulus_ratio_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="-")
                    _cache_rows(rows)
                    if "modulus.effective.youngs.ratio" in allowed_requested:
                        _add_rows(rows)

                if "modulus.effective.shear.ratio" in allowed_needed and "modulus.effective.shear.ratio" in compute_needed:
                    rows = extract_effective_shear_modulus_ratio_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="-")
                    _cache_rows(rows)
                    if "modulus.effective.shear.ratio" in allowed_requested:
                        _add_rows(rows)

                if "modulus.effective.youngs.specific" in allowed_needed and "modulus.effective.youngs.specific" in compute_needed:
                    rows = extract_specific_youngs_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="mm^2/s^2")
                    _cache_rows(rows)
                    if "modulus.effective.youngs.specific" in allowed_requested:
                        _add_rows(rows)

                if "modulus.effective.shear.specific" in allowed_needed and "modulus.effective.shear.specific" in compute_needed:
                    rows = extract_specific_shear_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="mm^2/s^2")
                    _cache_rows(rows)
                    if "modulus.effective.shear.specific" in allowed_requested:
                        _add_rows(rows)

                if "area.boundary_contact.value" in allowed_needed and "area.boundary_contact.value" in compute_needed:
                    rows = extract_boundary_touch_area_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="mm^2")
                    _cache_rows(rows)
                    if "area.boundary_contact.value" in allowed_requested:
                        _add_rows(rows)

                if "area.boundary_contact.ratio" in allowed_needed and "area.boundary_contact.ratio" in compute_needed:
                    rows = extract_boundary_touch_area_ratio_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="-")
                    _cache_rows(rows)
                    if "area.boundary_contact.ratio" in allowed_requested:
                        _add_rows(rows)

                if "traction.contact.value" in allowed_needed and "traction.contact.value" in compute_needed:
                    rows = extract_contact_traction_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
                    _cache_rows(rows)
                    if "traction.contact.value" in allowed_requested:
                        _add_rows(rows)

                if "stress.contact.value" in allowed_needed and "stress.contact.value" in compute_needed:
                    rows = extract_contact_stress_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
                    _cache_rows(rows)
                    if "stress.contact.value" in allowed_requested:
                        _add_rows(rows)

                if "volume.solid.value" in allowed_needed and "volume.solid.value" in compute_needed:
                    rows = extract_volume_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="mm^3")
                    _cache_rows(rows)
                    if "volume.solid.value" in allowed_requested:
                        _add_rows(rows)

                if "mass.solid.value" in allowed_needed and "mass.solid.value" in compute_needed:
                    rows = extract_mass_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="kg")
                    _cache_rows(rows)
                    if "mass.solid.value" in allowed_requested:
                        _add_rows(rows)

                if "volume_fraction.cell.value" in allowed_needed and "volume_fraction.cell.value" in compute_needed:
                    rows = extract_volume_fraction_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="-")
                    _cache_rows(rows)
                    if "volume_fraction.cell.value" in allowed_requested:
                        _add_rows(rows)

                if "stress.volume.sum" in allowed_needed and "stress.volume.sum" in compute_needed:
                    rows = extract_volume_stress_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa*mm^3")
                    _cache_rows(rows)
                    if "stress.volume.sum" in allowed_requested:
                        _add_rows(rows)

                if "stress.volume.avg" in allowed_needed and "stress.volume.avg" in compute_needed:
                    rows = extract_volume_avg_stress_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
                    _cache_rows(rows)
                    if "stress.volume.avg" in allowed_requested:
                        _add_rows(rows)

                if "energy.strain.total" in allowed_needed and "energy.strain.total" in compute_needed:
                    rows = extract_volume_energy_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="mJ")
                    _cache_rows(rows)
                    if "energy.strain.total" in allowed_requested:
                        _add_rows(rows)

                if "energy.strain_density.avg" in allowed_needed and "energy.strain_density.avg" in compute_needed:
                    rows = extract_volume_avg_energy_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="mJ/mm^3")
                    _cache_rows(rows)
                    if "energy.strain_density.avg" in allowed_requested:
                        _add_rows(rows)

                # Modal outputs (mode 1..20)
                for i in range(1, 21):
                    key = f"res_freq_{i}"
                    if key in allowed_needed and key in compute_needed:
                        rows = extract_resonant_frequency_rows(
                            ctx=ctx,
                            mapdl=mapdl,
                            case_hash=case_hash,
                            mode_index=i,
                            unit="Hz",
                        )
                        _cache_rows(rows)
                        if key in allowed_requested:
                            _add_rows(rows)

                    key = f"part_factor_{i}"
                    if key in allowed_needed and key in compute_needed:
                        rows = extract_participation_factor_rows(
                            ctx=ctx,
                            mapdl=mapdl,
                            case_hash=case_hash,
                            mode_index=i,
                            unit="-",
                        )
                        _cache_rows(rows)
                        if key in allowed_requested:
                            _add_rows(rows)

                    key = f"eff_modal_mass_{i}"
                    if key in allowed_needed and key in compute_needed:
                        rows = extract_effective_modal_mass_rows(
                            ctx=ctx,
                            mapdl=mapdl,
                            case_hash=case_hash,
                            mode_index=i,
                            unit="kg",
                        )
                        _cache_rows(rows)
                        if key in allowed_requested:
                            _add_rows(rows)

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
