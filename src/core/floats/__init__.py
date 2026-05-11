"""Numeric type aliases used across the project.

Prefer importing from here (or :mod:`core.floats.types`) instead of defining new
ad-hoc aliases in feature modules.
"""

from core.floats.types import *

# Re-export for type-checkers/linting tools.
from core.floats.types import __all__  # noqa: F401
