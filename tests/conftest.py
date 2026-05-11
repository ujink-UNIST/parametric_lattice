import numpy as np
import pytest

from core.unit_cell import UnitCell


@pytest.fixture
def simple_unit_cell() -> UnitCell:
    return UnitCell(
        name="toy",
        nodes=np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
            ],
            dtype=float,
        ),
        node_boundaries=np.array(
            [
                [0, 0, 0],
                [1, 0, 0],
                [1, 1, 0],
            ],
            dtype=int,
        ),
        beam_types=({},),
        edges=np.array(
            [
                [0, 1, 1.0],
                [1, 2, 1.0],
            ],
            dtype=int,
        ),
        edge_beam_type_ids=np.array([0, 0], dtype=int),
        edge_ratios=np.array([1.0, 0.5], dtype=float),
        edge_normal_vectors=np.array(
            [
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=float,
        ),
    )
