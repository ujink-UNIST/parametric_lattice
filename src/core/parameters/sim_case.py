# File: c:\Users\USER\Documents\parametric_lattice\src\core\parameters\sim_case.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from dataclasses import dataclass

from core.parameters.geometry_params import GeometryParams
from core.parameters.material_params import MaterialParams
from core.parameters.meshing_params import MeshingParams

# from core.parameters.results_params import ResultsParams
from core.parameters.setup_params import SetupParams


@dataclass(frozen=True)
class SimCase:
    row_idx: int
    material_params: MaterialParams
    geometry_params: GeometryParams
    meshing_params: MeshingParams
    setup_params: SetupParams
