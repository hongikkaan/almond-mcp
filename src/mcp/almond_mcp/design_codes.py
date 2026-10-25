"""Backward-compatible module identity for structural design_codes."""
import sys

from almond_mcp.features.structure import design_codes as _implementation

sys.modules[__name__] = _implementation
