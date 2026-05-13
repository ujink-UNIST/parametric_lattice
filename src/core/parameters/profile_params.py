from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolidProfileParams:
    radius: float

    def to_string(self) -> str:
        return f"Radius:{self.radius:.6f}"


@dataclass(frozen=True)
class BeamProfileParams:
    radius: float
    kappa: float

    def to_string(self) -> str:
        return (
            f"Radius:{self.radius:.6f}__Kappa:{self.kappa:.6f}"
        )


ProfileParams = BeamProfileParams | SolidProfileParams


def build_profile_params(
    *,
    element_model: str,
    radius: float,
    kappa: float | None = None,
) -> ProfileParams:
    """Create the right ProfileParams variant based on element type.

    Convention:
      - element_model like "SOLID187" => SolidProfileParams(radius)
      - element_model like "BEAM189"  => BeamProfileParams(radius, kappa)

    Args:
        element_model: Element model string from ElementTypeParams.model.
        radius: Profile radius (or radius multiplier used in this project).
        kappa: Timoshenko shear coefficient for beam profiles. Required for BEAM.
    """

    m = element_model.strip().upper()

    if m.startswith("SOLID"):
        return SolidProfileParams(radius=float(radius))

    if m.startswith("BEAM"):
        if kappa is None:
            raise ValueError(
                "kappa must be provided for BEAM profiles"
            )
        return BeamProfileParams(
            radius=float(radius), kappa=float(kappa)
        )

    raise ValueError(f"Unsupported element model: {element_model!r}")
