"""Compatibility alias for the feature-owned drafting implementation."""

import sys

from almond_mcp.features.assets import drafting as implementation

sys.modules[__name__] = implementation
