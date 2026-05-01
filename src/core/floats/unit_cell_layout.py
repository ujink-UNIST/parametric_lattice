# File: c:\Users\USER\Documents\parametric_lattice\src\core\floats\unit_cell_layout.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from collections.abc import Sequence
import numpy as np
from jaxtyping import Float, Int

Nodes = Float[np.ndarray, "N 3"]
NodeBoundaries = Int[np.ndarray, "N 3"]
Edges = Int[np.ndarray, "E 3"]
EdgeTypeIds = Int[np.ndarray, "E"]
EdgeRatios = Float[np.ndarray, "E"]
EdgeNormals = Float[np.ndarray, "E 3"]
