# File: c:\Users\USER\Documents\parametric_lattice\src\core\parameters\sim_case.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from dataclasses import dataclass

from core.parameters.element_type_params import (
    ElementTypeParams,
)
from core.parameters.geometry_params import GeometryParams
from core.parameters.material_params import MaterialParams
from core.parameters.meshing_params import MeshingParams
from core.parameters.profile_params import (
    ProfileParams,
)
from core.parameters.setup_params import SetupParams


@dataclass(frozen=True)
class PreMeshSpec:
    element_type: ElementTypeParams
    profile: ProfileParams
    geometry: GeometryParams
    meshing: MeshingParams

    def to_string(self) -> str:
        return (
            self.element_type.to_string()
            + "__"
            + self.profile.to_string()
            + "__"
            + self.geometry.to_string()
            + "__"
            + self.meshing.to_string()
        )


@dataclass(frozen=True)
class PostMeshSpec:
    material: MaterialParams
    setup: SetupParams

    def to_string(self) -> str:
        return (
            self.material.to_string()
            + "__"
            + self.setup.to_string()
        )


@dataclass(frozen=True)
class SimCase:
    row_idx: int
    pre_mesh_spec: PreMeshSpec
    post_mesh_spec: PostMeshSpec

    def to_string(self) -> str:
        return (
            self.pre_mesh_spec.to_string()
            + "__"
            + self.post_mesh_spec.to_string()
        )
