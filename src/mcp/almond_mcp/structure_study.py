"""Backward-compatible module identity for structural structure_study."""
import sys

from almond_mcp.features.structure import structure_study as _implementation

sys.modules[__name__] = _implementation
