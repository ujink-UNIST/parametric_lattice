from dataclasses import dataclass


@dataclass(frozen=True)
class SolidProfileParams:
    radius: float


@dataclass(frozen=True)
class BeamProfileParams:
    radius: float
    kappa: float


ProfileParams = BeamProfileParams | SolidProfileParams
