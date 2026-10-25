"""Backward-compatible module identity for structural floor_loads."""
import sys

from almond_mcp.features.structure import floor_loads as _implementation

sys.modules[__name__] = _implementation
