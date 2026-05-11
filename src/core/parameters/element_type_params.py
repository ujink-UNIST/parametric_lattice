from dataclasses import dataclass


@dataclass(frozen=True)
class ElementTypeParams:
    model: str
