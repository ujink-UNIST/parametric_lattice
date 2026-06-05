#dependency_resolver.py
"""Dependency resolution utilities for post outputs.

Mirrors :mod:`postprocess.dependency_resolver`.

Given a set of requested output prefixes and a dependency graph
(`OUTPUT_DEPENDENCIES`), this module can:
- expand the request to include all prerequisites
- compute an execution order that respects dependencies (topological order)
"""

from __future__ import annotations

from collections.abc import Iterable


class DependencyCycleError(ValueError):
    """Raised when the dependency graph contains a cycle."""


def expand_prefixes(
    requested: Iterable[str],
    deps: dict[str, tuple[str, ...]],
) -> set[str]:
    """Return requested prefixes plus all transitive prerequisites."""

    requested_set = set(requested)
    expanded: set[str] = set()

    visiting: set[str] = set()

    def dfs(node: str) -> None:
        if node in expanded:
            return
        if node in visiting:
            raise DependencyCycleError(
                f"Cycle detected while expanding dependencies at {node!r}"
            )
        visiting.add(node)
        for prereq in deps.get(node, ()):  # unknown nodes: no deps
            dfs(prereq)
        visiting.remove(node)
        expanded.add(node)

    for n in requested_set:
        dfs(n)

    return expanded


def topo_sort(
    nodes: Iterable[str],
    deps: dict[str, tuple[str, ...]],
) -> list[str]:
    """Topologically sort nodes so prerequisites come first.

    deps mapping direction:
      node -> (prereq1, prereq2, ...)

    Only dependencies within `nodes` are considered for ordering.
    """

    node_set = set(nodes)

    order: list[str] = []
    state: dict[str, int] = {}  # 0/absent=unvisited, 1=visiting, 2=done

    def dfs(node: str) -> None:
        st = state.get(node, 0)
        if st == 2:
            return
        if st == 1:
            raise DependencyCycleError(
                f"Cycle detected while sorting dependencies at {node!r}"
            )
        state[node] = 1
        for prereq in deps.get(node, ()):
            if prereq in node_set:
                dfs(prereq)
        state[node] = 2
        order.append(node)

    for n in node_set:
        if state.get(n, 0) == 0:
            dfs(n)

    return order
