"""Backward-compatible module alias for feature-owned asset exchange."""
import sys

from almond_mcp.features.exchange import exchange as implementation

sys.modules[__name__] = implementation
