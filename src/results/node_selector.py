# """Node selection utilities for boundary-face result extraction."""

# from __future__ import annotations

# from typing import Tuple

# from core.types_ import UnitCell
# from geometry.solid_geometry import FACE_TO_NS

# # Legacy aliases kept for compatibility with older APDL component naming.
# _BEAM_LINE_COMPONENT_ALIASES = {
#     "+x": ("CM_LINE_PX", "NS_PX"),
#     "-x": ("CM_LINE_MX", "NS_MX"),
#     "+y": ("CM_LINE_PY", "NS_PY"),
#     "-y": ("CM_LINE_MY", "NS_MY"),
#     "+z": ("CM_LINE_PZ", "NS_PZ"),
#     "-z": ("CM_LINE_MZ", "NS_MZ"),
# }

# _BEAM_KP_COMPONENT_ALIASES = {
#     "+x": ("CM_KP_PX", "KP_PX"),
#     "-x": ("CM_KP_MX", "KP_MX"),
#     "+y": ("CM_KP_PY", "KP_PY"),
#     "-y": ("CM_KP_MY", "KP_MY"),
#     "+z": ("CM_KP_PZ", "KP_PZ"),
#     "-z": ("CM_KP_MZ", "KP_MZ"),
# }


# def selected_node_ids(mapdl) -> Tuple[int, ...]:
#     """Return currently selected node ids as a sorted tuple."""
#     raw = mapdl.get_array("NODE", item1="NLIST")
#     if raw is None:
#         return tuple()

#     node_ids = []
#     for value in raw:
#         node_id = int(value)
#         if node_id > 0:
#             node_ids.append(node_id)
#     return tuple(sorted(set(node_ids)))


# def component_face_node_ids_solid(mapdl, face: str) -> Tuple[int, ...]:
#     """Read solid-face node ids from the named area component."""
#     area_cm = FACE_TO_NS[face]
#     try:
#         mapdl.asel("ALL")
#         mapdl.nsel("NONE")
#         mapdl.cmsel("S", area_cm, "AREA")
#         mapdl.nsla("S", 1)
#         return selected_node_ids(mapdl)
#     except Exception:
#         return tuple()
#     finally:
#         mapdl.allsel()


# def component_face_node_ids_beam(mapdl, face: str) -> Tuple[int, ...]:
#     """Read beam-face node ids from line and keypoint components (union)."""
#     node_ids = set()

#     line_components = _BEAM_LINE_COMPONENT_ALIASES[face]
#     kp_components = _BEAM_KP_COMPONENT_ALIASES[face]

#     mapdl.lsel("ALL")
#     mapdl.nsel("NONE")
#     for line_cm in line_components:
#         try:
#             mapdl.cmsel("S", line_cm, "LINE")
#             try:
#                 mapdl.nsll("S", 1)
#             except Exception:
#                 mapdl.nsll("S")
#             picked = selected_node_ids(mapdl)
#             if picked:
#                 node_ids.update(int(node_id) for node_id in picked)
#                 print(
#                     f"[node_selector] face={face} beam_line_component={line_cm} "
#                     f"picked_nodes={len(picked)}"
#                 )
#                 break
#         except Exception:
#             continue
#     mapdl.allsel()

#     mapdl.ksel("ALL")
#     mapdl.nsel("NONE")
#     for kp_cm in kp_components:
#         try:
#             mapdl.cmsel("S", kp_cm, "KP")
#             try:
#                 mapdl.nslk("S")
#             except Exception:
#                 try:
#                     mapdl.nslk("S", 1)
#                 except Exception:
#                     pass
#             picked = selected_node_ids(mapdl)
#             if picked:
#                 node_ids.update(int(node_id) for node_id in picked)
#                 print(
#                     f"[node_selector] face={face} beam_kp_component={kp_cm} "
#                     f"picked_nodes={len(picked)}"
#                 )
#                 break
#         except Exception:
#             continue
#     mapdl.allsel()

#     return tuple(sorted(node_ids))


# def location_face_node_ids(
#     mapdl,
#     unit_cell: UnitCell,
#     face: str,
#     tol: float = 1e-3,
# ) -> Tuple[int, ...]:
#     """Select MAPDL nodes on a boundary face using coordinate windows."""
#     lx, ly, lz = unit_cell.size
#     face_target = {
#         "+x": ("X", +lx / 2.0),
#         "-x": ("X", -lx / 2.0),
#         "+y": ("Y", +ly / 2.0),
#         "-y": ("Y", -ly / 2.0),
#         "+z": ("Z", +lz / 2.0),
#         "-z": ("Z", -lz / 2.0),
#     }
#     axis, value = face_target[face]
#     vmin = value - tol
#     vmax = value + tol

#     mapdl.run("NSEL,NONE")
#     mapdl.run(f"NSEL,S,LOC,{axis},{vmin:.10g},{vmax:.10g}")
#     node_ids = selected_node_ids(mapdl)
#     mapdl.allsel()
#     return node_ids


# def face_node_ids(
#     mapdl,
#     unit_cell: UnitCell,
#     face: str,
#     model: str,
# ) -> Tuple[int, ...]:
#     """Return node ids for one face using name-based selection first."""
#     from core.types_ import element_group

#     group = element_group(model)
#     if group == "BEAM":
#         component_nodes = component_face_node_ids_beam(mapdl, face)
#     else:
#         component_nodes = component_face_node_ids_solid(mapdl, face)

#     if component_nodes:
#         print(
#             f"[node_selector] face={face} model={model} node_source=component "
#             f"count={len(component_nodes)}"
#         )
#         return component_nodes

#     fallback_nodes = location_face_node_ids(mapdl, unit_cell, face)
#     print(
#         f"[node_selector] face={face} model={model} node_source=location_fallback "
#         f"count={len(fallback_nodes)}"
#     )
#     return fallback_nodes


# def select_nodes(mapdl, node_ids: Tuple[int, ...]) -> None:
#     """Select nodes one by one (legacy-compatible selection flow)."""
#     mapdl.nsel("NONE")
#     first = True
#     for node_id in node_ids:
#         mapdl.nsel("S" if first else "A", "NODE", "", int(node_id))
#         first = False
