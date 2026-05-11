import pytest

from core.parameters.meshing_params import MeshingParams
from meshing.volume_meshing import (
    _divisions_for_edge,
)


def test_divisions_for_edge_rounds_up():
    assert _divisions_for_edge(1.0, 0.4) == 3


def test_divisions_for_edge_rejects_non_positive_size():
    with pytest.raises(ValueError):
        _divisions_for_edge(1.0, 0.0)


# def test_beam_volume_meshing_commands_include_lesize_and_lmesh(
#     simple_unit_cell,
# ):
#     commands = build_beam_volume_meshing_commands_(
#         simple_unit_cell,
#         MeshingParams(max_element_size=0.6),
#     )

#     assert commands[0] == "! --- Beam volume meshing stage ---"
#     assert "LESIZE,1,,,2" in commands
#     assert "LESIZE,2,,,2" in commands
#     assert commands[-2:] == (
#         "! Mesh all beam lines",
#         "LMESH,ALL",
#     )
