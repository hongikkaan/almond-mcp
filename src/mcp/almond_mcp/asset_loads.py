"""Backward-compatible module identity for structural asset_loads."""
import sys

from almond_mcp.features.structure import asset_loads as _implementation

sys.modules[__name__] = _implementation
