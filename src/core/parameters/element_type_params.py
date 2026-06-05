#element_type_params.py
"""Module for element type params functionality in src.core.parameters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ElementTypeParams:
    model: str

    def to_string(self) -> str:
        return self.model
