#errors.py
"""Module for errors functionality in src.preprocess."""

class LatticeJsonError(ValueError):
    """Raised when LGF input cannot be converted into canonical lattice JSON."""
