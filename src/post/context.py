"""Shared context passed to post output handlers.

This mirrors :mod:`postprocess.context` so the new post/ pipeline can evolve
independently while keeping the same calling convention.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.parameters.sim_case import SimCase


@dataclass(frozen=True, slots=True)
class PostprocessContext:
    sim_case: SimCase
    needed: dict[str, int]
