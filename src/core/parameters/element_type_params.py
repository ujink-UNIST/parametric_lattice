# element_type_params.py

from dataclasses import dataclass


@dataclass(frozen=True)
class ElementTypeParams:
    model: str

    def to_string(self) -> str:
        return self.model
