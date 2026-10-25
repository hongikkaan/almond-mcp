"""Backward-compatible module identity for structural frame_solver."""
import sys

from almond_mcp.features.structure import frame_solver as _implementation

sys.modules[__name__] = _implementation
