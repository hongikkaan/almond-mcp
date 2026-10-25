"""Backward-compatible module identity for structural native_structure."""
import sys

from almond_mcp.features.structure import native_structure as _implementation

sys.modules[__name__] = _implementation
