"""Backward-compatible alias for the capture conditioning implementation."""
import sys

from almond_mcp.features.capture import conditioning as _implementation

sys.modules[__name__] = _implementation
