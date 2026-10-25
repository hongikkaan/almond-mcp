"""Backward-compatible module identity for structural ec3."""
import sys

from almond_mcp.features.structure import ec3 as _implementation

sys.modules[__name__] = _implementation
