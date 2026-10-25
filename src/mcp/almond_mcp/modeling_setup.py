"""Backward-compatible module alias for modeling feature support."""
import sys

from almond_mcp.features.modeling import modeling_setup as _implementation

sys.modules[__name__] = _implementation
