# path_safety.py

from __future__ import annotations

from pathlib import Path


def safe_path_under(root: Path, name: str, suffix: str) -> Path:
    """Build a safe path under *root* from a user-provided relative name.

    This prevents directory traversal (e.g. "../"), absolute paths, and other
    ways to escape the intended root directory.

    Args:
        root: Base directory that all paths must remain under.
        name: User-provided relative path (e.g. "custom/test").
        suffix: Required suffix (".json", ".lgf", ...). If *name* has a
            different suffix (or no suffix), it is replaced.

    Returns:
        Resolved absolute path that is guaranteed to be inside *root*.

    Raises:
        ValueError: If *name* is absolute, contains a drive, or escapes *root*.
    """

    root_resolved = root.resolve()
    rel = Path(name)

    # Block absolute paths (including Windows drive paths).
    if rel.is_absolute() or rel.drive:
        raise ValueError(f"Absolute path not allowed: {name!r}")

    if rel.suffix != suffix:
        rel = rel.with_suffix(suffix)

    out = (root_resolved / rel).resolve()

    # Ensure the final resolved path is still under the root.
    if not out.is_relative_to(root_resolved):
        raise ValueError(f"Path escapes root: {name!r}")

    return out
