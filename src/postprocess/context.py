"""Shared context passed to postprocess output handlers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.parameters.sim_case import SimCase


@dataclass(frozen=True, slots=True)
class PostprocessContext:
    sim_case: SimCase
    needed: dict[str, int]
