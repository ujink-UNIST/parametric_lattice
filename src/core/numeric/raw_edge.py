# raw_edge.py

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawEdge:
    node0_id: int
    node1_id: int
    beam_id: int
