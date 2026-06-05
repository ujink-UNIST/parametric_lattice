#raw_edge.py
"""Module for raw edge functionality in src.core.numeric."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawEdge:
    node0_id: int
    node1_id: int
    beam_id: int
